"""
Base models and classes for the MCP server.
"""
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
import openai
import logging

logger = logging.getLogger(__name__)


class RichToolDescription(openai.BaseModel):
    """Rich tool description model for MCP server compatibility."""
    description: str
    use_when: str
    side_effects: Optional[str] = None


class BaseServiceConfig(openai.BaseModel):
    """Base configuration for services."""
    timeout: int = 30
    max_retries: int = 3
    rate_limit_delay: float = 0.0


class BaseAPIClient(ABC):
    """Base class for API clients with common functionality."""
    
    def __init__(self, config: BaseServiceConfig = None):
        self.config = config or BaseServiceConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def log_info(self, message: str):
        """Log info message."""
        self.logger.info(message)
    
    def log_error(self, message: str):
        """Log error message."""
        self.logger.error(message)
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the service is healthy."""
        pass


class ToolService(ABC):
    """Base class for tool services."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"ToolService.{name}")
    
    @abstractmethod
    def get_tool_descriptions(self) -> Dict[str, RichToolDescription]:
        """Get tool descriptions for this service."""
        pass
    
    @abstractmethod
    def register_tools(self, mcp):
        """Register tools with the MCP server."""
        pass


class ToolRegistry:
    """Central registry for managing tool services."""
    
    def __init__(self):
        self.services: Dict[str, ToolService] = {}
        self.logger = logging.getLogger("ToolRegistry")
    
    def register_service(self, service: ToolService):
        """Register a tool service."""
        self.services[service.name] = service
        self.logger.info(f"Registered service: {service.name}")
    
    def get_service(self, name: str) -> Optional[ToolService]:
        """Get a service by name."""
        return self.services.get(name)
    
    def get_all_services(self) -> List[ToolService]:
        """Get all registered services."""
        return list(self.services.values())
    
    def register_all_tools(self, mcp):
        """Register all tools from all services."""
        for service in self.services.values():
            try:
                service.register_tools(mcp)
                self.logger.info(f"Successfully registered tools for service: {service.name}")
            except Exception as e:
                self.logger.error(f"Failed to register tools for service {service.name}: {e}")
                raise


class ContentProcessor:
    """Base class for content processing utilities."""
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 5000, start_index: int = 0) -> tuple[str, bool]:
        """Truncate text with pagination support."""
        if start_index >= len(text):
            return "", False
        
        end_index = start_index + max_length
        truncated = text[start_index:end_index]
        has_more = end_index < len(text)
        
        return truncated, has_more
    
    @staticmethod
    def format_error_response(error_msg: str, suggestions: List[str] = None) -> str:
        """Format error response with suggestions."""
        response = [f"❌ Error: {error_msg}"]
        if suggestions:
            response.append("\n💡 Suggestions:")
            response.extend([f"- {s}" for s in suggestions])
        return "\n".join(response)
