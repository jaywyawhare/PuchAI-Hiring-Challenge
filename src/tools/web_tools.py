"""
Web fetching and information search tools.
"""
from typing import Annotated, Optional
from pydantic import AnyUrl, Field, validator
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR, INVALID_PARAMS, TextContent
import httpx
import json
import re
from urllib.parse import urlparse, urljoin
import openai
import logging

logger = logging.getLogger(__name__)


class RichToolDescription(openai.BaseModel):
    """Rich tool description model for MCP server compatibility."""
    description: str
    use_when: str
    side_effects: Optional[str] = None


def register_web_tools(mcp):
    """Register web-related tools with the MCP server."""
    
    logger.info("Registering web tools...")
    
    def validate_url(url: str) -> tuple[bool, str]:
        """Validate and clean URL."""
        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                url = f"https://{url}"
                parsed = urlparse(url)
            if not parsed.netloc:
                return False, "Invalid URL format"
            return True, url
        except Exception:
            return False, "Invalid URL format"

    def format_error_response(error_msg: str, suggestions: list[str] = None) -> list[TextContent]:
        """Format error response with suggestions."""
        response = [f"❌ Error: {error_msg}"]
        if suggestions:
            response.append("\n💡 Suggestions:")
            response.extend([f"- {s}" for s in suggestions])
        return [TextContent(type="text", text="\n".join(response))]

    FetchToolDescription = RichToolDescription(
        description="Fetch a URL and return its content with optional truncation.",
        use_when="When you need to retrieve and process content from a specific URL, summarize web articles, or extract information from websites.",
        side_effects="Makes an HTTP request to the specified URL and may be subject to rate limiting or blocking by the target website.",
    )

    @mcp.tool(description=FetchToolDescription.model_dump_json())
    async def fetch(
        url: Annotated[AnyUrl, Field(description="URL to fetch")],
        max_length: Annotated[int, Field(default=5000, gt=0, lt=1000000)] = 5000,
        start_index: Annotated[int, Field(default=0, ge=0)] = 0,
        raw: Annotated[bool, Field(default=False)] = False,
    ) -> list[TextContent]:
        """Fetch a URL and return its content."""
        from ..utils.helpers import ContentFetcher
        
        logger.info(f"Fetching URL: {url}")
        url_str = str(url).strip()
        is_valid, url_or_error = validate_url(url_str)
        if not is_valid:
            return format_error_response(url_or_error, [
                "Make sure the URL starts with http:// or https://",
                "Check for typos in the domain name",
                "Try using search_information_on_internet instead"
            ])

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:  # Set explicit timeout
                content, prefix = await ContentFetcher.fetch_url(url_or_error, force_raw=raw)
                if not content:
                    raise ValueError("No content received")
                
                # Format content with length info
                original_length = len(content)
                if start_index >= original_length:
                    return format_error_response("No more content available", [
                        "Try starting from index 0",
                        f"Maximum available content length: {original_length}"
                    ])
                
                truncated_content = content[start_index:start_index + max_length]
                if not truncated_content:
                    return format_error_response("No content available at specified index", [
                        "Try starting from index 0",
                        f"Maximum available content length: {original_length}"
                    ])
                
                response = [f"📄 Contents of {url_or_error}:"]
                if prefix:
                    response.append(f"\n{prefix}")
                response.append(f"\n{truncated_content}")
                
                # Add continuation info if needed
                remaining = original_length - (start_index + len(truncated_content))
                if remaining > 0:
                    next_start = start_index + len(truncated_content)
                    response.append(f"\n\n📝 Content truncated. {remaining} characters remaining.")
                    response.append(f"To continue reading, use: fetch(url='{url_or_error}', start_index={next_start})")
                
                return [TextContent(type="text", text="\n".join(response))]
                
        except httpx.TimeoutError:
            return format_error_response("Request timed out", [
                "The website might be slow or unresponsive",
                "Try again later",
                "Try using search_information_on_internet instead"
            ])
        except httpx.HTTPError as e:
            return format_error_response(f"Failed to fetch URL: {str(e)}", [
                "Check if the URL is accessible in your browser",
                "The website might be blocking automated access",
                "Try using search_information_on_internet instead"
            ])
        except Exception as e:
            return format_error_response(str(e), [
                "The URL might be invalid or inaccessible",
                "Try using search_information_on_internet instead"
            ])

    SearchInternetToolDescription = RichToolDescription(
        description="Search the internet for information using DuckDuckGo API.",
        use_when="When you need to find current information, news, or general knowledge from the internet that isn't available in a specific URL.",
        side_effects="Makes API calls to DuckDuckGo search service and may be subject to rate limiting.",
    )

    @mcp.tool(description=SearchInternetToolDescription.model_dump_json())
    async def search_information_on_internet(
        query: Annotated[str, Field(description="Search query to look up on the internet")],
        max_results: Annotated[int, Field(default=5, description="Maximum number of results to return", ge=1, le=10)] = 5
    ) -> list[TextContent]:
        """Search for information on the internet using DuckDuckGo."""
        try:
            logger.info(f"Searching internet for: {query}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        'q': query,
                        'format': 'json',
                        'no_html': '1',
                        'skip_disambig': '1'
                    }
                )
                
                if response.status_code != 200:
                    raise McpError(
                        ErrorData(
                            code=INTERNAL_ERROR,
                            message=f"Search API returned status code: {response.status_code}"
                        )
                    )
                
                data = response.json()
                sections = []
                
                # Handle direct answers with better formatting
                if data.get('Abstract') or data.get('AbstractText'):
                    abstract = data.get('Abstract') or data.get('AbstractText')
                    direct_answer = ["**Direct Answer:**", abstract]
                    if data.get('AbstractURL'):
                        direct_answer.extend([f"Source: {data['AbstractURL']}", ""])
                    sections.append("\n".join(direct_answer))
                
                # Improved topic handling with better categorization
                if data.get('RelatedTopics'):
                    topics = []
                    categories = {}
                    
                    for topic in data['RelatedTopics']:
                        if not isinstance(topic, dict):
                            continue
                            
                        category = 'Related'
                        if 'Name' in topic:
                            category = topic['Name']
                            
                        if 'Topics' in topic:
                            for subtopic in topic['Topics']:
                                if 'Text' in subtopic:
                                    if category not in categories:
                                        categories[category] = []
                                    categories[category].append((
                                        subtopic['Text'],
                                        subtopic.get('FirstURL', '')
                                    ))
                        elif 'Text' in topic:
                            if category not in categories:
                                categories[category] = []
                            categories[category].append((
                                topic['Text'],
                                topic.get('FirstURL', '')
                            ))
                    
                    # Format topics by category
                    for category, items in categories.items():
                        if items:
                            category_topics = [f"\n**{category} Information:**"]
                            for i, (text, url) in enumerate(items[:max_results], 1):
                                category_topics.append(f"{i}. {text}")
                                if url:
                                    category_topics.append(f"   Source: {url}")
                            sections.append("\n".join(category_topics))
                
                if not sections:
                    search_url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}"
                    sections.append(f"No direct information found for '{query}'.\nTry searching here: {search_url}")
                
                return [TextContent(type="text", text=f"Search results for '{query}':\n\n" + "\n\n".join(sections))]
                
        except httpx.TimeoutError:
            logger.error("Search request timed out")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message="Search request timed out. Please try again."
                )
            )
        except Exception as e:
            logger.error(f"Error in search_information_on_internet: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Error searching for information: {str(e)}"
                )
            )

    HelpMenuToolDescription = RichToolDescription(
        description="Display comprehensive help information for all available tools.",
        use_when="User requests help or information about available features.",
        side_effects="Returns a formatted help menu with all tools and capabilities.",
    )

    @mcp.tool(description=HelpMenuToolDescription.model_dump_json())
    async def get_help_menu() -> list[TextContent]:
        """Get comprehensive help information about Chup AI's available tools and capabilities."""
        help_text = """
# 🤖 Chup AI - WhatsApp Assistant Help Menu

Hi! I'm **Chup AI**, your intelligent WhatsApp assistant. Here's everything I can help you with:

## � About Me  
- **`resume()`** - Get Arinjay's professional resume and background
- **`validate()`** - System validation tool for Chup AI
- **`get_help_menu()`** - Show this help menu anytime

## 🌐 Web & Information Tools
- **`fetch(url)`** - Get content from any website, article, or webpage
  💡 *Just send me a link and I'll summarize it for you!*
  
- **`search_information_on_internet(query)`** - Search the internet for information
  💡 *Ask me anything: "What's the weather in Mumbai?" or "Latest news about AI"*

## 🚂 Indian Railway Tools (Live Data)
- **`get_live_train_status(train_number)`** - Get real-time train information
  💡 *Example: "Check train 12345 status"*
  
- **`get_trains_between_stations(from_station, to_station)`** - Find trains between cities
  💡 *Example: "Trains from Delhi to Mumbai" (use station codes like NDLS, BCT)*
  
- **`get_pnr_status_tool(pnr_number)`** - Check your PNR booking status
  💡 *Just send your 10-digit PNR number*
  
- **`get_train_schedule_tool(train_number)`** - Get complete train route and timings
  💡 *See all stations and arrival/departure times*
  
- **`get_station_live_status(station_code)`** - Live status of all trains at a station
  💡 *Check what's happening at any railway station*

## 🎵 Music & Entertainment Tools
- **`get_song_name_links(song_name, artist)`** - Find songs on all platforms
  💡 *Get Spotify, YouTube, Apple Music links for any song*
  
- **`get_music_recommendations(genre, mood, artist)`** - Get personalized music suggestions
  💡 *"Recommend chill songs" or "Songs like Arijit Singh"*

- **`get_youtube_music_stream(video_url)`** - Get audio streams from YouTube videos
  💡 *Convert YouTube videos to audio for streaming*

- **`search_and_stream_music(query)`** - Search and stream music from YouTube
  💡 *Find and get streaming links for any song*

- **`download_youtube_audio(video_url)`** - Download audio from YouTube
  💡 *Save YouTube videos as audio files*

## 🎯 How to Use Chup AI on WhatsApp

**For Quick Info:**
- "Show me Arinjay's resume"
- "Search for latest AI news"  
- "Check train 12951 status"

**For Links:**
- Send any website URL and I'll summarize it
- "Find Bohemian Rhapsody on all platforms"

**For Travel:**
- "Trains from NDLS to BCT tomorrow"
- "PNR status 1234567890"
- "Live status of NDLS station"

**For Music:**
- "Recommend sad songs"
- "Get YouTube link for this song"
- "Songs by Kishore Kumar"

## ✨ Smart Features
- **Live Railway Data** - Real-time info from Indian Railways
- **Multi-Platform Music** - Spotify, YouTube, Apple Music, etc.
- **Smart Web Processing** - Clean, readable content from any website
- **WhatsApp Optimized** - Responses formatted for mobile messaging
- **YouTube Integration** - Stream, download, and convert videos to audio

## � Security & Privacy
- Secure bearer token authentication
- No personal data stored
- All railway data from official sources
- Music links from legitimate platforms

## � Pro Tips for WhatsApp Users
- Send clear, specific requests for better results
- Use station codes (NDLS, BCT) for railway queries
- Share direct links for website content
- Ask follow-up questions - I understand context!

**I'm here to make your WhatsApp experience smarter and more helpful! 🚀**

*Chup AI Version 1.0.0 | Powered by PuchAI | Optimized for WhatsApp*
        """
        return [TextContent(type="text", text=help_text.strip())]
