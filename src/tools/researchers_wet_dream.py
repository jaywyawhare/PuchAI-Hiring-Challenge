"""
Register the researcher's wet dream tool for the MCP server.

Usage:
    from .researchers_wet_dream import register_researchers_wet_dream
    register_researchers_wet_dream(mcp)

This tool provides advanced autonomous research with thinking integration.
"""
from ..services.researchers_wet_dream_service import ResearchersWetDreamService


def register_researchers_wet_dream(mcp):
    """
    Register the researcher's wet dream tool with the MCP server.
    
    Features:
        - Multi-source deep research (Wikipedia, arXiv, Semantic Scholar, OpenAlex, PubMed)
        - Intelligent thinking integration with hypothesis generation
        - Self-iterating research process with autonomous direction adjustment
        - Comprehensive citation network analysis
        - Dynamic research planning and gap analysis
        - Cross-source validation and contradiction detection
    """
    researchers_wet_dream_service = ResearchersWetDreamService()
    researchers_wet_dream_service.register_tools(mcp) 