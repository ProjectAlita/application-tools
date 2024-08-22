import logging
import requests
from typing import List, Optional, Any
from pydantic import create_model
from pydantic.fields import FieldInfo
from langchain_core.documents import Document
from langchain_core.pydantic_v1 import root_validator, BaseModel
from langchain_community.document_loaders.confluence import ContentFormat
from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_exponential,
)


logger = logging.getLogger(__name__)

createPage = create_model(
    "createPage",
    space=(str, FieldInfo(description="Confluence space that is used for page's creation", default=None)),
    title=(str, FieldInfo(description="Title of the page")),
    body=(str, FieldInfo(description="Body of the page")),
    parent_id=(str, FieldInfo(description="Page parent id (optional)", default=None)),
    representation=(str, FieldInfo(description="Content representation format: storage for html, wiki for markdown", default='storage')),
)

createPages = create_model(
    "createPages",
    space=(str, FieldInfo(description="Confluence space that is used for pages creation", default=None)),
    pages_info=(dict, FieldInfo(description="Content in key-value format: Title=Body")),
    parent_id=(str, FieldInfo(description="Page parent id (optional)", default=None)),
)

deletePage = create_model(
    "deletePage",
    page_id=(str, FieldInfo(description="Page id")),
    recursive=(bool, FieldInfo(description="Recursive: if True - will recursively delete all children pages too", default=False))
)

getPageTree = create_model(
    "getPageTree",
    page_id=(str, FieldInfo(description="Page id")),
)

pageExists = create_model(
    "pageExists",
    title=(str, FieldInfo(description="Title of the page")),
)

getPagesWithLabel = create_model(
    "getPagesWithLabel",
    label=(str, FieldInfo(description="Label of the pages")),
)

searchPages = create_model(
    "searchPages",
    query=(str, FieldInfo(description="Query text to search pages")),
)

class ConfluenceAPIWrapper(BaseModel):
    base_url: str
    api_key: Optional[str] = None,
    username: Optional[str] = None
    token: Optional[str] = None
    cloud: Optional[bool] = True
    limit: Optional[int] = 5
    space: Optional[str] = None
    max_pages: Optional[int] = 10
    content_format: Optional[ContentFormat] = ContentFormat.VIEW
    include_attachments: Optional[bool] = False
    include_comments: Optional[bool] = False
    include_restricted_content: Optional[bool] = False
    number_of_retries: Optional[int] = 3
    min_retry_seconds: Optional[int] = 2
    max_retry_seconds: Optional[int] = 10
    keep_markdown_format: Optional[bool] = True
    ocr_languages: Optional[str] = None
    keep_newlines: Optional[bool] = True

    @root_validator()
    def validate_toolkit(cls, values):
        try:
            from atlassian import Confluence  # noqa: F401
        except ImportError:
            raise ImportError(
                "`atlassian` package not found, please run "
                "`pip install atlassian-python-api`"
            )

        url = values['base_url']
        api_key = values.get('api_key')
        username = values.get('username')
        token = values.get('token')
        cloud = values.get('cloud')
        if token:
            values['client'] = Confluence(url=url, token=token, cloud=cloud)
        else:
            values['client'] = Confluence(url=url,username=username, password=api_key, cloud=cloud)
        return values

    def create_page(self, title: str, body: str, space: str = None, parent_id: str = None, representation: str = 'storage'):
        """ Creates a page in the Confluence space. Represents content in html (storage) or wiki (wiki) formats """
        # normal user flow: put pages in the Space Home, not in the root of the Space
        user_space = space if space else self.space
        # logger.info(f"Page will be created within the space ${user_space}")
        parent_id_filled = parent_id if parent_id else self.client.get_space(user_space)['homepage']['id']
        status = self.client.create_page(space=user_space, title=title, body=body, parent_id=parent_id_filled, representation=representation)
        logger.info(f"Page created: {status['_links']['base'] + status['_links']['webui']}")
        page_details = {
            'title': status['title'],
            'id': status['id'],
            'space key': status['space']['key'],
            'author': status['version']['by']['displayName'],
            'link': status['_links']['base'] + status['_links']['webui']
        }
        return f"The page '{title}' was created under the parent page '{parent_id_filled}': '{status['_links']['base'] + status['_links']['webui']}'. \nDetails: {str(page_details)}"

    def create_pages(self, pages_info: dict, space: str = None, parent_id: str = None):
        """ Creates a batch of pages in the Confluence space."""
        statuses = []
        user_space = space if space else self.space
        logger.info(f"Pages will be created within the space ${user_space}")
        # duplicate action to avoid extra api calls in downstream function
        parent_id_filled = parent_id if parent_id else self.client.get_space(user_space)['homepage']['id']
        for title, body in pages_info.items():
            status = self.create_page(title=title, body=body, parent_id=parent_id_filled, space=user_space)
            statuses.append(status)
        return statuses

    def delete_page(self, page_id, recursive=False):
        """Deletes a page by its defined page_id and considering recursive flag: child entities will be removed as well if it is True"""
        logger.info(f"Remove page '{page_id}', recursively: {recursive}")
        self.client.remove_page(page_id=page_id, recursive=recursive)
        return f"Page with page_id: '{page_id}' was removed."

    def get_page_tree(self, page_id: str):
        """ Gets page tree for the Confluence space """
        descendant_pages = self.get_all_descendants(page_id)  # Pass None as the parent for the root
        for page in descendant_pages:
            logger.info(f"Page ID: {page['id']}, Title: {page['title']}, Parent ID: {page['parent_id']}")
        descendants = {page['id']: (page['title'], page['parent_id']) for page in descendant_pages}
        return f"The list of pages under the '{page_id}' was extracted: {descendants}"

    def get_all_descendants(self, page_id: str):
        """ Recursively gets all descendant pages of a given page. """
        descendants = []
        limit = 100
        start = 0

        while True:
            children = self.client.get_page_child_by_type(page_id, type='page', start=start, limit=limit)
            if not children:
                break
            for child in children:
                child_info = {'id': child['id'], 'title': child['title'], 'parent_id': page_id}
                descendants.append(child_info)
                descendants.extend(self.get_all_descendants(child['id']))
            start += limit

        return descendants

    def page_exists(self, title: str):
        """ Checks if a page exists in the Confluence space."""
        status = self.client.page_exists(space=self.space, title=title)
        return status
    
    def get_pages_with_label(self, label: str):
        """ Gets pages with specific label in the Confluence space."""
        start = 0
        content = []
        for _ in range(self.max_pages // self.limit):
            pages = self.client.get_all_pages_by_label(label, start=start, limit=self.limit)
            if not pages:
                break
            content += [page.page_content for page in self.get_pages_by_id([page["id"] for page in pages])]
            start += self.limit
        return "\n".join(content)

    
    def is_public_page(self, page: dict) -> bool:
        """Check if a page is publicly accessible."""
        restrictions = self.client.get_all_restrictions_for_content(page["id"])

        return (
            page["status"] == "current"
            and not restrictions["read"]["restrictions"]["user"]["results"]
            and not restrictions["read"]["restrictions"]["group"]["results"]
        )

    def get_pages_by_id(self, page_ids: List[str]):
        """ Gets pages by id in the Confluence space."""
        for page_id in page_ids:
            get_page = retry(
                reraise=True,
                stop=stop_after_attempt(
                    self.number_of_retries  # type: ignore[arg-type]
                ),
                wait=wait_exponential(
                    multiplier=1,  # type: ignore[arg-type]
                    min=self.min_retry_seconds,  # type: ignore[arg-type]
                    max=self.max_retry_seconds,  # type: ignore[arg-type]
                ),
                before_sleep=before_sleep_log(logger, logging.WARNING),
            )(self.client.get_page_by_id)
            page = get_page(
                page_id=page_id, expand=f"{self.content_format.value},version"
            )
            if not self.include_restricted_content and not self.is_public_page(page):
                continue
            yield self.process_page(page)
    
    def search_pages(self, query: str):
        """Search pages in Confluence by query text in title or body."""
        start = 0
        content = []
        if not self.space:
            cql = f'(type=page) and (title~"{query}" or text~"{query}")'
        else:
            cql = f'(type=page and space={self.space}) and (title~"{query}" or text~"{query}")'
        for _ in range(self.max_pages // self.limit):
            pages = self.client.cql(cql, start=0, limit=self.limit).get("results", [])
            if not pages:
                break
            content += [page.page_content for page in self.get_pages_by_id([page['content']["id"] for page in pages])]
            start += self.limit
        return "\n".join(content)
    
    def process_page(self, page: dict) -> Document:
        
        if self.keep_markdown_format:
            try:
                from markdownify import markdownify
            except ImportError:
                raise ImportError(
                    "`markdownify` package not found, please run "
                    "`pip install markdownify`"
                )
        if self.include_comments or not self.keep_markdown_format:
            try:
                from bs4 import BeautifulSoup
            except ImportError:
                raise ImportError(
                    "`beautifulsoup4` package not found, please run "
                    "`pip install beautifulsoup4`"
                )
        if self.include_attachments:
            attachment_texts = self.process_attachment(page["id"], self.ocr_languages)
        else:
            attachment_texts = []

        content = self.content_format.get_content(page)
        if self.keep_markdown_format:
            # Use markdownify to keep the page Markdown style
            text = markdownify(content, heading_style="ATX") + "".join(attachment_texts)

        else:
            if self.keep_newlines:
                text = BeautifulSoup(
                    content.replace("</p>", "\n</p>").replace("<br />", "\n"), "lxml"
                ).get_text(" ") + "".join(attachment_texts)
            else:
                text = BeautifulSoup(content, "lxml").get_text(
                    " ", strip=True
                ) + "".join(attachment_texts)

        if self.include_comments:
            comments = self.client.get_page_comments(
                page["id"], expand="body.view.value", depth="all"
            )["results"]
            comment_texts = [
                BeautifulSoup(comment["body"]["view"]["value"], "lxml").get_text(
                    " ", strip=True
                )
                for comment in comments
            ]
            text = text + "".join(comment_texts)

        metadata = {
            "title": page["title"],
            "id": page["id"],
            "source": self.base_url.strip("/") + page["_links"]["webui"],
        }

        if "version" in page and "when" in page["version"]:
            metadata["when"] = page["version"]["when"]

        return Document(
            page_content=text,
            metadata=metadata,
        )
    
    def process_attachment(
        self,
        page_id: str,
        ocr_languages: Optional[str] = None,
    ) -> List[str]:
        try:
            from PIL import Image  # noqa: F401
        except ImportError:
            raise ImportError(
                "`Pillow` package not found, " "please run `pip install Pillow`"
            )

        # depending on setup you may also need to set the correct path for
        # poppler and tesseract
        attachments = self.client.get_attachments_from_content(page_id)["results"]
        texts = []
        for attachment in attachments:
            media_type = attachment["metadata"]["mediaType"]
            absolute_url = self.base_url + attachment["_links"]["download"]
            title = attachment["title"]
            try:
                if media_type == "application/pdf":
                    text = title + self.process_pdf(absolute_url, ocr_languages)
                elif (
                    media_type == "image/png"
                    or media_type == "image/jpg"
                    or media_type == "image/jpeg"
                ):
                    text = title + self.process_image(absolute_url, ocr_languages)
                elif (
                    media_type == "application/vnd.openxmlformats-officedocument"
                    ".wordprocessingml.document"
                ):
                    text = title + self.process_doc(absolute_url)
                elif media_type == "application/vnd.ms-excel":
                    text = title + self.process_xls(absolute_url)
                elif media_type == "image/svg+xml":
                    text = title + self.process_svg(absolute_url, ocr_languages)
                else:
                    continue
                texts.append(text)
            except requests.HTTPError as e:
                if e.response.status_code == 404:
                    print(f"Attachment not found at {absolute_url}")  # noqa: T201
                    continue
                else:
                    raise

        return texts
    
    def get_available_tools(self):
        return [
            {
                "name": "create_page",
                "ref": self.create_page,
                "description": self.create_page.__doc__,
                "args_schema": createPage,
            },
            {
                "name": "create_pages",
                "ref": self.create_pages,
                "description": self.create_pages.__doc__,
                "args_schema": createPages,
            },
            {
                "name": "get_page_tree",
                "ref": self.get_page_tree,
                "description": self.get_page_tree.__doc__,
                "args_schema": getPageTree,
            },
            # {
            #     "name": "page_exists",
            #     "ref": self.page_exists,
            #     "description": self.page_exists.__doc__,
            #     "args_schema": pageExists,
            # },
            {
                "name": "get_pages_with_label",
                "ref": self.get_pages_with_label,
                "description": self.get_pages_with_label.__doc__,
                "args_schema": getPagesWithLabel,
            },
            {
                "name": "search_pages",
                "ref": self.search_pages,
                "description": self.search_pages.__doc__,
                "args_schema": searchPages,
            },
            {
                "name": "delete_page",
                "ref": self.delete_page,
                "description": self.delete_page.__doc__,
                "args_schema": deletePage,
            }
        ]
    
    def run(self, mode: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")