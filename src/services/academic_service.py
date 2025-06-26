"""
Academic service for arXiv paper search and retrieval.
"""
from typing import Dict
from ..models.base import RichToolDescription, ToolService, BaseServiceConfig
import logging

logger = logging.getLogger(__name__)


class AcademicServiceConfig(BaseServiceConfig):
    """Configuration for academic service."""
    arxiv_base_url: str = "https://arxiv.org"
    max_papers: int = 20
    rate_limit_delay: float = 3.0  # arXiv requires 3 second delays


class AcademicService(ToolService):
    """Academic service for arXiv paper search and retrieval."""
    
    def __init__(self, config: AcademicServiceConfig = None):
        super().__init__("academic")
        self.config = config or AcademicServiceConfig()
    
    def get_tool_descriptions(self) -> Dict[str, RichToolDescription]:
        """Get tool descriptions for academic service."""
        return {
            "search_arxiv_papers": RichToolDescription(
                description="Search for academic papers on arXiv.org with advanced query support.",
                use_when="User asks for academic papers, research, or scientific literature on specific topics.",
                side_effects="Makes API calls to arXiv.org and may be subject to rate limiting (3 second delays between requests)."
            ),
            "get_arxiv_paper": RichToolDescription(
                description="Get detailed information about a specific arXiv paper by its ID.",
                use_when="User provides a specific arXiv paper ID or asks for details about a known paper.",
                side_effects="Makes API calls to arXiv.org and may be subject to rate limiting (3 second delays between requests)."
            )
        }
    
    def register_tools(self, mcp):
        logger.info("Registering academic tools...")
        """Register academic tools with the MCP server."""
        # Import the existing arxiv tools registration function
        from ..tools.arxiv_tools import register_arxiv_tools
        
        register_arxiv_tools(mcp)
        logger.info("Academic tools registered.")
