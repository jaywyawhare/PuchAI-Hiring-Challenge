"""
Weather service for weather information.
"""
from typing import Dict
from ..models.base import RichToolDescription, ToolService, BaseServiceConfig
import logging

logger = logging.getLogger(__name__)


class WeatherServiceConfig(BaseServiceConfig):
    """Configuration for weather service."""
    api_provider: str = "openweathermap"
    units: str = "metric"


class WeatherService(ToolService):
    """Weather service for current weather information."""
    
    def __init__(self, config: WeatherServiceConfig = None):
        super().__init__("weather")
        self.config = config or WeatherServiceConfig()
    
    def get_tool_descriptions(self) -> Dict[str, RichToolDescription]:
        """Get tool descriptions for weather service."""
        return {
            "get_weather": RichToolDescription(
                description="Get current weather information for any location.",
                use_when="When you need current weather conditions, temperature, humidity, and forecast for a specific location.",
                side_effects="Makes API calls to weather data providers and may be subject to rate limiting."
            )
        }
    
    def register_tools(self, mcp):
        """Register weather tools with the MCP server."""
        # Import the existing weather tools registration function
        from ..tools.weather_tools import register_weather_tools
        
        self.logger.info("Registering weather tools...")
        register_weather_tools(mcp)
        self.logger.info("Weather tools registered successfully")
