"""
Tools package for the MCP server.
"""
from .core_tools import register_core_tools
from .web_tools import register_web_tools
from .railway_tools import register_railway_tools
from .music_tools import register_music_tools
from .weather_tools import register_weather_tools
from .arxiv_tools import register_arxiv_tools
from .hn_tools import register_hn_tools

__all__ = [
    "register_core_tools",
    "register_web_tools",
    "register_railway_tools", 
    "register_music_tools",
    "register_weather_tools",
    "register_arxiv_tools",
    "register_hn_tools"
]