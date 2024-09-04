import itertools
import os
import re
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Tuple, Any

from langchain_community.document_loaders import ConfluenceLoader
from langchain_community.document_loaders.confluence import ContentFormat
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.pydantic_v1 import root_validator, BaseModel
from langchain_text_splitters import MarkdownHeaderTextSplitter
from pydantic import create_model
from pydantic.fields import FieldInfo

from ..llm.llm_utils import get_model, summarize

PrepareDataSchema = create_model(
    "PrepareDataSchema",
    jira_issue_key=(str, FieldInfo(
        description="The issue key of the Jira issue, which will be used to pull data from, e.g. 'TEST-123'.")),
)

SearchDataSchema = create_model(
    "SearchDataSchema",
    jira_issue_key=(str, FieldInfo(
        description="The issue key of the Jira issue, which will be used to pull data from, e.g. 'TEST-123'.")),
    query=(
        str,
        FieldInfo(description="The query to search in the data created from jira ticket. Usually it will be an AC")),
)


class AdvancedJiraMiningWrapper(BaseModel):
    jira_base_url: str
    confluence_base_url: str
    llm_settings: dict
    model_type: str
    summarization_prompt: Optional[str] = None
    jira_api_key: Optional[str] = None,
    jira_username: Optional[str] = None
    jira_token: Optional[str] = None
    is_jira_cloud: Optional[bool] = True
    verify_ssl: Optional[bool] = True

    @root_validator()
    def validate_toolkit(cls, values):
        try:
            from atlassian import Jira  # noqa: F401
        except ImportError:
            raise ImportError(
                "`atlassian` package not found, please run "
                "`pip install atlassian-python-api`"
            )
        url = values['jira_base_url']
        model_type = values['model_type']
        llm_settings = values['llm_settings']
        api_key = values.get('jira_api_key')
        username = values.get('jira_username')
        token = values.get('jira_token')
        is_cloud = values.get('is_jira_cloud')
        if token:
            values['client'] = Jira(url=url, token=token, cloud=is_cloud, verify_ssl=values['verify_ssl'])
        else:
            values['client'] = Jira(url=url, username=username, password=api_key, cloud=is_cloud,
                                    verify_ssl=values['verify_ssl'])
        values['llm'] = get_model(model_type, llm_settings)
        return values

    def __zip_directory(self, folder_path, output_path):
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    # Create a relative path for files to keep the directory structure
                    relative_path = os.path.relpath(os.path.join(root, file), os.path.join(folder_path, '..'))
                    zipf.write(os.path.join(root, file), relative_path)

    def __fetch_jira_confluence_page_ids(self, jira_issue_key: str) -> list[str]:
        """Fetch Jira issue remote confluence page id's

        Args:
            jira_issue_key (str): The key of the jira issue to fetch remote links from

        Returns:
            list: A list containing the remote Jira issue confluence page id's

        """
        remote_links = self.client.get_issue_remote_links(jira_issue_key)
        confluence_remote_links = [link['object']['url'] for link in remote_links if
                                   (link['application'].get('type') is not None and
                                    link['application']['type'] == 'com.atlassian.confluence')]

        return re.findall(r'\d{4,12}', '\n'.join(confluence_remote_links), re.DOTALL)

    def __fetch_all_linked_jira_issue_keys(self, jira_issue_key: str) -> set[str]:
        """Fetch all linked Jira issue keys from a Jira issue.

         Args:
            jira_issue_key (str): The key of the jira issue to fetch linked Jira issue keys from

        Returns:
            set: A set containing the linked Jira issue keys

        """
        linked_issues_keys = set()
        jira_issue = self.client.issue(jira_issue_key, fields='issuelinks')
        linked_links = [link for link in jira_issue['fields']['issuelinks']]
        for link in linked_links:
            if link.get('outwardIssue') is not None:
                # Include in result set ONLY those issues, which are not of type Bug
                if not (link['outwardIssue']['fields']['issuetype']['name'] == 'Bug' or
                        link['outwardIssue']['fields']['issuetype']['name'] == 'Task' or
                        link['outwardIssue']['fields']['issuetype']['name'] == 'Sub-task'):
                    linked_issues_keys.add(link['outwardIssue']['key'])
            else:
                # Include in result set ONLY those issues, which are not of type Bug
                if not (link['inwardIssue']['fields']['issuetype']['name'] == 'Bug' or
                        link['inwardIssue']['fields']['issuetype']['name'] == 'Task' or
                        link['inwardIssue']['fields']['issuetype']['name'] == 'Sub-task'):
                    linked_issues_keys.add(link['inwardIssue']['key'])
        return linked_issues_keys

    def __bulk_fetch_specific_fields_from_jira_issue_key(self, jira_issue_keys: list[str], fields="*all") -> list[str]:
        """Bulk fetch specific fields for Jira issue keys.

        Args:
            jira_issue_keys (list[str]): The keys of the jira issues to fetch data from
            fields (str, optional): A comma-separated string of fields to fetch for the issue. Default is all fields

        Returns:
            list: List of fields specific to Jira issue keys

        """
        issues = self.client.bulk_issue(jira_issue_keys, fields=fields)
        return issues

    def __get_all_jira_issue_keys_from_issue_description(self, jira_issue_key: str) -> list[str]:
        jira_issue = self.client.issue(jira_issue_key, 'description')
        description = jira_issue['fields']['description']
        return list(set(re.findall(r'[A-Z]{1,5}-\d{1,5}', description, re.DOTALL)))

    def __get_all_jira_issue_keys_from_issue_ac(self, jira_issue_key: str) -> list[str]:
        jira_issue = self.client.issue(jira_issue_key, 'customfield_10300')
        description = jira_issue['fields']['customfield_10300']
        return list(set(re.findall(r'[A-Z]{1,5}-\d{1,5}', description, re.DOTALL)))

    def __get_all_jira_issue_keys_from_description_and_ac(self, jira_issue_key: str) -> list[str]:
        desc_keys = self.__get_all_jira_issue_keys_from_issue_description(jira_issue_key)
        ac_keys = self.__get_all_jira_issue_keys_from_issue_ac(jira_issue_key)
        return list(set(itertools.chain(desc_keys, ac_keys)))

    def __get_all_linked_and_in_text_jira_keys(self, jira_issue_key: str) -> list[str]:
        linked_issues = self.__fetch_all_linked_jira_issue_keys(jira_issue_key)
        linked_issues.add(jira_issue_key)
        in_text_issues = self.__get_all_jira_issue_keys_from_description_and_ac(jira_issue_key)
        return list(set(itertools.chain(linked_issues, in_text_issues)))

    def __attach_file_to_jira_issue(self, jira_issue_key: str, file_name: str):
        self.client.add_attachment(jira_issue_key, filename=file_name)

    def __get_confluence_documents_by_jira_ticket(self, jira_issue_id: str) -> list[Document]:
        page_ids = self.__fetch_jira_confluence_page_ids(jira_issue_id)
        if len(page_ids) == 0:
            return []
        confluence_loader = ConfluenceLoader(
            page_ids=page_ids,
            url=self.confluence_base_url,
            api_key=self.jira_api_key,
            username=self.jira_username,
            limit=len(page_ids),
            max_pages=len(page_ids),
            keep_markdown_format=True,
            content_format=ContentFormat.VIEW
        )
        return confluence_loader.load()

    def __split_the_confluence_documents(self, confluence_documents: list) -> list:
        if len(confluence_documents) == 0:
            return []
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4"),
        ]

        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on, strip_headers=False)
        splitted_by_headers_docs = []
        for doc in confluence_documents:
            meta = doc.metadata
            docs_by_headers = markdown_splitter.split_text(doc.page_content)
            for i, split in enumerate(docs_by_headers):
                meta['split_id'] = i
                split.metadata = meta | split.metadata
                splitted_by_headers_docs.append(split)
        return splitted_by_headers_docs

    def __clean_text_lines(self, text: str):
        # Clean none-breaking spaces (nbsp)
        return (line.replace('\xa0', ' ').strip() for line in text.splitlines() if line.strip())

    def __clean_text_from_color_identifiers(self, text: str) -> str:
        clean_color_start = re.sub(r'\{color:#[a-z0-9]{1,6}}', '', text)
        return re.sub(r'\{color}', '', clean_color_start)

    def __process_issue_from_bulk_response(self, issue_from_bulk_response: dict) -> str:
        description = self.__clean_text_from_color_identifiers(
            '\n'.join(self.__clean_text_lines(issue_from_bulk_response['fields']['description'])))
        if self.summarization_prompt:
            return summarize(llm=self.llm, data_to_summarize=description, summarization_key='description',
                             summarization_prompt=self.summarization_prompt)
        else:
            return description

    def __get_jira_descriptions_to_dict(self, jira_issue_key: str) -> Tuple[dict, list[str]]:
        # Cache to store fetched Jira data
        jira_data_cache = {}
        # Get all the jJira issue keys related to jira issue passed in method argument
        jira_keys = self.__get_all_linked_and_in_text_jira_keys(jira_issue_key)
        # Find all the descriptions for all the related jira issues + issue passed in argument itself
        found_issues, _ = self.__bulk_fetch_specific_fields_from_jira_issue_key(jira_keys, fields='description')

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_issue = {
                executor.submit(self.__process_issue_from_bulk_response, issue): issue for issue in
                found_issues['issues']}
            for future in as_completed(future_to_issue):
                jira_issue = future_to_issue[future]
                try:
                    jira_data_cache[jira_issue['key']] = future.result()
                except Exception as e:
                    print(f"Error fetching data for Jira issue {jira_issue}: {e}")
        return jira_data_cache, jira_keys

    def __create_ac_documents_content(self, jira_issue_key: str) -> list[Document]:
        related_description_content = []  # List of related descriptions

        jira_data_cache, keys = self.__get_jira_descriptions_to_dict(
            jira_issue_key)  # Cache to store fetched Jira descriptions

        # Process scenarios and ACs
        for key in keys:
            if key in jira_data_cache:
                res_desc = jira_data_cache[key]
                related_description_content.append(Document(
                    page_content=f"Related links content for jira key - {key}:Ticket Description:\n{res_desc}",
                    metadata={'source': key}))
        return related_description_content

    def __get_attachment_id(self, jira_issue_key: str, file_name: str):
        attachment_ids = self.client.get_attachments_ids_from_issue(jira_issue_key)
        filtered_ids = list(filter(lambda attachment: attachment['filename'] == file_name, attachment_ids))
        print(f"Filtered attachment ids len: {len(filtered_ids)} and value: {filtered_ids}")
        if len(filtered_ids) > 0:
            return filtered_ids[0]['attachment_id']
        else:
            return None

    def __download_attachment_by_id(self, jira_issue_key: str, file_name: str, persistent_path: str = '.'):
        attachment_json = self.client.get_attachment(self.__get_attachment_id(jira_issue_key, file_name))
        url_to_download = attachment_json['content']
        # os.makedirs(persistent_path, exist_ok=True)
        content_to_download = self.client._session.get(url_to_download).content
        with open(os.path.join('.', file_name), 'wb') as f:
            f.write(content_to_download)
        # Open the ZIP file
        with zipfile.ZipFile(file_name, 'r') as zip_ref:
            # Extract all the contents of the zip file to the directory
            zip_ref.extractall(persistent_path)
        os.remove(file_name)

    def __prepare_vectorstore(self, jira_issue_key: str, obtain_vectorstore: bool = False) -> Tuple[str, Chroma | None]:
        persistent_path = os.path.abspath(os.path.join('.', f'jira_ticket_embeddings_{jira_issue_key}'))
        if obtain_vectorstore:
            embedding_function = HuggingFaceEmbeddings(encode_kwargs={'normalize_embeddings': True})
            vectorstore = Chroma(
                collection_name="jira_ticket_data",
                embedding_function=embedding_function,
                persist_directory=persistent_path
            )
            return  persistent_path, vectorstore
        return persistent_path, None


    def prepare_data(self, jira_issue_key: str) -> str:
        """ Prepare the embeddings for the specific jira issue key. They will include both Jira and Confluence info. """
        path, _ = self.__prepare_vectorstore(jira_issue_key)
        zip_file_name = f'jira_ticket_embeddings_{jira_issue_key}.zip'
        if self.__get_attachment_id(jira_issue_key, zip_file_name) is not None:
            self.__download_attachment_by_id(jira_issue_key, zip_file_name)
            return f"The vectorstore content have been obtained from Jira ticket - {jira_issue_key}. You can use it from the path - {path}"
        elif not os.path.exists(path):
            initial_confluence_docs = self.__get_confluence_documents_by_jira_ticket(jira_issue_key)
            result_confluence_docs = self.__split_the_confluence_documents(initial_confluence_docs)
            related_description_list = self.__create_ac_documents_content(jira_issue_key)
            _, vectorstore = self.__prepare_vectorstore(jira_issue_key, obtain_vectorstore=True)
            vectorstore.add_documents(result_confluence_docs)
            vectorstore.add_documents(related_description_list)
            vectorstore.persist()
            self.__zip_directory(path, zip_file_name)
            self.__attach_file_to_jira_issue(jira_issue_key, zip_file_name)
            os.remove(zip_file_name)
            return f'Successfully created embeddings for the jira ticket with following id - {jira_issue_key}'
        else:
            pass

    def search_data(self, jira_issue_key: str, query: str) -> str:
        """ Search the specific jira ticket data using already provided by user jira ticket id and given query. Usually query will be a simple AC from the same ticket """
        _, vectorstore = self.__prepare_vectorstore(jira_issue_key, obtain_vectorstore=True)
        output = []
        retrieved_docs = vectorstore.search(query, 'mmr', k=20, fetch_k=50)
        for doc in retrieved_docs:
            output.append(f'\n\n{doc.page_content}')
        return ''.join(output)

    def get_available_tools(self):
        return [
            {
                "name": "prepare_data",
                "description": self.prepare_data.__doc__,
                "args_schema": PrepareDataSchema,
                "ref": self.prepare_data,
            },
            {
                "name": "search_data",
                "description": self.search_data.__doc__,
                "args_schema": SearchDataSchema,
                "ref": self.search_data,
            },

        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")
