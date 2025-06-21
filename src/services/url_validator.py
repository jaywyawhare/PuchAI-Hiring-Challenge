"""
URL validation service.
"""
from urllib.parse import urlparse
from typing import Tuple


class URLValidator:
    """URL validation utility class."""
    
    @staticmethod
    def validate_url(url: str) -> Tuple[bool, str]:
        """Validate and clean URL."""
        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                url = f"https://{url}"
                parsed = urlparse(url)
            if not parsed.netloc:
                return False, "Invalid URL format"
            return True, url
        except Exception:
            return False, "Invalid URL format"
