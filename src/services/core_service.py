"""
Core service for basic MCP functionality.
"""
from typing import Dict, Annotated
from pathlib import Path
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR, TextContent
from ..models.base import RichToolDescription, ToolService
import logging

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
            "get_help_menu": RichToolDescription(
                description="Display comprehensive help information for all available tools.",
                use_when="User asks for help, wants to see available commands, or needs guidance on using Chup AI.",
                side_effects="User receives a formatted help menu with all available tools organized by category."
            ),
            "meow": RichToolDescription(
                description="Meow back with adorable cat pictures and cat-themed responses.",
                use_when="User sends 'meow', asks for cats, or wants cute cat content.",
                side_effects="Returns cat-themed responses with ASCII art and cat facts."
            ),
            "list_tools": RichToolDescription(
                description="Get a comprehensive list of all available tools and their descriptions.",
                use_when="User wants to see all available tools, asks for commands list, or needs to know what the system can do.",
                side_effects="Returns a formatted list of all registered tools with descriptions."
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
                self.logger.info("Loading resume from file...")
                result_text = self.get_resume_content()
                return [TextContent(type="text", text=result_text.strip())]
                
            except Exception as e:
                if isinstance(e, McpError):
                    self.logger.error(f"Error in resume: {e.data.message}")
                    raise
                self.logger.error(f"Error in resume: {str(e)}")
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message=f"Error reading resume: {str(e)}"
                    )
                )
        
        @mcp.tool(description=self.get_tool_descriptions()["validate"].model_dump_json())
        async def validate() -> list[TextContent]:
            """
            Validate the MCP server configuration.
            
            This tool is required for Puch AI system compatibility.
            Returns the configured phone number for validation.
            
            Returns:
                list[TextContent]: The configured phone number
            """
            import os
            my_number = os.getenv("MY_NUMBER", "Not configured")
            self.logger.info(f"Validation requested. Phone number: {my_number}")
            return [TextContent(type="text", text=my_number.strip())]
        
        @mcp.tool(description=self.get_tool_descriptions()["meow"].model_dump_json())
        async def meow() -> list[TextContent]:
            """
            Meow back with adorable cat pictures and cat-themed responses.
            
            Fetches a random cat image from The Cat API and returns it with
            cat-themed ASCII art and fun cat facts.
            
            Returns:
                list[TextContent]: Cat-themed response with random cat image URL
            """
            try:
                import httpx
                import json
                import random
                
                self.logger.info("Fetching random cat from The Cat API...")
                
                # Fetch random cat image from The Cat API
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get("https://api.thecatapi.com/v1/images/search")
                    
                    if response.status_code == 200:
                        cat_data = response.json()
                        if cat_data and len(cat_data) > 0:
                            cat_url = cat_data[0]["url"]
                            cat_id = cat_data[0].get("id", "unknown")
                            width = cat_data[0].get("width", "unknown")
                            height = cat_data[0].get("height", "unknown")
                        else:
                            cat_url = "https://cdn2.thecatapi.com/images/ebc.jpg"
                            cat_id = "fallback"
                            width = height = "unknown"
                    else:
                        # Fallback cat image
                        cat_url = "https://cdn2.thecatapi.com/images/ebc.jpg"
                        cat_id = "fallback"
                        width = height = "unknown"
                
                # Random cat facts
                cat_facts = [
                    "Cats sleep 12-16 hours per day! 😴",
                    "A group of cats is called a 'clowder' 🐱",
                    "Cats have 32 muscles in each ear! 👂",
                    "A cat's purr vibrates at 20-50 Hz, which can heal bones! �",
                    "Cats can't taste sweetness! 🍭",
                    "A cat's nose print is unique, like a human fingerprint! �",
                    "Cats have a third eyelid called a nictitating membrane! �️",
                    "Adult cats only meow to communicate with humans! 🗣️",
                    "Cats can rotate their ears 180 degrees! 🔄",
                    "A cat's whiskers are roughly as wide as its body! 📏"
                ]
                
                random_fact = random.choice(cat_facts)
                
                result_text = f"""🐾 **MEOW MEOW!** 🐾

            /\\_/\\  
           ( o.o ) 
            > ^ <  

🖼️ **Here's your random cat!**
📸 **Image:** {cat_url}
🆔 **Cat ID:** {cat_id}
📐 **Size:** {width}x{height}px

🎲 **Random Cat Fact:** {random_fact}

          /\\_/\\  
         ( ^.^ ) 
          _) (_   

**More cats?** Just say "meow" again! 🐈

*🔴 Fresh cat from The Cat API - https://thecatapi.com/*
                """
                
                return [TextContent(type="text", text=result_text.strip())]
                
            except Exception as e:
                self.logger.error(f"Error fetching cat image: {e}")
                # Fallback response if API fails
                result_text = f"""🐾 **MEOW MEOW!** 🐾

            /\\_/\\  
           ( o.o ) 
            > ^ <  

🖼️ **Here's a cute cat for you!**
📸 **Image:** https://cdn2.thecatapi.com/images/ebc.jpg

🎲 **Cat Fact:** Cats are absolutely purr-fect! 😸

          /\\_/\\  
         ( ^.^ ) 
          _) (_   

**More cats?** Just say "meow" again! 🐈

*Note: Having trouble reaching The Cat API, but here's a backup cat!*
                """
                return [TextContent(type="text", text=result_text.strip())]
        
        @mcp.tool(description=self.get_tool_descriptions()["list_tools"].model_dump_json())
        async def list_tools() -> list[TextContent]:
            """
            Get a comprehensive list of all available tools and their descriptions.
            
            Returns a well-formatted list of all tools available in the MCP server,
            organized by category for easy navigation.
            """
            self.logger.info("Generating comprehensive tools list...")
            
            tools_list = """📋 **CHUP AI - COMPLETE TOOLS DIRECTORY**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 **CORE TOOLS**
┌─────────────────────────────────────────────────┐
│ • resume()                - Get developer resume │
│ • validate()              - System validation    │
│ • get_help_menu()         - Show help menu       │
│ • meow()                   - Cat pics & responses  │
│ • list_tools()            - This tools list      │
└─────────────────────────────────────────────────┘

🌐 **WEB TOOLS**
┌─────────────────────────────────────────────────┐
│ • fetch(url)              - Get webpage content  │
│ • search_information_on_internet(query)          │
│                           - Search with DuckGo   │
└─────────────────────────────────────────────────┘

🚆 **RAILWAY TOOLS** (🔴 LIVE DATA)
┌─────────────────────────────────────────────────┐
│ • get_live_train_status(train_number)            │
│ • get_trains_between_stations(from, to)          │
│ • get_pnr_status_tool(pnr_number)                │
│ • get_train_schedule_tool(train_number)          │
│ • get_station_live_status(station_code)          │
└─────────────────────────────────────────────────┘

🎵 **MUSIC TOOLS**
┌─────────────────────────────────────────────────┐
│ • get_song_name_links(song_name, artist)         │
│ • get_music_recommendations(genre, mood, artist) │
│ • get_youtube_music_stream(song_name, quality)   │
│ • search_and_stream_music(query)                 │
│ • download_youtube_audio(song_name, format)      │
└─────────────────────────────────────────────────┘

📚 **ACADEMIC TOOLS**
┌─────────────────────────────────────────────────┐
│ • search_arxiv_papers(query, max_results)        │
│ • get_arxiv_paper(paper_id)                      │
└─────────────────────────────────────────────────┘

📰 **NEWS TOOLS** (Hacker News)
┌─────────────────────────────────────────────────┐
│ • get_hn_stories(story_type, num_stories)        │
│ • search_hn_stories(query, num_results)          │
│ • get_hn_user(username, num_stories)             │
└─────────────────────────────────────────────────┘

🌤️ **WEATHER TOOLS**
┌─────────────────────────────────────────────────┐
│ • get_weather(location)   - Current weather      │
└─────────────────────────────────────────────────┘

📊 **USAGE STATS**
• Total Tools: 20+
• Live Data Sources: 5
• API Integrations: 8+
• Response Types: JSON, Markdown, Text

🎯 **QUICK EXAMPLES**
• "resume()" → Get developer resume
• "meow()" → Get cute cat content  
• "fetch('https://news.com')" → Get webpage
• "get_weather('London')" → London weather
• "search_arxiv_papers('AI')" → AI research papers

💡 **PRO TIP:** Use get_help_menu() for detailed usage instructions!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 **Chup AI** - Production Ready for Puch AI WhatsApp Bot
            """
            
            return [TextContent(type="text", text=tools_list.strip())]
        
        @mcp.tool(description=self.get_tool_descriptions()["get_help_menu"].model_dump_json())
        async def get_help_menu() -> list[TextContent]:
            """Get comprehensive help information about Chup AI's available tools and capabilities."""
            help_text = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 **CHUP AI - WhatsApp Assistant Help Menu**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Hi! I'm **Chup AI**, your intelligent WhatsApp assistant built for Puch AI. Here's everything I can help you with:

**🏠 Core Tools:**
• `resume()` - Get Arinjay's professional resume and background
• `validate()` - System validation tool for Puch AI compatibility
• `get_help_menu()` - Show this help menu anytime
• `meow()` - Get cute cat pictures and responses 🐱
• `list_tools()` - Get comprehensive list of all available tools

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

**🌤️ Weather Information:**
• `get_weather(location)` - Current weather conditions for any location

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
