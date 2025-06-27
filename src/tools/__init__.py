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
from .deep_research import register_deep_research_tools
from .thinking_tool import register_thinking_tool
from .researchers_wet_dream import register_researchers_wet_dream

__all__ = [
    "register_core_tools",
    "register_web_tools",
    "register_railway_tools", 
    "register_music_tools",
    "register_weather_tools",
    "register_arxiv_tools",
    "register_hn_tools",
    "register_deep_research_tools",
    "register_thinking_tool",
    "register_researchers_wet_dream"
]

def register_all_tools(mcp):
    """Register all available tools including unified deep research"""
    register_core_tools(mcp)
    register_web_tools(mcp)
    register_railway_tools(mcp)
    register_music_tools(mcp)
    register_weather_tools(mcp)
    register_arxiv_tools(mcp)
    register_hn_tools(mcp)
    register_deep_research_tools(mcp)
    register_thinking_tool(mcp)
    register_researchers_wet_dream(mcp)