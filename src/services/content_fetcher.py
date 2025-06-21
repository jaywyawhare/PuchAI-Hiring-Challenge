"""
Content fetching service for web scraping and content extraction.
"""
import markdownify
import readabilipy
from typing import Tuple
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR
from ..config import REQUEST_TIMEOUT, USER_AGENT
from ..models.base import BaseAPIClient
import logging

logger = logging.getLogger(__name__)


class ContentFetcher(BaseAPIClient):
    """
    A utility class for fetching and processing webpage content.
    """
    
    def __init__(self):
        super().__init__(timeout=REQUEST_TIMEOUT)
    
    async def fetch_url(
        self,
        url: str,
        user_agent: str = USER_AGENT,
        force_raw: bool = False,
    ) -> Tuple[str, str]:
        """
        Fetch the URL and return the content in a form ready for the LLM, as well as a prefix string with status information.
        """
        from httpx import AsyncClient, HTTPError

        self.log_info(f"Fetching URL: {url}")
        async with AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    follow_redirects=True,
                    headers={"User-Agent": user_agent},
                    timeout=self.timeout,
                )
            except HTTPError as e:
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR, message=f"Failed to fetch {url}: {e!r}"
                    )
                )
            if response.status_code >= 400:
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message=f"Failed to fetch {url} - status code {response.status_code}",
                    )
                )

            page_raw = response.text

        content_type = response.headers.get("content-type", "")
        is_page_html = (
            "<html" in page_raw[:100] or "text/html" in content_type or not content_type
        )

        if is_page_html and not force_raw:
            return self.extract_content_from_html(page_raw), ""

        return (
            page_raw,
            f"Content type {content_type} cannot be simplified to markdown, but here is the raw content:\n",
        )

    @staticmethod
    def extract_content_from_html(html: str) -> str:
        """Extract and convert HTML content to Markdown format.

        Args:
            html: Raw HTML content to process

        Returns:
            Simplified markdown version of the content
        """
        ret = readabilipy.simple_json.simple_json_from_html_string(
            html, use_readability=True
        )
        if not ret["content"]:
            return "<e>Page failed to be simplified from HTML</e>"
        content = markdownify.markdownify(
            ret["content"],
            heading_style=markdownify.ATX,
        )
        return content
