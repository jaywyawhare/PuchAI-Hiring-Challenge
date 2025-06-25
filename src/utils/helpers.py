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

async def translate_to_english(text: str, source_lang: str = 'auto') -> str:
    """
    Translate text to English using Google Translate without API.
    
    Args:
        text: Text to translate
        source_lang: Source language code (default: auto-detect)
        
    Returns:
        Translated text in English
    """
    if not text or source_lang == 'en':
        return text
        
    try:
        url = 'https://translate.googleapis.com/translate_a/single'
        params = {
            'client': 'gtx',
            'sl': source_lang,
            'tl': 'en',
            'dt': 't',
            'q': text
        }
        
        full_url = f"{url}?{urlencode(params)}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(full_url)
            if response.status_code != 200:
                logger.warning(f"Translation failed: {response.status_code}")
                return text
                
            # Parse the response
            data = response.json()
            if not data:
                return text
                
            # Extract translated text from the response
            translated = ''
            for segment in data[0]:
                if segment[0]:
                    translated += segment[0]
                    
            return translated or text
            
    except Exception as e:
        logger.warning(f"Translation error: {str(e)}")
        return text  # Return original text if translation fails

async def translate_to_english(text: str, detect_threshold: float = 0.8) -> str:
    """
    Translates text to English if it's not already in English.
    Uses Google Translate without API key through an unofficial API.
    
    Args:
        text: Text to translate
        detect_threshold: Confidence threshold for English detection (0-1)
        
    Returns:
        Translated text if input was non-English, original text otherwise
    """
    # Quick check for English using regex pattern
    # Check if text contains mostly English characters and common words
    english_pattern = re.compile(r'^[a-zA-Z0-9\s\.,!?\'-]+$')
    common_eng_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
    words = set(text.lower().split())
    
    # If text matches English pattern and contains common English words, return as is
    if (english_pattern.match(text) and 
        len(words.intersection(common_eng_words)) / len(words) >= detect_threshold):
        return text
        
    try:
        # Unofficial Google Translate API endpoint
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",  # Source language (auto-detect)
            "tl": "en",    # Target language (English)
            "dt": "t",     # Return type (text)
            "q": text      # Text to translate
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                # Extract translated text from response
                translated = ""
                for item in response.json()[0]:
                    if item[0]:
                        translated += item[0]
                return translated
            
    except Exception as e:
        logger.warning(f"Translation failed: {e}")
        return text  # Return original text if translation fails
        
    return text  # Return original text if anything goes wrong
