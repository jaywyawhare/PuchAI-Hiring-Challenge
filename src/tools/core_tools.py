"""
Core tools for the MCP server - Resume and Validation tools.
"""
from typing import Annotated, Optional
from pathlib import Path
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR, TextContent
from ..models.base import RichToolDescription
import logging

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
            logger.error(f"Error reading resume: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Error reading resume: {str(e)}"
                )
            )
    
    @staticmethod
    def create_tool_description(description: str, use_when: str, side_effects: Optional[str] = None) -> RichToolDescription:
        """Create a tool description."""
        return RichToolDescription(
            description=description,
            use_when=use_when,
            side_effects=side_effects
        )


def register_core_tools(mcp):
    """Register core tools (resume, validate) with the MCP server."""
    
    logger.info("Registering core tools...")
    
    manager = CoreToolsManager()
    
    ResumeToolDescription = manager.create_tool_description(
        description="Serve your resume in plain markdown.",
        use_when="Puch (or anyone) asks for your resume; this must return raw markdown, no extra formatting.",
        side_effects=None,
    )

    @mcp.tool(description=ResumeToolDescription.model_dump_json())
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
            logger.info("Loading resume from file...")
            result_text = manager.get_resume_content()
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
        from ..config import MY_NUMBER
        logger.info("Validation completed successfully")
        return [TextContent(type="text", text=MY_NUMBER.strip())]

    HelpMenuDescription = RichToolDescription(
        description="Display comprehensive help menu for Chup AI with all available tools and features.",
        use_when="User asks for help, wants to see available commands, or needs guidance on using Chup AI.",
        side_effects="User receives a formatted help menu with all available tools organized by category.",
    )

    @mcp.tool(description=HelpMenuDescription.model_dump_json())
    async def get_help_menu() -> list[TextContent]:
        """
        Display comprehensive help menu for Chup AI - Intelligent Assistant for Puch AI.
        
        Returns a well-formatted menu showing all available tools organized by category,
        optimized for WhatsApp chatbot interactions.
        """
        logger.info("Generating help menu...")
        help_text = """
🤖 **Chup AI - Intelligent Assistant for Puch AI**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 **Welcome to Chup AI!** 
Your intelligent assistant powered by Puch AI technology, optimized for WhatsApp chatbot integration.

📋 **Available Tools & Commands:**

**🔧 Core Services:**
• `resume()` - Get developer's resume in markdown
• `validate()` - System validation (required by Puch AI)
• `get_help_menu()` - Show this help menu

**🌐 Web Tools:**
• `fetch(url, max_length, start_index, raw)` - Fetch and process web content
• `search_information_on_internet(query, max_results)` - Search web using DuckDuckGo

**🚆 Railway Services (🔴 LIVE DATA):**
• `get_live_train_status(train_number, date)` - Real-time train status
• `get_trains_between_stations(from_station, to_station, date)` - Find trains between stations
• `get_pnr_status_tool(pnr_number)` - Check PNR booking status
• `get_train_schedule_tool(train_number)` - Complete train route info
• `get_station_live_status(station_code)` - Live station status

**🎵 Music & Entertainment:**
• `get_song_name_links(song_name, artist)` - Multi-platform music links
• `get_music_recommendations(genre, mood, artist)` - Personalized recommendations
• `get_youtube_music_stream(video_url, quality)` - Extract YouTube audio streams
• `search_and_stream_music(query, include_streams)` - Search & stream music
• `download_youtube_audio(video_url, output_format)` - Download YouTube audio

**📚 Academic Tools:**
• `search_arxiv_papers(query, max_results, include_abstracts)` - Search papers on arXiv
  Example: search_arxiv_papers('ti:"neural networks" AND au:"hinton"')
• `get_arxiv_paper(paper_id)` - Get paper details by ID (e.g., 2103.08220)

**📰 Hacker News Tools:**
• `get_hn_stories(story_type, num_stories)` - Get stories by type:
  - Types: top, new, ask, show
  - Live data from official HN API
  - Includes points, comments, timestamps

• `search_hn_stories(query, num_results)` - Search stories:
  - Full-text search across all stories
  - Filter by tags and date
  - Sort by relevance or date

• `get_hn_user(username, num_stories)` - User profiles:
  - Account info and karma
  - Recent submissions
  - About text and profile links

• `get_item_details(item_id)` - Detailed item view:
  - Full story/comment text
  - Nested comments
  - Rich metadata

**🎯 Key Features:**
✅ Real API integration (no mock data)
✅ Live Indian Railway data from erail.in
✅ YouTube music streaming with yt-dlp + ffmpeg
✅ Multi-platform music search (Spotify, Apple Music, etc.)
✅ Smart web content processing
✅ WhatsApp chatbot optimized
✅ Bearer token authentication
✅ Production-ready with comprehensive error handling

**💡 Usage Tips for WhatsApp:**
• Use simple commands like: "get train status 12951"
• Search music: "find songs by Queen"
• Get web content: "fetch https://example.com"
• Railway info: "trains from NDLS to BCT"
• Academic papers: "arxiv quantum computing"

**🔒 Authentication:** Bearer token required
**🌐 Server:** Running on streamable HTTP
**⚡ Status:** Production ready for Puch AI integration

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 **Chup AI** - Built with ❤️ for Puch AI WhatsApp Bot
        """
        return [TextContent(type="text", text=help_text.strip())]