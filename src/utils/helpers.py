"""
Utility functions for the MCP server.
"""
import markdownify
import readabilipy
from pathlib import Path
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR
from ..config import REQUEST_TIMEOUT, USER_AGENT
import logging
import httpx
from urllib.parse import urlencode
import re
from typing import Optional

logger = logging.getLogger(__name__)


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

        logger.info(f"Fetching URL: {url}")
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
    
    logger.info(f"Loading resume from: {RESUME_PATH}")
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

async def translate_to_english(text: str, source_lang: str = "auto") -> str:
    """
    Translate text to English using Google Translate API.
    
    Args:
        text: Text to translate
        source_lang: Source language code (use 'auto' for auto-detection)
        
    Returns:
        Translated text in English
    """
    if not text:
        return text
        
    try:
        # Use httpx for async HTTP requests
        async with httpx.AsyncClient() as client:
            params = {
                "client": "gtx",
                "sl": source_lang,
                "tl": "en",
                "dt": "t",
                "q": text,
            }
            
            url = f"https://translate.googleapis.com/translate_a/single?{urlencode(params)}"
            response = await client.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            # Parse response and extract translated text
            data = response.json()
            translated = "".join(item[0] for item in data[0] if item[0])
            
            logger.debug(f"Translated '{text}' ({source_lang}) -> '{translated}' (en)")
            return translated
            
    except Exception as e:
        logger.warning(f"Translation failed for '{text}': {e}")
        return text  # Fallback to original text if translation fails
