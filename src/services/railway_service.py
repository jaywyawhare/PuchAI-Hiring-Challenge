"""
Railway service for Indian Railway information.
"""
from typing import Dict, Annotated, List
from mcp.types import TextContent
from ..models.base import RichToolDescription, ToolService, BaseAPIClient, BaseServiceConfig
from pydantic import Field
import logging

logger = logging.getLogger(__name__)


class RailwayServiceConfig(BaseServiceConfig):
    """Configuration for railway service."""
    base_url: str = "https://erail.in"
    

class RailwayService(ToolService):
    """Railway service for Indian Railway data."""
    
    def __init__(self, config: RailwayServiceConfig = None):
        super().__init__("railway")
        self.config = config or RailwayServiceConfig()
    
    def get_tool_descriptions(self) -> Dict[str, RichToolDescription]:
        """Get tool descriptions for railway service."""
        return {
            "get_live_train_status": RichToolDescription(
                description="Get live status and detailed information of a train.",
                use_when="Fetches current location, delays, and status updates for a running train from Indian Railways live data.",
                side_effects="Makes API calls to Indian Railways data sources and may be subject to rate limiting."
            ),
            "get_trains_between_stations": RichToolDescription(
                description="Get all trains running between two stations.",
                use_when="Retrieves a comprehensive list of trains with schedules and timing information for the specified route.",
                side_effects="Makes API calls to Indian Railways data sources and may be subject to rate limiting."
            ),
            "get_pnr_status_tool": RichToolDescription(
                description="Check PNR status for a railway booking.",
                use_when="Retrieves current booking status, passenger information, seat details, and journey information from the PNR database.",
                side_effects="Makes API calls to Indian Railways PNR system and may be subject to rate limiting."
            ),
            "get_train_schedule_tool": RichToolDescription(
                description="Get complete schedule/route for a train with all stations.",
                use_when="Retrieves the full train route including all stops, arrival/departure times, platform numbers, and distance information.",
                side_effects="Makes API calls to Indian Railways data sources and may be subject to rate limiting."
            ),
            "get_station_live_status": RichToolDescription(
                description="Get live status of all trains currently at or arriving at a station.",
                use_when="Displays real-time information about trains at the specified station including expected arrival/departure times, platforms, and delays.",
                side_effects="Makes API calls to Indian Railways live data sources and may be subject to rate limiting."
            )
        }
    
    def register_tools(self, mcp):
        """Register railway tools with the MCP server."""
        # Import the existing railway tools registration function
        from ..tools.railway_tools import register_railway_tools
        
        self.logger.info("Registering railway tools...")
        register_railway_tools(mcp)
        self.logger.info("Railway tools registered successfully")
