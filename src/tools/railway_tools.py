"""
Railway-related tools for train information and status.
Uses erail.in as the data source for real-time train information.
"""
from typing import Annotated, Optional, Dict, List, Any
from pydantic import Field
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR, TextContent
import httpx
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup
import random
import openai
import logging
from ..utils.helpers import translate_to_english

logger = logging.getLogger(__name__)


class RichToolDescription(openai.BaseModel):
    """Rich tool description model for MCP server compatibility."""
    description: str
    use_when: str
    side_effects: Optional[str]


class RailwayAPI:
    """Railway API client for erail.in"""
    
    BASE_URL = "https://erail.in"
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    ]
    
    @classmethod
    def get_random_user_agent(cls) -> str:
        return random.choice(cls.USER_AGENTS)
    
    @classmethod
    async def get_train_info(cls, train_no: str) -> Dict[str, Any]:
        """Get train information by train number"""
        url = f"{cls.BASE_URL}/rail/getTrains.aspx?TrainNo={train_no}&DataSource=0&Language=0&Cache=true"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    headers={"User-Agent": cls.get_random_user_agent()},
                    timeout=30
                )
                response.raise_for_status()
                return cls._parse_train_info(response.text)
            except Exception as e:
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message=f"Error fetching train info: {str(e)}"
                    )
                )

    @classmethod
    async def _translate_station_name(cls, station_name: str) -> str:
        """Translate station name to English if needed"""
        return await translate_to_english(station_name)

    @classmethod
    async def get_trains_between_stations(cls, from_station: str, to_station: str) -> Dict[str, Any]:
        """Get trains between two stations"""
        try:
            # Translate station names if needed
            from_station_en = await cls._translate_station_name(from_station)
            to_station_en = await cls._translate_station_name(to_station)
            
            url = f"{cls.BASE_URL}/rail/getTrains.aspx?Station_From={from_station_en}&Station_To={to_station_en}&DataSource=0&Language=0&Cache=true"
            
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(
                        url,
                        headers={"User-Agent": cls.get_random_user_agent()},
                        timeout=30
                    )
                    response.raise_for_status()
                    return cls._parse_between_stations(response.text)
                except Exception as e:
                    raise McpError(
                        ErrorData(
                            code=INTERNAL_ERROR,
                            message=f"Error fetching trains between stations: {str(e)}"
                        )
                    )
        except Exception as e:
            logger.error(f"Error in get_trains_between_stations: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Error processing train stations: {str(e)}"
                )
            )
    
    @classmethod
    async def get_train_route(cls, train_no: str) -> Dict[str, Any]:
        """Get complete route of a train"""
        # First get train info to get train_id
        train_info = await cls.get_train_info(train_no)
        if not train_info.get("success"):
            return train_info
        
        train_id = train_info["data"].get("train_id")
        if not train_id:
            return {"success": False, "data": "Train ID not found"}
        
        url = f"{cls.BASE_URL}/data.aspx?Action=TRAINROUTE&Password=2012&Data1={train_id}&Data2=0&Cache=true"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    headers={"User-Agent": cls.get_random_user_agent()},
                    timeout=30
                )
                response.raise_for_status()
                return cls._parse_train_route(response.text)
            except Exception as e:
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message=f"Error fetching train route: {str(e)}"
                    )
                )
    
    @classmethod
    async def get_station_live_status(cls, station_code: str) -> Dict[str, Any]:
        """Get live status of trains at a station"""
        url = f"{cls.BASE_URL}/station-live/{station_code}?DataSource=0&Language=0&Cache=true"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    headers={"User-Agent": cls.get_random_user_agent()},
                    timeout=30
                )
                response.raise_for_status()
                return cls._parse_station_live(response.text)
            except Exception as e:
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message=f"Error fetching station live status: {str(e)}"
                    )
                )
    
    @classmethod
    async def get_pnr_status(cls, pnr_number: str) -> Dict[str, Any]:
        """Get PNR status"""
        url = f"https://www.confirmtkt.com/pnr-status/{pnr_number}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    headers={"User-Agent": cls.get_random_user_agent()},
                    timeout=30
                )
                response.raise_for_status()
                return cls._parse_pnr_status(response.text)
            except Exception as e:
                logger.error(f"Error in get_pnr_status: {e}")
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message=f"Error fetching PNR status: {str(e)}"
                    )
                )
    
    @classmethod
    def _parse_train_info(cls, html_text: str) -> Dict[str, Any]:
        """Parse train information from HTML response"""
        try:
            retval = {"success": True, "time_stamp": int(datetime.now().timestamp() * 1000), "data": {}}
            
            data = html_text.split("~~~~~~~~")
            
            # Check for errors
            if (data[0] == "~~~~~Please try again after some time." or 
                data[0] == "~~~~~Train not found"):
                return {
                    "success": False,
                    "time_stamp": int(datetime.now().timestamp() * 1000),
                    "data": data[0].replace("~", "")
                }
            
            data1 = [item for item in data[0].split("~") if item]
            if len(data1[1]) > 6:
                data1.pop(0)
            
            obj = {
                "train_no": data1[1].replace("^", ""),
                "train_name": data1[2],
                "from_stn_name": data1[3],
                "from_stn_code": data1[4],
                "to_stn_name": data1[5],
                "to_stn_code": data1[6],
                "from_time": data1[11],
                "to_time": data1[12],
                "travel_time": data1[13],
                "running_days": data1[14]
            }
            
            if len(data) > 1:
                data2 = [item for item in data[1].split("~") if item]
                obj.update({
                    "type": data2[11] if len(data2) > 11 else "",
                    "train_id": data2[12] if len(data2) > 12 else "",
                    "distance_from_to": data2[18] if len(data2) > 18 else "",
                    "average_speed": data2[19] if len(data2) > 19 else ""
                })
            
            retval["data"] = obj
            return retval
            
        except Exception as e:
            return {
                "success": False,
                "time_stamp": int(datetime.now().timestamp() * 1000),
                "data": f"Error parsing train info: {str(e)}"
            }
    
    @classmethod
    def _parse_between_stations(cls, html_text: str) -> Dict[str, Any]:
        """Parse trains between stations from HTML response"""
        try:
            retval = {"success": True, "time_stamp": int(datetime.now().timestamp() * 1000), "data": []}
            
            data = html_text.split("~~~~~~~~")
            
            # Check for "No direct trains found"
            nore = data[0].split("~")
            if len(nore) > 5:
                nore = nore[5].split("<")
                if nore[0] == "No direct trains found":
                    return {
                        "success": False,
                        "time_stamp": int(datetime.now().timestamp() * 1000),
                        "data": nore[0]
                    }
            
            # Check for other errors
            error_messages = [
                "~~~~~Please try again after some time.",
                "~~~~~From station not found",
                "~~~~~To station not found"
            ]
            
            if data[0] in error_messages:
                return {
                    "success": False,
                    "time_stamp": int(datetime.now().timestamp() * 1000),
                    "data": data[0].replace("~", "")
                }
            
            data = [item for item in data if item]
            arr = []
            
            for item in data:
                data1 = item.split("~^")
                if len(data1) == 2:
                    data1 = [d for d in data1[1].split("~") if d]
                    if len(data1) >= 14:
                        obj = {
                            "train_no": data1[0],
                            "train_name": data1[1],
                            "source_stn_name": data1[2],
                            "source_stn_code": data1[3],
                            "dstn_stn_name": data1[4],
                            "dstn_stn_code": data1[5],
                            "from_stn_name": data1[6],
                            "from_stn_code": data1[7],
                            "to_stn_name": data1[8],
                            "to_stn_code": data1[9],
                            "from_time": data1[10],
                            "to_time": data1[11],
                            "travel_time": data1[12],
                            "running_days": data1[13]
                        }
                        arr.append({"train_base": obj})
            
            retval["data"] = arr
            return retval
            
        except Exception as e:
            return {
                "success": False,
                "time_stamp": int(datetime.now().timestamp() * 1000),
                "data": f"Error parsing between stations: {str(e)}"
            }
    
    @classmethod
    def _parse_train_route(cls, html_text: str) -> Dict[str, Any]:
        """Parse train route from HTML response"""
        try:
            retval = {"success": True, "time_stamp": int(datetime.now().timestamp() * 1000), "data": []}
            
            data = html_text.split("~^")
            arr = []
            
            for item in data:
                data1 = [d for d in item.split("~") if d]
                if len(data1) >= 10:
                    obj = {
                        "source_stn_name": data1[2] if len(data1) > 2 else "",
                        "source_stn_code": data1[1] if len(data1) > 1 else "",
                        "arrive": data1[3] if len(data1) > 3 else "",
                        "depart": data1[4] if len(data1) > 4 else "",
                        "distance": data1[6] if len(data1) > 6 else "",
                        "day": data1[7] if len(data1) > 7 else "",
                        "zone": data1[9] if len(data1) > 9 else ""
                    }
                    arr.append(obj)
            
            retval["data"] = arr
            return retval
            
        except Exception as e:
            return {
                "success": False,
                "time_stamp": int(datetime.now().timestamp() * 1000),
                "data": f"Error parsing train route: {str(e)}"
            }
    
    @classmethod
    def _parse_station_live(cls, html_text: str) -> Dict[str, Any]:
        """Parse station live status from HTML response"""
        try:
            retval = {"success": True, "time_stamp": int(datetime.now().timestamp() * 1000), "data": []}
            
            soup = BeautifulSoup(html_text, 'html.parser')
            arr = []
            
            name_elements = soup.find_all(class_='name')
            for el in name_elements:
                text = el.get_text().strip()
                if len(text) >= 5:
                    train_no = text[:5]
                    train_name = text[5:].strip()
                    
                    next_div = el.find_next_sibling('div')
                    route_text = next_div.get_text().strip() if next_div else ""
                    
                    source_stn = ""
                    dstn_stn = ""
                    if "→" in route_text:
                        parts = route_text.split("→")
                        source_stn = parts[0].strip()
                        dstn_stn = parts[1].strip() if len(parts) > 1 else ""
                    
                    # Get timing info
                    td_parent = el.find_parent('td')
                    next_td = td_parent.find_next_sibling('td') if td_parent else None
                    timing_text = next_td.get_text().strip() if next_td else ""
                    
                    time_at = timing_text[:5] if len(timing_text) >= 5 else ""
                    detail = timing_text[5:].strip() if len(timing_text) > 5 else ""
                    
                    obj = {
                        "train_no": train_no,
                        "train_name": train_name,
                        "source_stn_name": source_stn,
                        "dstn_stn_name": dstn_stn,
                        "time_at": time_at,
                        "detail": detail
                    }
                    arr.append(obj)
            
            retval["data"] = arr
            return retval
            
        except Exception as e:
            return {
                "success": False,
                "time_stamp": int(datetime.now().timestamp() * 1000),
                "data": f"Error parsing station live status: {str(e)}"
            }
    
    @classmethod
    def _parse_pnr_status(cls, html_text: str) -> Dict[str, Any]:
        """Parse PNR status from HTML response"""
        try:
            retval = {"success": True, "time_stamp": int(datetime.now().timestamp() * 1000), "data": {}}
            
            # Look for data pattern in JavaScript
            pattern = r'data\s*=\s*({.*?;)'
            match = re.search(pattern, html_text)
            
            if match:
                json_str = match.group(0)[7:-1]  # Remove 'data = ' and trailing ';'
                try:
                    data = json.loads(json_str)
                    retval["data"] = data
                    return retval
                except json.JSONDecodeError:
                    pass
            
            # Fallback: try to extract basic PNR info from HTML
            soup = BeautifulSoup(html_text, 'html.parser')
            
            # This is a simplified extraction - the actual website structure may vary
            pnr_info = {
                "pnr": "N/A",
                "train_name": "N/A",
                "journey_date": "N/A",
                "from": "N/A",
                "to": "N/A",
                "passengers": []
            }
            
            retval["data"] = pnr_info
            return retval
            
        except Exception as e:
            return {
                "success": False,
                "time_stamp": int(datetime.now().timestamp() * 1000),
                "data": f"Error parsing PNR status: {str(e)}"
            }


def register_railway_tools(mcp):
    """Register railway-related tools with the MCP server."""
    
    logger.info("Registering railway tools...")
    
    LiveTrainStatusToolDescription = RichToolDescription(
        description="Get real-time train location and status information",
        use_when="You want to check where a train is right now, if it's running on time, or any delays",
        side_effects="Makes HTTP requests to Indian Railways servers for live train data",
    )
    
    @mcp.tool(description=LiveTrainStatusToolDescription.model_dump_json())
    async def get_live_train_status(
        train_number: Annotated[str, Field(description="Train number (e.g., 12345)")],
        date: Annotated[str, Field(description="Date in YYYY-MM-DD format", default="")] = ""
    ) -> list[TextContent]:
        """Get live status and detailed information of a train."""
        try:
            logger.info(f"Getting live train status for train {train_number}")
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            
            # Get train information
            train_info = await RailwayAPI.get_train_info(train_number)
            
            if not train_info.get("success"):
                return [TextContent(
                    type="text", 
                    text=f"❌ **Error:** {train_info.get('data', 'Train not found')}"
                )]
            
            data = train_info["data"]
            
            result_text = f"""
**🚂 Train Status for {train_number}**

📋 **Train Details:**
• **Name:** {data.get('train_name', 'N/A')}
• **Number:** {data.get('train_no', train_number)}
• **Type:** {data.get('type', 'N/A')}

🛤️ **Route Information:**
• **From:** {data.get('from_stn_name', 'N/A')} ({data.get('from_stn_code', 'N/A')})
• **To:** {data.get('to_stn_name', 'N/A')} ({data.get('to_stn_code', 'N/A')})
• **Distance:** {data.get('distance_from_to', 'N/A')} km
• **Average Speed:** {data.get('average_speed', 'N/A')} km/h

⏰ **Timing:**
• **Departure:** {data.get('from_time', 'N/A')}
• **Arrival:** {data.get('to_time', 'N/A')}
• **Travel Time:** {data.get('travel_time', 'N/A')}

📅 **Running Days:** {data.get('running_days', 'N/A')}

📍 **Date:** {date}

*Last Updated: {datetime.fromtimestamp(train_info.get('time_stamp', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S')}*
            """
            
            return [TextContent(type="text", text=result_text.strip())]
            
        except Exception as e:
            logger.error(f"Error in get_live_train_status: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Error fetching train status: {str(e)}"
                )
            )

    trains_between_desc = RichToolDescription(
        description="Find all trains running between two stations",
        use_when="You want to know which trains run between specific stations and their timings",
        side_effects="Makes HTTP requests to get train schedule data"
    )

    @mcp.tool(description=trains_between_desc.model_dump_json())
    async def get_trains_between_stations(
        from_station: Annotated[str, Field(description="Source station code (e.g., NDLS, BCT)")],
        to_station: Annotated[str, Field(description="Destination station code (e.g., BCT, NDLS)")],
        source_lang: Annotated[str, Field(description="Source language code (e.g., 'hi', 'mr'). Use 'auto' for auto-detection.", default="auto")] = "auto",
        date: Annotated[str, Field(description="Date in DD-MM-YYYY format for filtering trains", default="")] = ""
    ) -> List[TextContent]:
        """Get trains between two stations."""
        try:
            logger.info(f"Getting trains between {from_station} and {to_station}")
            # Get trains between stations
            trains_data = await RailwayAPI.get_trains_between_stations(from_station, to_station, source_lang)
            
            if not trains_data.get("success"):
                return [TextContent(
                    type="text", 
                    text=f"❌ **Error:** {trains_data.get('data', 'No trains found between stations')}"
                )]
            
            trains = trains_data["data"]
            
            if not trains:
                return [TextContent(
                    type="text", 
                    text=f"❌ **No trains found between {from_station} and {to_station}**"
                )]
            
            result_text = f"""
**🚂 Trains from {from_station} to {to_station}**
{f"📅 **Date Filter:** {date}" if date else ""}

**Found {len(trains)} trains:**

"""
            
            for i, train_data in enumerate(trains, 1):
                train = train_data.get("train_base", {})
                result_text += f"""
**{i}. {train.get('train_name', 'N/A')} ({train.get('train_no', 'N/A')})**
🛤️ **Route:** {train.get('source_stn_name', 'N/A')} ({train.get('source_stn_code', 'N/A')}) → {train.get('dstn_stn_name', 'N/A')} ({train.get('dstn_stn_code', 'N/A')})
📍 **Journey:** {train.get('from_stn_name', 'N/A')} ({train.get('from_stn_code', 'N/A')}) → {train.get('to_stn_name', 'N/A')} ({train.get('to_stn_code', 'N/A')})
🕐 **Timing:** {train.get('from_time', 'N/A')} → {train.get('to_time', 'N/A')}
⏱️ **Duration:** {train.get('travel_time', 'N/A')}
📅 **Runs:** {train.get('running_days', 'N/A')}
"""
            
            result_text += f"\n*Last Updated: {datetime.fromtimestamp(trains_data.get('time_stamp', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S')}*"
            
            return [TextContent(type="text", text=result_text.strip())]
            
        except Exception as e:
            logger.error(f"Error in get_trains_between_stations: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Error fetching trains between stations: {str(e)}"
                )
            )

    PNRStatusToolDescription = RichToolDescription(
        description="Check PNR status for a railway booking.",
        use_when="When you need to retrieve current booking status, passenger information, seat details, and journey information from a PNR database.",
        side_effects="Makes HTTP requests to railway booking systems to fetch PNR information.",
    )

    @mcp.tool(description=PNRStatusToolDescription.model_dump_json())
    async def get_pnr_status_tool(
        pnr_number: Annotated[str, Field(description="10-digit PNR number")]
    ) -> list[TextContent]:
        """Check PNR status for a railway booking."""
        try:
            logger.info(f"Checking PNR status for: {pnr_number}")
            if len(pnr_number) != 10 or not pnr_number.isdigit():
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message="PNR number must be exactly 10 digits"
                    )
                )
            
            # Get PNR status
            pnr_data = await RailwayAPI.get_pnr_status(pnr_number)
            
            if not pnr_data.get("success"):
                return [TextContent(
                    type="text", 
                    text=f"❌ **Error:** {pnr_data.get('data', 'PNR status not found')}"
                )]
            
            data = pnr_data["data"]
            
            result_text = f"""
**🎫 PNR Status for {pnr_number}**

📋 **Booking Details:**
• **PNR:** {data.get('pnr', pnr_number)}
• **Train:** {data.get('train_name', 'N/A')}
• **Journey Date:** {data.get('journey_date', 'N/A')}
• **From:** {data.get('from', 'N/A')}
• **To:** {data.get('to', 'N/A')}

👥 **Passenger Details:**
"""
            
            passengers = data.get('passengers', [])
            if passengers:
                for i, passenger in enumerate(passengers, 1):
                    result_text += f"""
**{i}. {passenger.get('name', 'Passenger ' + str(i))}**
   • Age: {passenger.get('age', 'N/A')} | Gender: {passenger.get('gender', 'N/A')}
   • Current Status: {passenger.get('current_status', 'N/A')}
   • Booking Status: {passenger.get('booking_status', 'N/A')}
"""
            else:
                result_text += "\n*Passenger details not available*"
            
            result_text += f"\n*Last Updated: {datetime.fromtimestamp(pnr_data.get('time_stamp', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S')}*"
            
            return [TextContent(type="text", text=result_text.strip())]
            
        except Exception as e:
            if isinstance(e, McpError):
                raise
            logger.error(f"Error in get_pnr_status_tool: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Error fetching PNR status: {str(e)}"
                )
            )

    TrainScheduleToolDescription = RichToolDescription(
        description="Get complete schedule/route for a train with all stations.",
        use_when="When you need the full train route including all stops, arrival/departure times, platform numbers, and distance information.",
        side_effects="Makes HTTP requests to railway data sources to fetch complete train schedule information.",
    )

    @mcp.tool(description=TrainScheduleToolDescription.model_dump_json())
    async def get_train_schedule_tool(
        train_number: Annotated[str, Field(description="Train number (e.g., 12345)")]
    ) -> list[TextContent]:
        """Get complete schedule/route for a train with all stations."""
        try:
            logger.info(f"Getting train schedule for train {train_number}")
            # Get train route
            route_data = await RailwayAPI.get_train_route(train_number)
            
            if not route_data.get("success"):
                return [TextContent(
                    type="text", 
                    text=f"❌ **Error:** {route_data.get('data', 'Train route not found')}"
                )]
            
            stations = route_data["data"]
            
            if not stations:
                return [TextContent(
                    type="text", 
                    text=f"❌ **No route information found for train {train_number}**"
                )]
            
            result_text = f"""
**🚂 Complete Schedule for Train {train_number}**

**📍 Route with {len(stations)} stations:**

"""
            
            for i, station in enumerate(stations, 1):
                arrival = station.get('arrive', 'Start') if station.get('arrive') != '00:00' else 'Start'
                departure = station.get('depart', 'End') if station.get('depart') != '00:00' else 'End'
                
                result_text += f"""
**{i}. {station.get('source_stn_name', 'N/A')} ({station.get('source_stn_code', 'N/A')})**
   📍 Distance: {station.get('distance', 'N/A')} km
   🕐 Arrival: {arrival} | Departure: {departure}
   📅 Day: {station.get('day', 'N/A')} | Zone: {station.get('zone', 'N/A')}
"""
            
            result_text += f"\n*Last Updated: {datetime.fromtimestamp(route_data.get('time_stamp', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S')}*"
            
            return [TextContent(type="text", text=result_text.strip())]
            
        except Exception as e:
            logger.error(f"Error in get_train_schedule: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Error fetching train schedule: {str(e)}"
                )
            )

    StationLiveStatusToolDescription = RichToolDescription(
        description="Get live status of all trains currently at or arriving at a station.",
        use_when="When you need real-time information about trains at a specific station including expected arrival/departure times, platforms, and delays.",
        side_effects="Makes HTTP requests to railway data sources to fetch live station information.",
    )

    @mcp.tool(description=StationLiveStatusToolDescription.model_dump_json())
    async def get_station_live_status(
        station_code: Annotated[str, Field(description="Station code (e.g., NDLS, BCT, AGC)")]
    ) -> list[TextContent]:
        """Get live status of all trains currently at or arriving at a station."""
        try:
            logger.info(f"Getting live station status for {station_code}")
            # Get station live status
            station_data = await RailwayAPI.get_station_live_status(station_code)
            
            if not station_data.get("success"):
                return [TextContent(
                    type="text", 
                    text=f"❌ **Error:** {station_data.get('data', 'Station status not found')}"
                )]
            
            trains = station_data["data"]
            
            if not trains:
                return [TextContent(
                    type="text", 
                    text=f"❌ **No live train information available for station {station_code}**"
                )]
            
            result_text = f"""
**🚉 Live Status for Station {station_code}**

**🚂 {len(trains)} trains found:**

"""
            
            for i, train in enumerate(trains, 1):
                result_text += f"""
**{i}. {train.get('train_name', 'N/A')} ({train.get('train_no', 'N/A')})**
   🛤️ Route: {train.get('source_stn_name', 'N/A')} → {train.get('dstn_stn_name', 'N/A')}
   🕐 Time: {train.get('time_at', 'N/A')}
   📝 Status: {train.get('detail', 'N/A')}
"""
            
            result_text += f"\n*Last Updated: {datetime.fromtimestamp(station_data.get('time_stamp', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S')}*"
            
            return [TextContent(type="text", text=result_text.strip())]
            
        except Exception as e:
            logger.error(f"Error in get_station_live_status: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Error fetching station live status: {str(e)}"
                )
            )
