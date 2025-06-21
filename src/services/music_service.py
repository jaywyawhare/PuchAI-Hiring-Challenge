"""
Music service for music search and streaming.
"""
from typing import Dict
from ..models.base import RichToolDescription, ToolService, BaseServiceConfig
import logging

logger = logging.getLogger(__name__)


class MusicServiceConfig(BaseServiceConfig):
    """Configuration for music service."""
    youtube_quality: str = "best"
    default_format: str = "mp3"


class MusicService(ToolService):
    """Music service for streaming and music search."""
    
    def __init__(self, config: MusicServiceConfig = None):
        super().__init__("music")
        self.config = config or MusicServiceConfig()
    
    def get_tool_descriptions(self) -> Dict[str, RichToolDescription]:
        """Get tool descriptions for music service."""
        return {
            "get_song_name_links": RichToolDescription(
                description="Get real links and information for songs from various music platforms.",
                use_when="When you need to find music on different streaming platforms like Spotify, Apple Music, etc.",
                side_effects="Makes API calls to various music platforms and may be subject to rate limiting."
            ),
            "get_music_recommendations": RichToolDescription(
                description="Get real music recommendations using web scraping and API calls.",
                use_when="When you need personalized music recommendations based on genre, mood, or artist.",
                side_effects="Makes API calls to music recommendation services and may be subject to rate limiting."
            ),
            "get_youtube_music_stream": RichToolDescription(
                description="Search for a song and extract its audio stream information for music streaming.",
                use_when="When you need to get streaming URLs for music from YouTube.",
                side_effects="Uses yt-dlp to extract streaming information from YouTube and may be subject to rate limiting."
            ),
            "search_and_stream_music": RichToolDescription(
                description="Search for music on YouTube and get streaming information.",
                use_when="When you need to search for music and get both search results and streaming URLs in one request.",
                side_effects="Uses yt-dlp to search and extract streaming information from YouTube and may be subject to rate limiting."
            ),
            "download_youtube_audio": RichToolDescription(
                description="Search for a song and download its audio.",
                use_when="When you need to download audio files from YouTube for offline use.",
                side_effects="Downloads audio files using yt-dlp and may consume storage space and bandwidth."
            )
        }
    
    def register_tools(self, mcp):
        """Register music tools with the MCP server."""
        # Import the existing music tools registration function
        from ..tools.music_tools import register_music_tools
        
        self.logger.info("Registering music tools...")
        register_music_tools(mcp)
        self.logger.info("Music tools registered successfully")
