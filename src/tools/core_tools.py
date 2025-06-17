"""
Core tools for the MCP server - Resume and Validation tools.
"""
from typing import Annotated
from pathlib import Path
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR
from pydantic import BaseModel


class RichToolDescription(BaseModel):
    description: str
    use_when: str
    side_effects: str | None


def register_core_tools(mcp):
    """Register core tools (resume, validate) with the MCP server."""
    
    ResumeToolDescription = RichToolDescription(
        description="Serve your resume in plain markdown.",
        use_when="Puch (or anyone) asks for your resume; this must return raw markdown, no extra formatting.",
        side_effects=None,
    )

    @mcp.tool(description=ResumeToolDescription.model_dump_json())
    async def resume() -> str:
        """
        Return your resume exactly as markdown text.
        
        This function reads the resume.md file from the current directory
        and returns its content as markdown text.
        
        Returns:
            str: The resume content in markdown format
            
        Raises:
            McpError: If the resume file cannot be found or read
        """
        try:
            resume_path = Path(__file__).parent.parent.parent / "resume.md"
            if not resume_path.exists():
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message="Resume file not found. Please create resume.md"
                    )
                )
            
            resume_content = resume_path.read_text(encoding='utf-8')
            if not resume_content.strip():
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message="Resume file is empty"
                    )
                )
            print(f"Serving resume from {resume_path}\n")
            print(f"Resume content:\n{resume_content}\n") 
            return resume_content
            
        except Exception as e:
            if isinstance(e, McpError):
                raise
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Error reading resume: {str(e)}"
                )
            )

    @mcp.tool
    async def validate() -> str:
        """
        NOTE: This tool must be present in an MCP server used by puch.
        """
        from ..config import MY_NUMBER
        return MY_NUMBER

    HelpMenuDescription = RichToolDescription(
        description="Display comprehensive help menu for Chup AI with all available tools and features.",
        use_when="User asks for help, wants to see available commands, or needs guidance on using Chup AI.",
        side_effects="User receives a formatted help menu with all available tools organized by category.",
    )

    @mcp.tool(description=HelpMenuDescription.model_dump_json())
    async def get_help_menu() -> str:
        """
        Display comprehensive help menu for Chup AI - Intelligent Assistant for Puch AI.
        
        Returns a well-formatted menu showing all available tools organized by category,
        optimized for WhatsApp chatbot interactions.
        """
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

**🔒 Authentication:** Bearer token required
**🌐 Server:** Running on streamable HTTP
**⚡ Status:** Production ready for Puch AI integration

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 **Chup AI** - Built with ❤️ for Puch AI WhatsApp Bot
        """
        return help_text.strip()
