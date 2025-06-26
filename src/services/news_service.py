"""
News service for Hacker News integration.
"""
from typing import Dict
from ..models.base import RichToolDescription, ToolService, BaseServiceConfig
import logging

logger = logging.getLogger(__name__)


class NewsServiceConfig(BaseServiceConfig):
    """Configuration for news service."""
    hn_base_url: str = "https://hacker-news.firebaseio.com/v0"
    algolia_base_url: str = "https://hn.algolia.com/api/v1"
    max_stories: int = 30


class NewsService(ToolService):
    """News service for Hacker News integration."""
    
    def __init__(self, config: NewsServiceConfig = None):
        super().__init__("news")
        self.config = config or NewsServiceConfig()
    
    def get_tool_descriptions(self) -> Dict[str, RichToolDescription]:
        """Get tool descriptions for news service."""
        return {
            "get_hn_stories": RichToolDescription(
                description="Get Hacker News stories by type (top, new, ask, show).",
                use_when="Fetches and formats stories from Hacker News, including titles, points, comment counts, and URLs.",
                side_effects="Makes API calls to Hacker News official API and may be subject to rate limiting."
            ),
            "search_hn_stories": RichToolDescription(
                description="Search Hacker News stories by keyword.",
                use_when="Performs a full-text search across Hacker News stories and returns matching results with relevance ranking.",
                side_effects="Makes API calls to Hacker News Algolia API and may be subject to rate limiting."
            ),
            "get_hn_user": RichToolDescription(
                description="Get Hacker News user information and recent submissions.",
                use_when="Fetches user profile information including karma, creation date, and recent story submissions.",
                side_effects="Makes API calls to Hacker News official API and may be subject to rate limiting."
            )
        }
    
    def register_tools(self, mcp):
        logger.info("Registering news tools...")
        """Register news tools with the MCP server."""
        # Import the existing hacker news tools registration function
        from ..tools.hn_tools import register_hn_tools
        
        register_hn_tools(mcp)
        logger.info("News tools registered.")
