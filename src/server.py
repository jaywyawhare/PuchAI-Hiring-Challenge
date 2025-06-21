"""
Main MCP server implementation with modular architecture.
"""
from typing import Optional
from fastmcp import FastMCP
from .models.auth import SimpleBearerAuthProvider
from .models.base import ToolRegistry
from .services.core_service import CoreService
from .services.web_service import WebService
from .services.railway_service import RailwayService
from .services.music_service import MusicService
from .services.weather_service import WeatherService
from .services.academic_service import AcademicService
from .services.news_service import NewsService
import logging

logger = logging.getLogger(__name__)


class MCPServer:
    """Main MCP server class with modular tool registration."""
    
    def __init__(self, token: str, name: str = "Chup AI - Intelligent Assistant for Puch AI"):
        self.token = token
        self.name = name
        self.mcp = FastMCP(name, auth=SimpleBearerAuthProvider(token))
        self.registry = ToolRegistry()
        self._setup_services()
        self._register_all_tools()
    
    def _setup_services(self):
        """Setup all tool services."""
        logger.info("Setting up services...")
        
        # Register all services
        self.registry.register_service(CoreService())
        self.registry.register_service(WebService())
        self.registry.register_service(RailwayService())
        self.registry.register_service(MusicService())
        self.registry.register_service(WeatherService())
        self.registry.register_service(AcademicService())
        self.registry.register_service(NewsService())
        
        logger.info("Services setup complete")
    
    def _register_all_tools(self):
        """Register all available tools with the MCP server."""
        logger.info("Registering all tools...")
        self.registry.register_all_tools(self.mcp)
        logger.info("All tools registered successfully")
    
    async def run(self, host: str = "0.0.0.0", port: int = 8085):
        """Run the MCP server."""
        logger.info(f"Starting {self.name} on {host}:{port}")
        await self.mcp.run_async("streamable-http", host=host, port=port)
    
    def get_mcp_instance(self) -> FastMCP:
        """Get the underlying FastMCP instance."""
        return self.mcp
    
    def get_registry(self) -> ToolRegistry:
        """Get the tool registry."""
        return self.registry
