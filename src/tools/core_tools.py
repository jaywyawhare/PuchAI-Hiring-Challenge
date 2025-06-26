"""
Core tools for the MCP server - Resume and Validation tools.
"""
import logging
from typing import Annotated, Optional, List
from pathlib import Path
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR, TextContent
from ..models.base import RichToolDescription
from .scheme_tools import register_scheme_tools

logger = logging.getLogger(__name__)


class CoreToolsManager:
    """Manager for core tools registration."""
    
    @staticmethod
    def get_resume_content() -> str:
        """Get resume content from file."""
        try:
            resume_path = Path(__file__).parent.parent.parent / "resume.md"
            return resume_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read resume: {e}")
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(e)))

    @staticmethod
    def create_tool_description(description: str, use_when: str, side_effects: Optional[str] = None) -> RichToolDescription:
        """Create a rich tool description."""
        return RichToolDescription(
            description=description,
            use_when=use_when,
            side_effects=side_effects
        )


def register_core_tools(mcp):
    """Register all core tools with the MCP server."""
    
    logger.info("Registering core tools...")
    
    manager = CoreToolsManager()
    
    # Create rich descriptions for tools
    resume_desc = manager.create_tool_description(
        description="Serve your resume in plain markdown.",
        use_when="Puch (or anyone) asks for your resume; this must return raw markdown, no extra formatting.",
        side_effects=None,
    )

    @mcp.tool(description=resume_desc.model_dump_json())
    async def resume() -> list[TextContent]:
        """
        Return your resume exactly as markdown text.
        
        This function reads the resume.md file from the current directory
        and returns its content as markdown text.
        
        Returns:
            list[TextContent]: The resume content in markdown format
            
        Raises:
            McpError: If the resume file cannot be found or read
        """
        try:
            logger.info("resume tool called")
            result_text = manager.get_resume_content()
            logger.info(f"resume tool output: {result_text[:200]}..." if len(result_text) > 200 else f"resume tool output: {result_text}")
            return [TextContent(type="text", text=result_text.strip())]
            
        except Exception as e:
            if isinstance(e, McpError):
                logger.error(f"Error in resume: {e.data.message}")
                raise
            logger.error(f"Error in resume: {str(e)}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Error reading resume: {str(e)}"
                )
            )

    ValidateToolDescription = manager.create_tool_description(
        description="Validate the MCP server configuration.",
        use_when="This tool is required for Puch AI system compatibility.",
        side_effects="Returns the configured phone number for validation.",
    )

    @mcp.tool(description=ValidateToolDescription.model_dump_json())
    async def validate() -> list[TextContent]:
        """
        Validate the MCP server configuration.

        This tool is required for Puch AI system compatibility.
        Returns the configured phone number for validation.

        Returns:
            list[TextContent]: The configured phone number
        """
        logger.info("Validating MCP server configuration...")
        logger.info("validate tool called")
        from ..config import MY_NUMBER
        logger.info(f"validate tool output: {MY_NUMBER.strip()}")
        return [TextContent(type="text", text=MY_NUMBER.strip())]

    HelpMenuDescription = RichToolDescription(
        description="Display comprehensive help menu for Chup AI with all available tools and features.",
        use_when="User asks for help, wants to see available commands, or needs guidance on using Chup AI.",
        side_effects="User receives a formatted help menu with all available tools organized by category.",
    )

    @mcp.tool(description=HelpMenuDescription.model_dump_json())
    async def core_get_help_menu() -> list[TextContent]:
        """
        Display comprehensive help menu for Chup AI - Intelligent Assistant for Puch AI.
        
        Returns a well-formatted menu showing all available tools organized by category,
        optimized for WhatsApp chatbot interactions.
        """
        logger.info("Generating help menu...")
        logger.info("core_get_help_menu tool called")
        help_text = """
🤖 **Welcome to Chup AI!** 
Your intelligent WhatsApp assistant with smart tools and live data.

📋 **What I Can Do:**

**📝 Basic Functions:**
• Show my developer's resume 
• Share my system credentials
• Display this help menu

**🌐 Web Tools:**
• Get content from any website
• Search the internet for information

**🚆 Railway Info (Live Data):**
• Check real-time train status
• Find trains between stations
• Check PNR booking status
• View complete train schedules
• See live station updates 

**🎵 Music & Entertainment:**
• Find songs across platforms
• Get music recommendations
• Stream YouTube audio
• Search and play music
• Download YouTube audio

**📚 Academic Research:**
• Search academic papers
• Get detailed paper info
• Access arXiv database
• Perform deep research with citation analysis

**🔬 Deep Research:**
• Comprehensive topic analysis using DFS citation traversal
• Wikipedia and arXiv source integration  
• Reference analysis and knowledge graph construction
• Multi-level citation exploration

**📰 Hacker News Feed:**
• Browse top stories
• Search articles
• View user profiles
• Read discussions

**🌤️ Weather Updates:**
• Get current conditions
• See hourly forecasts
• Check multiple locations

📊 **Key Features:**
✅ Live data from verified sources
✅ Smart web content processing 
✅ Multi-platform music support
✅ WhatsApp-optimized responses
✅ Bearer token authentication
✅ Advanced research capabilities

💡 **Quick Tips:**
• Ask in natural language
• Share links to fetch content
• Use station codes for trains
• Be specific with requests
• Try deep research for comprehensive topic analysis

*🔴 Always connected to live data sources*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 Chup AI - Your Intelligent WhatsApp Assistant
        """
        result_text = help_text.strip()
        logger.info(f"core_get_help_menu tool output: {result_text[:200]}..." if len(result_text) > 200 else f"core_get_help_menu tool output: {result_text}")
        return [TextContent(type="text", text=result_text.strip())]

    available_tools_desc = manager.create_tool_description(
        description="Get a list of all available tools and their descriptions",
        use_when="User requests information about available features or capabilities",
        side_effects="Returns formatted list of all registered tools and their descriptions"
    )

    @mcp.tool(description=available_tools_desc.model_dump_json())
    async def core_get_available_tools() -> list[TextContent]:
        """
        Get a list of all available tools and their descriptions.
        
        Returns information about all tools available in this MCP server,
        including scheme search, web tools, and other utilities.
        """
        logger.info("core_get_available_tools tool called")
        tools_info = {
            "Scheme Search Tools": [
                "search_government_schemes - AI-powered semantic search for government schemes",
                "get_scheme_categories - Get all available scheme categories",
                "get_scheme_states - Get all available states/regions"
            ],
            "Web Tools": [
                "fetch_url - Fetch and process webpage content",
                "search_web - Search the web using DuckDuckGo"
            ],
            "Railway Tools": [
                "get_train_schedule - Get Indian Railway train schedules",
                "search_stations - Search railway stations"
            ],
            "Music Tools": [
                "search_youtube_music - Search for music on YouTube",
                "get_music_recommendations - Get music recommendations"
            ],
            "Weather Tools": [
                "get_weather - Get current weather information",
                "get_weather_forecast - Get weather forecast"
            ],
            "Research Tools": [
                "search_arxiv - Search academic papers on arXiv",
                "search_hackernews - Search Hacker News stories"
            ],
            "Deep Research Tools": [
                "deep_research - Perform deep research on a topic using citation graph traversal, Wikipedia, and arXiv integration."
            ]
        }
        
        response_parts = ["🛠️ **Available Tools in Chup AI MCP Server:**", ""]
        
        for category, tools in tools_info.items():
            response_parts.append(f"**{category}:**")
            for tool in tools:
                response_parts.append(f"  • {tool}")
            response_parts.append("")
        
        response_parts.extend([
            "For more details on each tool, use the help command or ask for specific functionality.",
            "You can also use the `core_get_help_menu` command to see a comprehensive help menu."
        ])
        
        output = "\n".join(response_parts)
        logger.info(f"core_get_available_tools tool output: {output[:200]}..." if len(output) > 200 else f"core_get_available_tools tool output: {output}")
        return [TextContent(type="text", text=output)]
    
    @mcp.tool(description=available_tools_desc.model_dump_json())
    async def core_list_tools() -> list[TextContent]:
        """
        Alias for core_get_available_tools to ensure compatibility with expected tool names.
        Returns the same output as core_get_available_tools.
        """
        logger.info("core_list_tools tool called (alias for core_get_available_tools)")
        result = await core_get_available_tools()
        logger.info(f"core_list_tools tool output: {result[0].text[:200]}..." if len(result[0].text) > 200 else f"core_list_tools tool output: {result[0].text}")
        return result

    # Register scheme search tools
    register_scheme_tools(mcp)