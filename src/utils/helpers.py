"""
Utility functions for the MCP server.
"""
import markdownify
import readabilipy
from pathlib import Path
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR
from ..config import REQUEST_TIMEOUT, USER_AGENT


class ContentFetcher:
    """
    A utility class for fetching and processing webpage content.
    """
    
    @classmethod
    async def fetch_url(
        cls,
        url: str,
        user_agent: str = USER_AGENT,
        force_raw: bool = False,
    ) -> tuple[str, str]:
        """
        Fetch the URL and return the content in a form ready for the LLM, as well as a prefix string with status information.
        """
        from httpx import AsyncClient, HTTPError

        async with AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    follow_redirects=True,
                    headers={"User-Agent": user_agent},
                    timeout=REQUEST_TIMEOUT,
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
            return cls.extract_content_from_html(page_raw), ""

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
            return "<error>Page failed to be simplified from HTML</error>"
        content = markdownify.markdownify(
            ret["content"],
            heading_style=markdownify.ATX,
        )
        return content


def load_resume() -> str:
    """Load resume from file."""
    from ..config import RESUME_PATH
    
    if not RESUME_PATH.exists():
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message="Resume file not found. Please create resume.md"
            )
        )
    
    resume_content = RESUME_PATH.read_text(encoding='utf-8')
    if not resume_content.strip():
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message="Resume file is empty"
            )
        )
    
    return resume_content
