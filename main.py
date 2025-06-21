from typing import Annotated, Optional
from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
import markdownify
from mcp import ErrorData, McpError
from mcp.server.auth.provider import AccessToken
from mcp.types import INTERNAL_ERROR, INVALID_PARAMS, TextContent
from openai import BaseModel
from pydantic import AnyUrl, Field
import readabilipy
from pathlib import Path
from dotenv import load_dotenv
import os
import logging

# Import tool registration functions
from src.tools.core_tools import register_core_tools
from src.tools.web_tools import register_web_tools
from src.tools.railway_tools import register_railway_tools
from src.tools.music_tools import register_music_tools
from src.tools.weather_tools import register_weather_tools
from src.tools.arxiv_tools import register_arxiv_tools
from src.tools.hn_tools import register_hn_tools

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")
MY_NUMBER = os.getenv("MY_NUMBER")

if not TOKEN or not MY_NUMBER:
    raise ValueError("TOKEN and MY_NUMBER environment variables must be set")

logger.info("Environment variables loaded successfully")

class RichToolDescription(BaseModel):
    """Rich tool description model for MCP server compatibility."""
    description: str
    use_when: str
    side_effects: Optional[str]


class SimpleBearerAuthProvider(BearerAuthProvider):
    """
    A simple BearerAuthProvider that does not require any specific configuration.
    It allows any valid bearer token to access the MCP server.
    For a more complete implementation that can authenticate dynamically generated tokens,
    please use `BearerAuthProvider` with your public key or JWKS URI.
    """

    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(
            public_key=k.public_key, jwks_uri=None, issuer=None, audience=None
        )
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(
                token=token,
                client_id="unknown",
                scopes=[],
                expires_at=None,  # No expiration for simplicity
            )
        return None


class Fetch:
    """
    A utility class for fetching and processing webpage content.
    
    Attributes:
        IGNORE_ROBOTS_TXT (bool): Flag to ignore robots.txt restrictions
        USER_AGENT (str): User agent string for HTTP requests
    """
    
    IGNORE_ROBOTS_TXT: bool = True
    USER_AGENT: str = "ChupAI/1.0 (Intelligent Assistant for Puch AI)"

    @classmethod
    async def fetch_url(
        cls,
        url: str,
        user_agent: str,
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
                    timeout=30,
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


mcp = FastMCP(
    "Chup AI - Intelligent Assistant for Puch AI",
    auth=SimpleBearerAuthProvider(TOKEN),
)

logger.info("FastMCP server initialized")

register_core_tools(mcp)
register_web_tools(mcp)
register_railway_tools(mcp)
register_music_tools(mcp)
register_weather_tools(mcp)
register_arxiv_tools(mcp)
register_hn_tools(mcp)  # Add HN tools registration

logger.info("All tools registered successfully")


async def main():
    """
    Main entry point for Chup AI MCP server.
    
    Chup AI is an intelligent assistant built for Puch AI that provides:
    - Resume and validation services
    - Web content fetching and search
    - Live Indian Railway information
    - YouTube music streaming and multi-platform music search
    - WhatsApp chatbot integration ready
    """
    logger.info("Starting Chup AI MCP server...")

    await mcp.run_async(
        "streamable-http",
        host="0.0.0.0",
        port=8085,
    )


if __name__ == "__main__":
    import asyncio
    
    logger.info("Chup AI MCP Server starting up...")
    asyncio.run(main())