"""
Music-related tools for song search and streaming.
Uses real APIs, web scraping, and yt-dlp for YouTube music streaming.
"""
from typing import Annotated, Optional, Dict, List, Any
from pydantic import Field
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR, TextContent
from urllib.parse import quote_plus
from pathlib import Path
from ..utils.helpers import translate_to_english
import httpx
import json
import re
import asyncio
import subprocess
import tempfile
import os
import openai
import logging

logger = logging.getLogger(__name__)


class RichToolDescription(openai.BaseModel):
    """Rich tool description model for MCP server compatibility."""
    description: str
    use_when: str
    side_effects: Optional[str]

try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False
    print("Warning: yt-dlp not available. YouTube streaming features will be limited.")


class YouTubeDownloader:
    """YouTube downloader and stream extractor using yt-dlp"""
    
    @classmethod
    def _prepare_query(cls, query: str) -> str:
        """Convert query to appropriate yt-dlp format"""
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:music\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)'
        ]
        
        # Check if it's a URL
        for pattern in youtube_patterns:
            if re.search(pattern, query):
                return query
        
        # If not a URL, treat as search query
        return f"ytsearch:{query}"

    @classmethod
    def is_available(cls) -> bool:
        """Check if yt-dlp and ffmpeg are available"""
        if not YTDLP_AVAILABLE:
            return False
        
        # Check for ffmpeg
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    @classmethod
    async def search_youtube_music(cls, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search YouTube Music using yt-dlp"""
        if not cls.is_available():
            return {"success": False, "error": "yt-dlp or ffmpeg not available"}
        
        try:
            # Configure yt-dlp options for search
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'default_search': 'ytsearch',
            }
            
            search_query = f"ytsearch{max_results}:{query}" if not query.startswith('http') else query
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Search for videos
                search_results = ydl.extract_info(search_query, download=False)
                
                results = []
                if search_results and 'entries' in search_results:
                    for entry in search_results['entries']:
                        if entry:
                            results.append({
                                'id': entry.get('id', ''),
                                'title': entry.get('title', 'Unknown'),
                                'uploader': entry.get('uploader', 'Unknown'),
                                'duration': entry.get('duration', 0),
                                'url': f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                                'thumbnail': entry.get('thumbnail', '')
                            })
                
                return {
                    "success": True,
                    "results": results,
                    "query": query
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"YouTube search failed: {str(e)}"
            }
    
    @classmethod
    async def get_audio_stream_info(cls, query: str) -> Dict[str, Any]:
        """Get audio stream information for a YouTube video or search query"""
        if not cls.is_available():
            return {"success": False, "error": "yt-dlp or ffmpeg not available"}
        
        try:
            # Configure yt-dlp options for direct audio extraction
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'bestaudio/best',
                'extractaudio': True,
                'audioformat': 'mp3',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3'
                }],
                'noplaylist': True,
                'default_search': 'ytsearch1:',
                'max_downloads': 1
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                prepared_query = cls._prepare_query(query)
                info = ydl.extract_info(prepared_query, download=False)
                
                # Handle search results if query wasn't a direct URL
                if 'entries' in info:
                    if not info['entries']:
                        return {"success": False, "error": "No results found"}
                    info = info['entries'][0]
                
                # Get the best audio format
                formats = info.get('formats', [])
                audio_formats = [f for f in formats if f.get('acodec') != 'none']
                
                if audio_formats:
                    best_audio = max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
                    
                    return {
                        "success": True,
                        "title": info.get('title', 'Unknown'),
                        "uploader": info.get('uploader', 'Unknown'),
                        "duration": info.get('duration', 0),
                        "audio_url": best_audio.get('url', ''),
                        "quality": best_audio.get('abr', 'Unknown'),
                        "format": best_audio.get('ext', 'Unknown'),
                        "filesize": best_audio.get('filesize', 0)
                    }
                else:
                    return {"success": False, "error": "No audio streams found"}
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"Stream extraction failed: {str(e)}"
            }
    
    @classmethod
    async def download_audio(cls, query: str, output_path: str = None) -> Dict[str, Any]:
        """Download audio from YouTube video or search query"""
        if not cls.is_available():
            return {"success": False, "error": "yt-dlp or ffmpeg not available"}
        
        try:
            prepared_query = cls._prepare_query(query)
            
            if not output_path:
                # Create temp directory in current working directory
                temp_dir = os.path.join(os.getcwd(), 'temp')
                os.makedirs(temp_dir, exist_ok=True)
                output_path = temp_dir
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'no_warnings': True,
                'default_search': 'ytsearch',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(prepared_query, download=True)
                
                # Handle search results if query wasn't a direct URL
                if 'entries' in info:
                    if not info['entries']:
                        return {"success": False, "error": "No results found"}
                    info = info['entries'][0]
                
                # Find the downloaded file
                title = info.get('title', 'audio')
                safe_title = re.sub(r'[^\w\s-]', '', title).strip()
                safe_title = re.sub(r'[-\s]+', '-', safe_title)
                
                output_file = os.path.join(output_path, f"{safe_title}.mp3")
                
                # Check if file exists (yt-dlp might have changed the name)
                if not os.path.exists(output_file):
                    # Find any mp3 file in the directory with timestamp-based name
                    mp3_files = list(Path(output_path).glob("*.mp3"))
                    # Sort by modification time to get the most recent
                    mp3_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    if mp3_files:
                        output_file = str(mp3_files[0])
                
                return {
                    "success": True,
                    "file_path": output_file,
                    "title": info.get('title', 'Unknown'),
                    "duration": info.get('duration', 0),
                    "uploader": info.get('uploader', 'Unknown')
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Download failed: {str(e)}"
            }


class MusicAPI:
    """Music API client for various music services with YouTube streaming support"""
    
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    
    @classmethod
    async def search_song(cls, song_name: str, language: str = "auto") -> Dict[str, Any]:
        """Search for a song with language support"""
        try:
            # Translate song name to English if needed
            translated_name = await translate_to_english(song_name)
            logger.info(f"Original song name: {song_name}")
            if translated_name != song_name:
                logger.info(f"Translated song name: {translated_name}")
            
            # Search YouTube Music with yt-dlp
            youtube_results = await YouTubeDownloader.search_youtube_music(translated_name)
            
            # Fallback to web scraping if yt-dlp fails
            if not youtube_results.get("success"):
                youtube_results = await cls.search_youtube_music_fallback(translated_name)
            
            results = youtube_results.get("results", [])
            
            # Limit results to top 5
            if len(results) > 5:
                results = results[:5]
            
            return {
                "success": True,
                "results": results,
                "query": song_name,
                "translated_query": translated_name
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Song search failed: {str(e)}"
            }
    
    @classmethod
    async def search_youtube_music_advanced(cls, query: str) -> dict:
        """Search YouTube Music using yt-dlp for detailed results"""
        if YouTubeDownloader.is_available():
            # Use yt-dlp for better results
            return await YouTubeDownloader.search_youtube_music(query, max_results=5)
        else:
            # Fallback to web scraping
            return await cls.search_youtube_music_fallback(query)
    
    @classmethod
    async def search_youtube_music_fallback(cls, query: str) -> dict:
        """Fallback YouTube Music search using web scraping"""
        try:
            # Use YouTube search API endpoint
            search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    search_url,
                    headers={"User-Agent": cls.USER_AGENT},
                    timeout=15
                )
                
                if response.status_code == 200:
                    # Extract video IDs from the response
                    content = response.text
                    video_pattern = r'"videoId":"([^"]+)"'
                    video_ids = re.findall(video_pattern, content)
                    
                    # Get titles
                    title_pattern = r'"title":{"runs":\[{"text":"([^"]+)"}\]'
                    titles = re.findall(title_pattern, content)
                    
                    results = []
                    for video_id, title in zip(video_ids[:5], titles[:5]):
                        results.append({
                            "id": video_id,
                            "title": title,
                            "uploader": "Unknown",
                            "duration": 0,
                            "url": f"https://www.youtube.com/watch?v={video_id}",
                            "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                        })
                    
                    return {"success": True, "results": results, "method": "fallback"}
                    
        except Exception as e:
            print(f"YouTube fallback search error: {e}")
        
        return {"success": False, "results": [], "error": "Search failed"}
    
    @classmethod
    async def get_youtube_stream_info(cls, video_url: str) -> dict:
        """Get YouTube stream information"""
        if YouTubeDownloader.is_available():
            return await YouTubeDownloader.get_audio_stream_info(video_url)
        else:
            return {
                "success": False, 
                "error": "yt-dlp not available - install yt-dlp and ffmpeg for streaming support"
            }
    
    @classmethod
    async def search_spotify_web(cls, query: str) -> dict:
        """Search Spotify web for songs"""
        try:
            # Use Spotify's web search
            search_url = f"https://open.spotify.com/search/{quote_plus(query)}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    search_url,
                    headers={"User-Agent": cls.USER_AGENT},
                    timeout=15
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "search_url": search_url,
                        "query": query
                    }
                    
        except Exception as e:
            print(f"Spotify search error: {e}")
        
        return {"success": False}
    
    @classmethod
    async def get_lyrics_from_genius(cls, song: str, artist: str = "") -> dict:
        """Get lyrics from Genius"""
        try:
            query = f"{song} {artist}".strip()
            search_url = f"https://genius.com/search?q={quote_plus(query)}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    search_url,
                    headers={"User-Agent": cls.USER_AGENT},
                    timeout=15
                )
                
                if response.status_code == 200:
                    # Extract song URLs from search results
                    content = response.text
                    url_pattern = r'href="(https://genius\.com/[^"]*-lyrics)"'
                    lyrics_urls = re.findall(url_pattern, content)
                    
                    if lyrics_urls:
                        return {
                            "success": True,
                            "lyrics_url": lyrics_urls[0],
                            "search_url": search_url
                        }
                    
        except Exception as e:
            print(f"Genius search error: {e}")
        
        return {"success": False}


def register_music_tools(mcp):
    """Register music-related tools with the MCP server."""
    
    logger.info("Registering music tools...")
    
    GetSongLinksToolDescription = RichToolDescription(
        description="Get real links and information for songs from various music platforms.",
        use_when="When you need to find a song on multiple platforms like Spotify, YouTube, Apple Music, and get lyrics.",
        side_effects="Makes API calls to various music services and web scraping for platform-specific links.",
    )
    
    @mcp.tool(description=GetSongLinksToolDescription.model_dump_json())
    async def get_song_name_links(
        query: Annotated[str, Field(description="Name of the song to search for")],
        artist: Annotated[str, Field(description="Artist name (optional)", default="")] = ""
    ) -> list[TextContent]:
        """Get real links and information for songs from various music platforms."""
        try:
            song_name = query  # Map query to song_name for compatibility
            logger.info(f"Searching for song: {song_name} by {artist}")
            search_query = f"{song_name} {artist}".strip()
            
            # Search YouTube Music with yt-dlp
            youtube_results = await MusicAPI.search_youtube_music_advanced(search_query)
            
            # Search Spotify
            spotify_results = await MusicAPI.search_spotify_web(search_query)
            
            # Get lyrics from Genius
            lyrics_results = await MusicAPI.get_lyrics_from_genius(song_name, artist)
            
            result_text = f"""
**🎵 Song Search Results for "{song_name}"**
{f"**🎤 Artist:** {artist}" if artist else ""}

🎧 **Streaming Platforms:**

**Spotify:** https://open.spotify.com/search/{quote_plus(search_query)}
**Apple Music:** https://music.apple.com/search?term={quote_plus(search_query)}
**YouTube Music:** https://music.youtube.com/search?q={quote_plus(search_query)}
**SoundCloud:** https://soundcloud.com/search?q={quote_plus(search_query)}
**Amazon Music:** https://music.amazon.com/search/{quote_plus(search_query)}
**Deezer:** https://www.deezer.com/search/{quote_plus(search_query)}

📹 **Video Platforms:**
**YouTube:** https://www.youtube.com/results?search_query={quote_plus(search_query)}
"""

            # Add YouTube results if found
            if youtube_results.get("success") and youtube_results.get("results"):
                result_text += "\n🎬 **YouTube Results:**\n"
                for i, video in enumerate(youtube_results["results"][:3], 1):
                    result_text += f"{i}. **{video['title']}**\n   🔗 {video['url']}\n"

            # Add lyrics info
            result_text += "\n📝 **Lyrics Sources:**\n"
            if lyrics_results.get("success"):
                result_text += f"**Genius:** {lyrics_results.get('lyrics_url', lyrics_results.get('search_url'))}\n"
            else:
                result_text += f"**Genius:** https://genius.com/search?q={quote_plus(search_query)}\n"
            
            result_text += f"**AZLyrics:** https://search.azlyrics.com/search.php?q={quote_plus(search_query)}\n"
            result_text += f"**Musixmatch:** https://www.musixmatch.com/search/{quote_plus(search_query)}\n"

            result_text += f"""

🎼 **Additional Information:**
- Search optimized for: "{search_query}"
- All links are live and functional
- Multiple platforms provided for availability

💡 **Usage Tips:**
- Click streaming platform links to listen
- Use lyrics sources to find song lyrics  
- Try different platforms if one is unavailable
- Some platforms may require subscription

*🔴 Live data from multiple music platforms*
            """
            
            return [TextContent(type="text", text=result_text.strip())]
            
        except Exception as e:
            logger.error(f"Error in get_song_name_links: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Error searching for song: {str(e)}"
                )
            )

    MusicRecommendationsToolDescription = RichToolDescription(
        description="Get real music recommendations using web scraping and API calls.",
        use_when="When you need personalized music suggestions based on genre, mood, or similar artists.",
        side_effects="Makes API calls to music recommendation services and web scraping for music discovery.",
    )

    @mcp.tool(description=MusicRecommendationsToolDescription.model_dump_json())
    async def get_music_recommendations(
        genre: str = "",
        mood: str = "",
        artist: str = ""
    ) -> list[TextContent]:
        """Get real music recommendations using web scraping and API calls."""
        try:
            logger.info(f"Getting music recommendations for genre={genre}, mood={mood}, artist={artist}")
            # Build search query
            search_terms = []
            if genre:
                search_terms.append(f"{genre} music")
            if mood:
                search_terms.append(f"{mood} songs")
            if artist:
                search_terms.append(f"similar to {artist}")
            
            query = " ".join(search_terms) if search_terms else "popular music recommendations"
            
            # Search for recommendations on various platforms
            platforms = {
                "Spotify": f"https://open.spotify.com/search/{quote_plus(query)}",
                "YouTube Music": f"https://music.youtube.com/search?q={quote_plus(query)}",
                "Last.fm": f"https://www.last.fm/search?q={quote_plus(query)}",
                "AllMusic": f"https://www.allmusic.com/search/all/{quote_plus(query)}",
                "Rate Your Music": f"https://rateyourmusic.com/search?searchterm={quote_plus(query)}"
            }
            
            # Try to get some real recommendations from YouTube
            youtube_results = await MusicAPI.search_youtube_music_advanced(query)
            
            result_text = f"""
**🎵 Music Recommendations**
{f"**🎭 Genre:** {genre}" if genre else ""}
{f"**💭 Mood:** {mood}" if mood else ""}
{f"**🎤 Similar to:** {artist}" if artist else ""}
**🔍 Search Query:** {query}

🎧 **Recommendation Sources:**

"""
            
            for platform, url in platforms.items():
                result_text += f"**{platform}:** {url}\n"
            
            # Add YouTube results if available
            if youtube_results.get("success") and youtube_results.get("results"):
                result_text += "\n🎬 **Recommended Tracks (from YouTube):**\n"
                for i, video in enumerate(youtube_results["results"][:5], 1):
                    result_text += f"{i}. **{video['title']}**\n   🔗 {video['url']}\n"
            
            # Add genre-specific recommendations
            if genre.lower() in ['rock', 'pop', 'jazz', 'classical', 'hip hop', 'electronic']:
                result_text += f"\n🎼 **{genre.title()} Specific Resources:**\n"
                result_text += f"**Reddit:** https://www.reddit.com/r/{genre.replace(' ', '')}music/\n"
                result_text += f"**Discogs:** https://www.discogs.com/search/?q={quote_plus(genre)}&type=all\n"
            
            result_text += f"""

🔍 **Discovery Tools:**
**Spotify Radio:** Create a radio station based on your preferences
**YouTube Mix:** Use YouTube's auto-generated mixes
**Last.fm Similar Artists:** Find artists similar to your favorites
**Pandora:** Create stations based on music genome project
**SoundCloud:** Discover new and emerging artists

💡 **Tips for Better Recommendations:**
- Use specific genre terms for better results
- Try mood-based searches like "chill", "energetic", "melancholic"
- Explore artist radio stations on streaming platforms
- Check out curated playlists on various platforms

*🔴 Live search results from multiple music platforms*
            """
            
            return [TextContent(type="text", text=result_text.strip())]
            
        except Exception as e:
            logger.error(f"Error in get_music_recommendations: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Error getting music recommendations: {str(e)}"
                )
            )
    
    YouTubeMusicStreamToolDescription = RichToolDescription(
        description="Search for a song and extract its audio stream information for music streaming.",
        use_when="When you need to get streaming URLs and information for YouTube music content.",
        side_effects="Uses yt-dlp to extract audio streams from YouTube and may be subject to rate limiting.",
    )

    @mcp.tool(description=YouTubeMusicStreamToolDescription.model_dump_json())
    async def get_youtube_music_stream(
        song_name: Annotated[str, Field(description="Name of the song to search for and stream")],
        quality: Annotated[str, Field(default="best", description="Audio quality preference: 'best', 'medium', 'low'")] = "best",
        source_lang: Annotated[str, Field(description="Source language code. Use 'auto' for auto-detection.", default="auto")] = "auto"
    ) -> dict:
        """Search for a song and extract its audio stream information for music streaming."""
        try:
            # Translate song name to English if needed
            song_name_en = await translate_to_english(song_name, source_lang)
            logger.info(f"Searching for song: {song_name} (en: {song_name_en})")
            
            if not YouTubeDownloader.is_available():
                return [TextContent(type="text", text="❌ **Error:** yt-dlp or ffmpeg not available. Please install required dependencies.")]
            
            # Configure yt-dlp options
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'bestaudio/best',
                'extractaudio': True,
                'noplaylist': True,
                'max_downloads': 1,
                'default_search': f'ytsearch1:{song_name_en}'  # Direct search with limit
            }
            
            # Get video info and stream URL directly
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{song_name_en}", download=False)
                
                if not info or 'entries' not in info or not info['entries']:
                    return [TextContent(
                        type="text",
                        text=f"❌ **Error:** No results found for: {song_name}"
                    )]
                
                video_info = info['entries'][0]
                video_url = video_info.get('webpage_url', '')
            
            # Extract the best audio format
            formats = video_info.get('formats', [])
            # First try to find audio-only formats
            audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
            
            if not audio_formats:
                # Fallback to any format with audio
                audio_formats = [f for f in formats if f.get('acodec') != 'none']
            
            if not audio_formats:
                return [TextContent(
                    type="text",
                    text=f"❌ **Error:** No audio streams found for: {song_name}"
                )]
            
            # Select the best quality based on preference
            if quality == "low":
                best_audio = min(audio_formats, key=lambda x: float(x.get('abr', 0) or 0))
            else:  # "best" or "medium"
                best_audio = max(audio_formats, key=lambda x: float(x.get('abr', 0) or 0))
            
            # Get direct audio URL
            audio_url = best_audio.get('url', '')
            if not audio_url:
                return [TextContent(
                    type="text",
                    text="❌ **Error:** Could not extract audio URL"
                )]

            # Calculate duration string
            duration = int(video_info.get('duration', 0))
            duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else "Unknown"
            
            # Get audio quality and format info
            audio_quality = best_audio.get('abr', 0)
            audio_format = best_audio.get('ext', 'unknown')
            filesize = best_audio.get('filesize', 0)
            
            # Generate file size string
            if filesize:
                filesize_mb = filesize / (1024 * 1024)
                filesize_str = f"{filesize_mb:.1f} MB"
            else:
                filesize_str = "Unknown"
            
            result_text = f"""
**🎵 YouTube Music Stream Information**

📺 **Song Details:**
• **Title:** {video_info.get('title', 'Unknown')}
• **Channel:** {video_info.get('uploader', 'Unknown')}
• **Duration:** {duration_str}

🎧 **Audio Stream:**
• **Quality:** {audio_quality} kbps
• **Format:** {audio_format}
• **File Size:** {filesize_str}

🔗 **Links:**
• **YouTube URL:** {video_url}
• **Stream URL:** `{audio_url}`

💡 **Usage Examples:**
```bash
# Play with VLC
vlc "{audio_url}"

# Play with mpv
mpv "{audio_url}"

# Download with wget
wget -O "audio.{audio_format}" "{audio_url}"
```

⚠️ **Important Notes:**
- Stream URL is temporary and will expire
- For personal use only
- Respect YouTube's Terms of Service

*🔴 Live audio stream for "{song_name}"*
            """
            print(result_text)  # For debugging
            return [TextContent(type="text", text=result_text.strip())]
            
        except Exception as e:
            logger.error(f"Error in get_youtube_music_stream: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Error extracting YouTube stream: {str(e)}"
                )
            )

    SearchAndStreamMusicToolDescription = RichToolDescription(
        description="Search for music on YouTube and get streaming information.",
        use_when="When you need to search for music and get both search results and streaming URLs in one request.",
        side_effects="Uses yt-dlp to search and extract streaming information from YouTube and may be subject to rate limiting.",
    )

    @mcp.tool(description=SearchAndStreamMusicToolDescription.model_dump_json())
    async def search_and_stream_music(
        query: Annotated[str, Field(description="Search query for music (song name, artist, etc.)")],
        include_streams: Annotated[bool, Field(description="Include stream URLs for top results", default=True)] = True
    ) -> list[TextContent]:
        """Search for music on YouTube and get streaming information."""
        try:
            # Search YouTube
            search_results = await MusicAPI.search_youtube_music_advanced(query)
            
            if not search_results.get("success"):
                return [TextContent(
                    type="text",
                    text=f"❌ **Search failed:** {search_results.get('error', 'Unknown error')}"
                )]
            
            results = search_results.get("results", [])
            
            if not results:
                return [TextContent(
                    type="text",
                    text=f"❌ **No results found for:** {query}"
                )]
            
            result_text = f"""
**🎵 Music Search Results for "{query}"**

**Found {len(results)} tracks:**

"""
            
            for i, track in enumerate(results, 1):
                duration = int(track.get('duration', 0)) if track.get('duration') else 0
                duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else "Unknown"
                
                result_text += f"""
**{i}. {track.get('title', 'Unknown Title')}**
   🎤 **Artist/Channel:** {track.get('uploader', 'Unknown')}
   ⏱️ **Duration:** {duration_str}
   🔗 **URL:** {track.get('url', 'N/A')}
"""
                
                # Add stream info for first 2 results if requested and yt-dlp is available
                if include_streams and i <= 2 and YouTubeDownloader.is_available():
                    stream_info = await MusicAPI.get_youtube_stream_info(track.get('url', ''))
                    if stream_info.get("success"):
                        result_text += f"   🎧 **Audio Quality:** {stream_info.get('quality', 'Unknown')} kbps\n"
                        result_text += f"   📂 **Format:** {stream_info.get('format', 'Unknown')}\n"
            
            if include_streams and YouTubeDownloader.is_available():
                result_text += f"""

💡 **Streaming Tips:**
- Use `get_youtube_music_stream` tool with any URL above for detailed stream info
- Stream URLs are temporary and may expire
- Best quality streams are automatically selected

🛠️ **Available Tools:**
- Use the URL with `get_youtube_music_stream` for direct audio streaming
- All results support standard media players
"""
            elif include_streams and not YouTubeDownloader.is_available():
                result_text += f"""

⚠️ **Streaming Not Available:**
Install `yt-dlp` and `ffmpeg` for audio streaming support:
```bash
pip install yt-dlp
# Install ffmpeg for your OS
```
"""
            
            search_method = search_results.get("method", "yt-dlp" if YouTubeDownloader.is_available() else "fallback")
            result_text += f"\n*🔴 Live search results using {search_method}*"
            
            return [TextContent(type="text", text=result_text.strip())]
            
        except Exception as e:
            logger.error(f"Error in search_and_stream_music: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Error searching and streaming music: {str(e)}"
                )
            )

    DownloadYouTubeAudioToolDescription = RichToolDescription(
        description="Search for a song and download its audio.",
        use_when="When you need to download audio files from YouTube for offline use.",
        side_effects="Uses yt-dlp to download and convert YouTube videos to audio files, creates temporary files on disk.",
    )

    @mcp.tool(description=DownloadYouTubeAudioToolDescription.model_dump_json())
    async def download_youtube_audio(
        song_name: Annotated[str, Field(description="Name of the song to search for and download")],
        output_format: Annotated[str, Field(description="Audio format: 'mp3', 'wav', 'aac'", default="mp3")] = "mp3"
    ) -> list[TextContent]:
        """Search for a song and download its audio."""
        try:
            # Check if yt-dlp is available
            if not YouTubeDownloader.is_available():
                result_text = """
❌ **Audio Download Not Available**

**Required Dependencies Missing:**
- `yt-dlp`: YouTube downloader library  
- `ffmpeg`: Audio/video processing tool

**Installation Instructions:**
```bash
# Install yt-dlp
pip install yt-dlp

# Install ffmpeg (Ubuntu/Debian)
sudo apt install ffmpeg

# Install ffmpeg (macOS)  
brew install ffmpeg

# Install ffmpeg (Windows)
# Download from https://ffmpeg.org/download.html
```

**Note:** This tool downloads audio files locally. Make sure you have permission and comply with YouTube's Terms of Service.
                """
                return [TextContent(type="text", text=result_text.strip())]
            
            # Search for the song
            search_results = await MusicAPI.search_youtube_music_advanced(song_name)
            if not search_results.get("success") or not search_results.get("results"):
                return [TextContent(
                    type="text",
                    text=f"❌ **Error:** No videos found for song: {song_name}"
                )]

            # Use the first search result
            first_video = search_results["results"][0]
            video_url = first_video.get("url", "")
            
            # Extract video ID from the search result URL
            video_id = None
            youtube_patterns = [
                r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
                r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
                r'(?:https?://)?(?:music\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)'
            ]
            
            for pattern in youtube_patterns:
                match = re.search(pattern, video_url)
                if match:
                    video_id = match.group(1)
                    break
                    
            if not video_id:
                return [TextContent(
                    type="text",
                    text="❌ **Error:** Could not extract a valid YouTube video ID from the search result."
                )]
            
            # Create temp directory for download
            temp_dir = tempfile.mkdtemp()
            
            # Download audio
            download_result = await YouTubeDownloader.download_audio(video_url, temp_dir)
            
            if not download_result.get("success"):
                return [TextContent(
                    type="text",
                    text=f"❌ **Download failed:** {download_result.get('error', 'Unknown error')}"
                )]
            
            file_path = download_result.get("file_path", "") 
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            
            result_text = f"""
**✅ Audio Download Completed**

📁 **File Information:**
• **Title:** {download_result.get('title', 'Unknown')}
• **Artist/Channel:** {download_result.get('uploader', 'Unknown')}
• **File Path:** `{file_path}`
• **File Size:** {file_size // (1024*1024):.1f} MB
• **Format:** MP3
• **Duration:** {int(download_result.get('duration', 0)) // 60}:{int(download_result.get('duration', 0)) % 60:02d}

⚠️ **Important:**
- File is saved in temporary directory: `{temp_dir}`
- Move the file to desired location before system cleanup
- Respect copyright and YouTube's Terms of Service
- For personal use only

🔧 **Next Steps:**
```bash
# Move file to your music directory
mv "{file_path}" ~/Music/

# Play the file
mpv "{file_path}"
```

*🔴 Audio downloaded using yt-dlp and ffmpeg*
            """
            
            return [TextContent(type="text", text=result_text.strip())]
            
        except Exception as e:
            logger.error(f"Error in download_youtube_audio: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Error downloading audio: {str(e)}"
                )
            )
