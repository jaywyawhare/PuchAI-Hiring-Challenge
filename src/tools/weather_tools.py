"""
Weather tools for fetching current weather and forecasts by location.
Uses Open-Meteo API for real-time weather data.
"""
from typing import Annotated, Dict, Any, Tuple, Optional
from pydantic import Field
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR, TextContent
from open_meteo import OpenMeteo
from open_meteo.models import HourlyParameters
from timezonefinder import TimezoneFinder
import pytz
from datetime import datetime
from dateutil.parser import isoparse
import openai
import logging
import pytz

logger = logging.getLogger(__name__)


class RichToolDescription(openai.BaseModel):
    """Rich tool description model for MCP server compatibility."""
    description: str
    use_when: str
    side_effects: Optional[str]

class WeatherError(Exception):
    """Custom exception for weather-related errors"""
    pass

class WeatherAPI:
    """Weather API client using Open-Meteo"""

    @staticmethod
    async def _get_coordinates(location: str) -> Tuple[float, float, str]:
        """Get coordinates for a location name"""
        try:
            async with OpenMeteo() as open_meteo:
                search = await open_meteo.geocoding(name=location)
                if not search.results:
                    raise WeatherError(f"Location '{location}' not found")
                result = search.results[0]
                return result.latitude, result.longitude, result.name
        except Exception as e:
            raise WeatherError(f"Error getting coordinates: {str(e)}")

    @classmethod
    async def get_current_weather(cls, location: str) -> Dict[str, Any]:
        """Get current weather for a location"""
        try:
            lat, lon, location_name = await cls._get_coordinates(location)

            # Get timezone from coordinates
            tf = TimezoneFinder()
            tz_name = tf.timezone_at(lat=lat, lng=lon)
            if not tz_name:
                raise WeatherError("Could not determine time zone for location")
            tz = pytz.timezone(tz_name)

            async with OpenMeteo() as open_meteo:
                forecast = await open_meteo.forecast(
                    latitude=lat,
                    longitude=lon,
                    current_weather=True,
                    hourly=[
                        HourlyParameters.TEMPERATURE_2M,
                        HourlyParameters.RELATIVE_HUMIDITY_2M,
                        HourlyParameters.WIND_SPEED_10M,
                    ]
                )

                # Use actual current local time (now) to align hourly forecast
                current_local = datetime.now(tz)

                # Convert forecast hourly times to local timezone
                hourly_local_times = [dt.astimezone(tz) for dt in forecast.hourly.time]

                # Find start index for the current local hour in hourly forecast
                start_index = next(
                    (i for i, dt in enumerate(hourly_local_times)
                     if dt.year == current_local.year and dt.month == current_local.month and dt.day == current_local.day and dt.hour == current_local.hour),
                    0
                )

                # Define end of local day and find end index in forecast
                end_of_day_local = current_local.replace(hour=23, minute=59, second=59, microsecond=0)
                end_index = next(
                    (i for i, dt in enumerate(hourly_local_times) if dt > end_of_day_local),
                    len(hourly_local_times)
                )

                # Prepare hourly data slices
                hourly_times_local_iso = [dt.isoformat() for dt in hourly_local_times[start_index:end_index]]

                hourly = {
                    "time": hourly_times_local_iso,
                    "temperature_2m": forecast.hourly.temperature_2m[start_index:end_index],
                    "relative_humidity_2m": forecast.hourly.relative_humidity_2m[start_index:end_index],
                    "wind_speed_10m": forecast.hourly.wind_speed_10m[start_index:end_index],
                }

                return {
                    "success": True,
                    "data": {
                        "location_name": location_name,
                        "timezone": tz_name,
                        "current": {
                            "temperature_2m": forecast.current_weather.temperature,
                            "wind_speed_10m": forecast.current_weather.wind_speed,
                            "time": current_local.isoformat(),
                        },
                        "hourly": hourly,
                    }
                }

        except WeatherError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}


def register_weather_tools(mcp):
    """Register weather-related tools with the MCP server."""

    logger.info("Registering weather tools...")

    WeatherToolDescription = RichToolDescription(
        description="Get current weather information for any location.",
        use_when="When you need current weather conditions, temperature, humidity, and wind information for a specific location.",
        side_effects="Makes API calls to Open-Meteo weather service to fetch real-time weather data.",
    )

    @mcp.tool(description=WeatherToolDescription.model_dump_json())
    async def get_weather(
        location: Annotated[str, Field(description="Location name (city, address)")],
    ) -> list[TextContent]:
        """Get current weather information for any location."""
        try:
            logger.info(f"Getting weather for location: {location}")
            weather_data = await WeatherAPI.get_current_weather(location)

            if not weather_data.get("success"):
                return [TextContent(
                    type="text",
                    text=f"❌ **Error:** {weather_data.get('error', 'Failed to fetch weather data')}"
                )]

            data = weather_data["data"]
            current = data["current"]
            hourly = data["hourly"]

            lines = [
                f"**🌡️ Weather in {data['location_name']} ({data['timezone']})**",
                "",
                "**Current Conditions:**",
                f"• Temperature: {current['temperature_2m']}°C",
                f"• Wind Speed: {current['wind_speed_10m']} km/h",
                f"• Relative Humidity: {hourly['relative_humidity_2m'][0]}%",
                "",
                "**Hourly Forecast (until midnight):**"
            ]

            for i, time_str in enumerate(hourly["time"]):
                local_time = isoparse(time_str).astimezone(pytz.timezone(data["timezone"]))
                lines.append(f"{local_time.strftime('%I:%M %p')}:")
                lines.append(f"• Temperature: {hourly['temperature_2m'][i]}°C")
                lines.append(f"• Wind Speed: {hourly['wind_speed_10m'][i]} km/h")
                lines.append(f"• Humidity: {hourly['relative_humidity_2m'][i]}%")

            lines.append("")
            lines.append(f"*Last Updated: {current['time']}*")

            result_text = "\n".join(lines)
            return [TextContent(type="text", text=result_text.strip())]

        except Exception as e:
            logger.error(f"Error in get_weather: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Error fetching weather data: {str(e)}"
                )
            )
