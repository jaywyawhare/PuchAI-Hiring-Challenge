"""
Configuration module for the MCP server.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Server configuration
TOKEN = os.getenv("TOKEN")
MY_NUMBER = os.getenv("MY_NUMBER")

if not TOKEN or not MY_NUMBER:
    raise ValueError("TOKEN and MY_NUMBER environment variables must be set")

# Server settings
HOST = "0.0.0.0"
PORT = 8085
SERVER_NAME = "PuchAI MCP Server"

# File paths
BASE_DIR = Path(__file__).parent.parent
RESUME_PATH = BASE_DIR / "resume.md"

# API configurations
RAILWAY_API_BASE = "https://indianrailapi.com/api/trains"
SEARCH_API_BASE = "https://api.duckduckgo.com"
MUSIC_API_BASE = "https://api.genius.com"

# Request settings
REQUEST_TIMEOUT = 30
USER_AGENT = "Puch/1.0 (Autonomous)"
IGNORE_ROBOTS_TXT = True
