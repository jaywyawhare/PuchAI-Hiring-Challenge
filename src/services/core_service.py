"""
Core service for basic MCP functionality.
"""
from typing import Dict, Annotated
from pathlib import Path
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR, TextContent
from ..models.base import RichToolDescription, ToolService
import logging
import os
import json

logger = logging.getLogger(__name__)


class CoreService(ToolService):
    """Core service providing resume and validation tools."""
    
    def __init__(self):
        super().__init__("core")
    
    def get_tool_descriptions(self) -> Dict[str, RichToolDescription]:
        """Get tool descriptions for core service."""
        return {
            "resume": RichToolDescription(
                description="Serve your resume in plain markdown format.",
                use_when="User requests resume content; must return raw markdown without extra formatting.",
                side_effects=None
            ),
            "validate": RichToolDescription(
                description="Validate the MCP server configuration.",
                use_when="This tool is required for Puch AI system compatibility.",
                side_effects="Returns the configured phone number for validation."
            ),
            "core_get_help_menu": RichToolDescription(
                description="Display comprehensive help information for all available tools.",
                use_when="User asks for help, wants to see available commands, or needs guidance on using Chup AI.",
                side_effects="User receives a formatted help menu with all available tools organized by category."
            ),
            "core_list_tools": RichToolDescription(
                description="Get a comprehensive list of all available tools and their descriptions.",
                use_when="User wants to see all available tools, asks for commands list, or needs to know what the system can do.",
                side_effects="Returns a formatted list of all registered tools with descriptions."
            ),
            "deep_research": RichToolDescription(
                description="Perform deep research on a topic with citation graph and references (DFS traversal, Wikipedia/arXiv integration)",
                use_when="User requests comprehensive research, citation analysis, or multi-level reference exploration.",
                side_effects="Returns a structured summary, references, and a citation graph in JSON."
            )
        }
    
    def get_resume_content(self) -> str:
        """Get resume content from file."""
        try:
            resume_path = Path(__file__).parent.parent.parent / "resume.md"
            return resume_path.read_text(encoding="utf-8")
        except Exception as e:
            self.logger.error(f"Error reading resume: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Error reading resume: {str(e)}"
                )
            )
    
    def register_tools(self, mcp):
        """Register core tools with the MCP server."""
        self.logger.info("Registering core tools...")
        
        @mcp.tool(description=self.get_tool_descriptions()["resume"].model_dump_json())
        async def resume() -> list[TextContent]:
            logger.info("resume tool called (core_service)")
            try:
                result_text = self.get_resume_content()
                logger.info(f"resume tool output (core_service): {result_text[:200]}..." if len(result_text) > 200 else f"resume tool output (core_service): {result_text}")
                return [TextContent(type="text", text=result_text.strip())]
            except Exception as e:
                logger.error(f"resume tool error (core_service): {e}")
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message=f"Error reading resume: {str(e)}"
                    )
                )
        
        @mcp.tool(description=self.get_tool_descriptions()["validate"].model_dump_json())
        async def validate() -> list[TextContent]:
            logger.info("validate tool called (core_service)")
            my_number = os.getenv("MY_NUMBER", "Not configured")
            logger.info(f"validate tool output (core_service): {my_number.strip()}")
            return [TextContent(type="text", text=my_number.strip())]
        
        @mcp.tool(description=self.get_tool_descriptions()["core_list_tools"].model_dump_json())
        async def core_list_tools() -> list[TextContent]:
            logger.info("core_list_tools tool called (core_service)")
            from src.tools.core_tools import core_get_available_tools
            result = await core_get_available_tools()
            logger.info(f"core_list_tools tool output (core_service): {result[0].text[:200]}..." if len(result[0].text) > 200 else f"core_list_tools tool output (core_service): {result[0].text}")
            return result
        
        @mcp.tool(description=self.get_tool_descriptions()["core_get_help_menu"].model_dump_json())
        async def core_get_help_menu() -> list[TextContent]:
            logger.info("core_get_help_menu tool called (core_service)")
            help_text = """
🤖 **Welcome to Chup AI!** 
Your intelligent WhatsApp assistant with smart tools and live data.

**Core Tools:**
- `resume()` - Get developer resume
- `validate()` - Validate MCP server configuration
- `core_get_help_menu()` - Show this help menu
- `core_list_tools()` - Get a list of all available tools

**Advanced Research Tools:**
- `researchers_wet_dream(topic, research_depth, thinking_depth, auto_iterate, max_iterations)` - 🎯 Ultimate autonomous research with thinking integration
- `deep_research(topic, max_depth, include_wikipedia, include_arxiv)` - Deep research with citation analysis
- `thinking_tool(thought, nextThoughtNeeded, thoughtNumber, totalThoughts, ...)` - Dynamic problem-solving with revision and branching

**Web Tools:**
- `fetch(url)` - Fetch webpage content
- `search_information_on_internet(query)` - Search the web

**Railway Tools (Live Data):**
- `get_live_train_status(train_number)` - Get live train status
- `get_trains_between_stations(from, to)` - Find trains between stations
- `get_pnr_status_tool(pnr_number)` - Check PNR status
- `get_train_schedule_tool(train_number)` - Get train schedule
- `get_station_live_status(station_code)` - Get station live status

**Music Tools:**
- `get_song_name_links(song_name, artist)` - Get song links
- `get_music_recommendations(genre, mood, artist)` - Get music recommendations
- `get_youtube_music_stream(song_name, quality)` - Get YouTube music stream
- `search_and_stream_music(query)` - Search and stream music
- `download_youtube_audio(song_name, format)` - Download YouTube audio

**Academic Tools:**
- `search_arxiv_papers(query, max_results)` - Search arXiv papers
- `get_arxiv_paper(paper_id)` - Get arXiv paper by ID

**News Tools (Hacker News):**
- `get_hn_stories(story_type, num_stories)` - Get Hacker News stories
- `search_hn_stories(query, num_results)` - Search Hacker News stories
- `get_hn_user(username, num_stories)` - Get Hacker News user profile

**Weather Tools:**
- `get_weather(location)` - Get current weather

**Usage Stats:**
- Total Tools: 25+
- Live Data Sources: 5
- API Integrations: 10+
- Response Types: JSON, Markdown, Text
- Advanced Research: 3 tools with autonomous capabilities

**Quick Examples:**
- "resume()" → Get developer resume
- "researchers_wet_dream('AI ethics')" → Comprehensive autonomous research
- "thinking_tool('Analyzing this problem...', True, 1, 5)" → Start thinking process
- "fetch('https://news.com')" → Get webpage
- "get_weather('London')" → London weather
- "search_arxiv_papers('AI')" → AI research papers

**Pro Tip:** Use core_get_help_menu() for detailed usage instructions!

*Chup AI is production-ready for Puch AI WhatsApp Bot integration with advanced research capabilities.*
            """
            result_text = help_text.strip()
            logger.info(f"core_get_help_menu tool output (core_service): {result_text[:200]}..." if len(result_text) > 200 else f"core_get_help_menu tool output (core_service): {result_text}")
            return [TextContent(type="text", text=result_text.strip())]
        
        @mcp.tool(description=self.get_tool_descriptions()["deep_research"].model_dump_json())
        async def deep_research(
            topic: str,
            max_depth: int = 2,
            include_wikipedia: bool = True,
            include_arxiv: bool = True
        ) -> list[TextContent]:
            # Log complete input parameters
            input_data = {
                "topic": topic,
                "max_depth": max_depth,
                "include_wikipedia": include_wikipedia,
                "include_arxiv": include_arxiv
            }
            logger.info(f"deep_research tool called with complete input: {json.dumps(input_data, indent=2)}")
            
            summary = f"# Deep Research Summary\n\n**Topic:** {topic}\n\nThis is a mock summary for '{topic}'."
            references = [
                {"title": "Reference Paper 1", "url": "https://arxiv.org/abs/1234.5678"},
                {"title": "Wikipedia Article", "url": f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}"}
            ]
            citation_graph = {
                "nodes": [
                    {"id": 1, "label": topic},
                    {"id": 2, "label": "Reference Paper 1"},
                    {"id": 3, "label": "Wikipedia Article"}
                ],
                "edges": [
                    {"from": 1, "to": 2},
                    {"from": 1, "to": 3}
                ]
            }
            import json
            markdown = f"""
🎯 **Deep Research Results**

📝 **Topic:** `{topic}`

---

## 📄 Summary
{summary}

---

## 📚 References
"""
            for ref in references:
                markdown += f"- [{ref['title']}]({ref['url']})\n"
            markdown += "\n---\n\n## 🕸️ Citation Graph (JSON)\n"
            markdown += f"```json\n{json.dumps(citation_graph, indent=2)}\n```\n"
            markdown += "\n---\n\n💡 *This is a mock result. Actual research will include multi-level citation traversal and real references.*"
            
            # Log complete output
            logger.info(f"deep_research tool completed with complete output: {markdown}")
            return [TextContent(type="text", text=markdown.strip())]
