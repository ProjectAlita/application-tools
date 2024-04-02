import logging
import requests
from typing import List, Optional, Any
from langchain_core.documents import Document
from langchain_core.pydantic_v1 import root_validator, BaseModel, Field
from langchain_community.document_loaders.confluence import ContentFormat
from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_exponential,
)


logger = logging.getLogger(__name__)


class createPage(BaseModel):
    title: str = Field(..., title="Title of the page")
    body: str = Field(..., title="Body of the page")

class pageExists(BaseModel):
    title: str = Field(..., title="Title of the page")
    
class getPagesWithLabel(BaseModel):
    label: str = Field(..., title="Label of the pages")

class searchPages(BaseModel):
    query: str = Field(..., title="Query text to search pages")
    

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
    
    def create_page(self, title: str, body: str):
        """ Creates a page in the Confluence space."""
        status = self.client.create_page(space=self.space, title=title, body=body)
        return status
    
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
        cql = f'(type=page and space={self.space}) and (title~"{query}" or text~"{query}")'
        for _ in range(self.max_pages // self.limit):
            pages = self.client.cql(cql, start=0, limit=self.limit).get("results", [])
            print(pages)
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
                "name": "page_exists",
                "ref": self.page_exists,
                "description": self.page_exists.__doc__,
                "args_schema": pageExists,
            },
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
            }
        ]
    
    def run(self, mode: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")