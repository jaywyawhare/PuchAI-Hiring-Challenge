"""
Web service for content fetching and internet search.
"""
from typing import Dict, Annotated, List
from urllib.parse import urlparse
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR, TextContent
from ..models.base import RichToolDescription, ToolService, BaseAPIClient, BaseServiceConfig, ContentProcessor
from ..utils.helpers import ContentFetcher
from pydantic import AnyUrl, Field
import httpx
import logging

logger = logging.getLogger(__name__)


class WebServiceConfig(BaseServiceConfig):
    """Configuration for web service."""
    user_agent: str = "ChupAI/1.0 (Intelligent Assistant for Puch AI)"
    max_content_length: int = 1000000
    default_content_length: int = 5000


class WebService(ToolService):
    """Web service for fetching and searching web content."""
    
    def __init__(self, config: WebServiceConfig = None):
        super().__init__("web")
        self.config = config or WebServiceConfig()
    
    def get_tool_descriptions(self) -> Dict[str, RichToolDescription]:
        """Get tool descriptions for web service."""
        return {
            "fetch": RichToolDescription(
                description="Fetch a URL and return its content with optional truncation.",
                use_when="When you need to retrieve and process content from a specific URL, summarize web articles, or extract information from websites.",
                side_effects="Makes an HTTP request to the specified URL and may be subject to rate limiting or blocking by the target website."
            ),
            "search_information_on_internet": RichToolDescription(
                description="Search the internet for information using DuckDuckGo API.",
                use_when="When you need to find current information, news, or general knowledge from the internet that isn't available in a specific URL.",
                side_effects="Makes API calls to DuckDuckGo search service and may be subject to rate limiting."
            )
        }
    
    def validate_url(self, url: str) -> tuple[bool, str]:
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

    def format_error_response(self, error_msg: str, suggestions: List[str] = None) -> List[TextContent]:
        """Format error response with suggestions."""
        response = [f"❌ Error: {error_msg}"]
        if suggestions:
            response.append("\n💡 Suggestions:")
            response.extend([f"- {s}" for s in suggestions])
        return [TextContent(type="text", text="\n".join(response))]
    
    def register_tools(self, mcp):
        """Register web tools with the MCP server."""
        self.logger.info("Registering web tools...")
        
        @mcp.tool(description=self.get_tool_descriptions()["fetch"].model_dump_json())
        async def fetch(
            url: Annotated[AnyUrl, Field(description="URL to fetch")],
            max_length: Annotated[int, Field(default=5000, gt=0, lt=1000000)] = 5000,
            start_index: Annotated[int, Field(default=0, ge=0)] = 0,
            raw: Annotated[bool, Field(default=False)] = False,
        ) -> List[TextContent]:
            """Fetch a URL and return its content."""
            self.logger.info(f"Fetching URL: {url}")
            url_str = str(url).strip()
            is_valid, url_or_error = self.validate_url(url_str)
            if not is_valid:
                return self.format_error_response(url_or_error, [
                    "Make sure the URL starts with http:// or https://",
                    "Check for typos in the domain name",
                    "Try using search_information_on_internet instead"
                ])

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    content, prefix = await ContentFetcher.fetch_url(url_or_error, force_raw=raw)
                    if not content:
                        raise ValueError("No content received")
                    
                    # Format content with length info
                    original_length = len(content)
                    if start_index >= original_length:
                        return self.format_error_response("No more content available", [
                            "Try starting from index 0",
                            f"Maximum available content length: {original_length}"
                        ])
                    
                    truncated_content = content[start_index:start_index + max_length]
                    if not truncated_content:
                        return self.format_error_response("No content available at specified index", [
                            "Try starting from index 0",
                            f"Maximum available content length: {original_length}"
                        ])
                    
                    # Format response
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
                return self.format_error_response("Request timed out", [
                    "The website might be slow or unresponsive",
                    "Try again later",
                    "Try using search_information_on_internet instead"
                ])
            except httpx.HTTPError as e:
                return self.format_error_response(f"Failed to fetch URL: {str(e)}", [
                    "Check if the URL is accessible in your browser",
                    "The website might be blocking automated access",
                    "Try using search_information_on_internet instead"
                ])
            except Exception as e:
                return self.format_error_response(str(e), [
                    "The URL might be invalid or inaccessible",
                    "Try using search_information_on_internet instead"
                ])

        @mcp.tool(description=self.get_tool_descriptions()["search_information_on_internet"].model_dump_json())
        async def search_information_on_internet(
            query: Annotated[str, Field(description="Search query to look up on the internet")],
            max_results: Annotated[int, Field(default=5, description="Maximum number of results to return", ge=1, le=10)] = 5
        ) -> List[TextContent]:
            """Search for information on the internet using DuckDuckGo."""
            try:
                self.logger.info(f"Searching internet for: {query}")
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
                self.logger.error("Search request timed out")
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message="Search request timed out. Please try again."
                    )
                )
            except Exception as e:
                self.logger.error(f"Error in search_information_on_internet: {e}")
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,                    message=f"Error searching for information: {str(e)}"
                )
            )
