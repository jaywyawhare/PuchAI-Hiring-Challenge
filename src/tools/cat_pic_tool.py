"""
Cat picture tool for MCP server - fetches a random cat image from a free API and returns as base64.
"""
import requests
import base64
from io import BytesIO
from typing import List
from ..models.base import RichToolDescription
from mcp.types import TextContent

# Tool description for registration
CatPicToolDescription = RichToolDescription(
    description="Send a random cat image as a base64-encoded string.",
    use_when="User asks for a cat picture, cat pic, or something cute.",
    side_effects="Fetches a random cat image from a public API (cataas.com) and returns it as base64-encoded image content.",
)

def fetch_cat_pic_content() -> TextContent:
    """Fetch a random cat image and return as a TextContent with base64 data."""
    try:
        response = requests.get("https://cataas.com/cat", timeout=10)
        response.raise_for_status()
        image_bytes = BytesIO(response.content)
        encoded = base64.b64encode(image_bytes.read()).decode("utf-8")
        return TextContent(
            type="text",  # Changed from "image" to "text" for compatibility # Changed from "image" to "text" for compatibility
            text=encoded,  # base64 string in text field
            extra={"mime_type": "image/jpeg"}
        )
    except Exception as e:
        return TextContent(type="text", text=f"Failed to fetch cat image: {e}")


def register_cat_pic_tool(mcp):
    """Register the cat pic tool with the MCP server."""
    @mcp.tool(description=CatPicToolDescription.model_dump_json())
    async def get_cat_pic(
    ) -> List[TextContent]:
        """Send a random cat image as base64-encoded content."""
        return [fetch_cat_pic_content()]
