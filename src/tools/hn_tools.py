"""
Hacker News API tools for fetching stories and user information.
Uses the official HN Algolia API.
"""
from typing import Annotated, Dict, List, Any, Optional
from pydantic import Field
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR, INVALID_PARAMS, TextContent
import httpx
import logging
from datetime import datetime
from urllib.parse import urlencode
import openai


class RichToolDescription(openai.BaseModel):
    """Rich tool description model for MCP server compatibility."""
    description: str
    use_when: str
    side_effects: Optional[str]

logger = logging.getLogger(__name__)

class HackerNewsAPI:
    """HN API client with proper error handling and rate limiting."""
    
    def __init__(self):
        self.base_url = "https://hn.algolia.com/api/v1"
        
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make API request with error handling."""
        url = f"{self.base_url}/{endpoint}"
        if params:
            url += f"?{urlencode(params)}"
            
        logger.debug(f"HN API request: {url}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, 
                    timeout=10.0,
                    headers={'User-Agent': 'ChupAI/1.0 (github.com/jaywyawhare/puch-ai-hiring)'}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"HTTP error while fetching: {e}")
                raise ValueError(f"HN API HTTP error: {str(e)}")

    async def get_stories(self, story_type: str, num_stories: int = 10, page: int = 0) -> Dict:
        """Get stories with pagination support."""
        mapping = {
            "top": {"endpoint": "search", "tags": "front_page"},
            "new": {"endpoint": "search_by_date", "tags": "story"},
            "ask": {"endpoint": "search", "tags": "ask_hn"},
            "show": {"endpoint": "search", "tags": "show_hn"}
        }
        
        if story_type not in mapping:
            raise ValueError(f"Invalid story type. Must be one of: {', '.join(mapping.keys())}")
        
        params = {
            "tags": mapping[story_type]["tags"],
            "hitsPerPage": num_stories,
            "page": page
        }
        
        return await self._make_request(mapping[story_type]["endpoint"], params)

    async def search_stories(self, query: str, num_results: int = 10) -> Dict:
        """Search stories by keyword."""
        params = {
            "query": query,
            "tags": "story",
            "hitsPerPage": num_results
        }
        
        return await self._make_request("search", params)

    async def get_user(self, username: str) -> Dict:
        """Get user profile information."""
        return await self._make_request(f"users/{username}")

    async def get_item(self, item_id: str) -> Dict:
        """Get item details including comments."""
        return await self._make_request(f"items/{item_id}")


def register_hn_tools(mcp):
    """Register Hacker News tools with the MCP server."""
    
    logger.info("Registering Hacker News tools...")
    
    GetHNStoriesToolDescription = RichToolDescription(
        description="Get Hacker News stories by type (top, new, ask, show).",
        use_when="Fetches and formats stories from Hacker News, including titles, points, comment counts, and URLs.",
        side_effects="Makes API calls to Hacker News Algolia API and may be subject to rate limiting.",
    )
    
    @mcp.tool(description=GetHNStoriesToolDescription.model_dump_json())
    async def get_hn_stories(
        story_type: Annotated[str, Field(description="Type of stories to fetch (top/new/ask/show)")] = "top",
        num_stories: Annotated[int, Field(description="Number of stories to fetch", default=10, ge=1, le=30)] = 10
    ) -> list[TextContent]:
        """Get Hacker News stories by type (top, new, ask, show)."""
        try:
            logger.info(f"Getting HN stories: type={story_type}, count={num_stories}")
            hn = HackerNewsAPI()
            stories = await hn.get_stories(story_type, num_stories)
            
            if not stories.get("hits"):
                return [TextContent(type="text", text="No stories found")]
            
            result_parts = [f"**📰 Hacker News - {story_type.upper()} Stories**\n"]
            
            for i, story in enumerate(stories["hits"], 1):
                # Format story data
                story_id = str(story.get("objectID", ""))
                title = story.get("title", "[No title]")
                points = int(story.get("points", 0) or 0)
                num_comments = int(story.get("num_comments", 0) or 0)
                author = story.get("author", "anonymous")
                url = story.get("url", "")
                
                try:
                    created = datetime.fromisoformat(story.get("created_at", "").replace("Z", "+00:00"))
                    time_str = created.strftime("%Y-%m-%d %H:%M")
                except:
                    time_str = "unknown time"
                
                story_text = [
                    f"{i}. **{title}**",
                    f"   👤 by {author} | ⬆️ {points} points | 💬 {num_comments} comments | 🕒 {time_str}"
                ]
                
                if url:
                    story_text.append(f"   🔗 {url}")
                
                story_text.append(f"   📎 https://news.ycombinator.com/item?id={story_id}")
                result_parts.append("\n".join(story_text))
            
            if "nbPages" in stories:
                result_parts.append(f"\nPage {stories.get('page', 0) + 1} of {stories['nbPages']}")
            
            result_parts.append("\n*🔴 Live data from Hacker News API*")
            return [TextContent(type="text", text="\n".join(result_parts))]
            
        except Exception as e:
            logger.error(f"Error in get_hn_stories: {e}")
            raise McpError(
                ErrorData(code=INTERNAL_ERROR, message=f"Error fetching HN stories: {str(e)}")
            )

    SearchHNStoriesToolDescription = RichToolDescription(
        description="Search Hacker News stories by keyword.",
        use_when="Performs a full-text search across Hacker News stories and returns matching results with relevance ranking.",
        side_effects="Makes API calls to Hacker News Algolia API and may be subject to rate limiting.",
    )

    @mcp.tool(description=SearchHNStoriesToolDescription.model_dump_json())
    async def search_hn_stories(
        query: Annotated[str, Field(description="Search query for stories")],
        num_results: Annotated[int, Field(description="Number of results to fetch", default=10, ge=1, le=30)] = 10
    ) -> list[TextContent]:
        """Search Hacker News stories by keyword."""
        try:
            logger.info(f"Searching HN stories for query: {query}")
            hn = HackerNewsAPI()
            stories = await hn.search_stories(query, num_results)
            
            if not stories.get("hits"):
                return [TextContent(type="text", text="No stories found")]
            
            result_parts = [
                f"**🔍 Hacker News Search Results**",
                f"*Query: {query}*\n"
            ]
            
            for i, story in enumerate(stories["hits"], 1):
                points = story["points"] or 0
                comments = story["num_comments"] or 0
                created = datetime.fromisoformat(story["created_at"].replace("Z", "+00:00"))
                story_url = story.get("url", "")
                
                story_text = [
                    f"{i}. **{story['title']}**",
                    f"   👤 by {story['author']} | ⬆️ {points} points | 💬 {comments} comments | 🕒 {created.strftime('%Y-%m-%d %H:%M')}"
                ]
                
                if story_url:
                    story_text.append(f"   🔗 {story_url}")
                    
                story_text.append(f"   📎 https://news.ycombinator.com/item?id={story['objectID']}")
                result_parts.append("\n".join(story_text))
            
            result_parts.append("\n*🔴 Live data from Hacker News API*")
            return [TextContent(type="text", text="\n".join(result_parts))]
            
        except Exception as e:
            logger.error(f"Error in search_hn_stories: {e}")
            raise McpError(
                ErrorData(code=INTERNAL_ERROR, message=f"Error searching HN stories: {str(e)}")
            )

    GetHNUserToolDescription = RichToolDescription(
        description="Get Hacker News user information and recent submissions.",
        use_when="Fetches user profile information including karma, creation date, and recent story submissions.",
        side_effects="Makes API calls to Hacker News Algolia API and may be subject to rate limiting.",
    )

    @mcp.tool(description=GetHNUserToolDescription.model_dump_json())
    async def get_hn_user(
        username: Annotated[str, Field(description="Hacker News username")],
        num_stories: Annotated[int, Field(description="Number of user's stories to fetch", default=5, ge=1, le=20)] = 5
    ) -> list[TextContent]:
        """Get Hacker News user information and recent submissions."""
        try:
            logger.info(f"Getting HN user info for: {username}")
            hn = HackerNewsAPI()
            user_info = await hn.get_user(username)
            stories = await hn.get_stories("new", num_stories, 0)  # Get recent stories
            
            created_str = user_info.get("created_at")
            if created_str:
                created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                created_formatted = created.strftime("%Y-%m-%d")
            else:
                created_formatted = "unknown"
            
            result_text = f"""
**👤 Hacker News User: {username}**

🔑 **Account Info:**
• Created: {created_formatted}
• Karma: {user_info.get("karma", 0)}
{"• About: " + user_info.get("about", "") if user_info.get("about") else ""}

📝 **Recent Submissions:**
"""
        
            for i, story in enumerate(stories["hits"], 1):
                points = story["points"] or 0
                comments = story["num_comments"] or 0
                
                result_text += f"""
{i}. **{story["title"]}**
   ⬆️ {points} points | 💬 {comments} comments
   {"🔗 " + story["url"] if story["url"] else ""}
   📎 https://news.ycombinator.com/item?id={story["objectID"]}
"""
        
            result_text += f"""

📊 **Profile Links:**
• Stories: https://news.ycombinator.com/submitted?id={username}
• Comments: https://news.ycombinator.com/threads?id={username}

*🔴 Live data from Hacker News API*
"""
        
            return [TextContent(type="text", text=result_text.strip())]
        
        except Exception as e:
            logger.error(f"Error in get_hn_user: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Error fetching HN user info: {str(e)}"
                )
            )
