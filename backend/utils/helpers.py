"""
Utility helper functions
"""
import re
from datetime import datetime
from typing import Optional


def sanitize_filename(name: str) -> str:
    """
    Sanitize a string to be used as a filename.
    
    Args:
        name: Original name
        
    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')
    # Limit length
    return sanitized[:100]

#format duration in milli seconds
#duration

def format_duration(ms: int) -> str:
    """
    Format duration in milliseconds to human-readable string.
    
    Args:
        ms: Duration in milliseconds
        
    Returns:
        Formatted duration string
    """
    if ms < 1000:
        return f"{ms}ms"
    elif ms < 60000:
        return f"{ms / 1000:.1f}s"
    else:
        minutes = ms // 60000
        seconds = (ms % 60000) / 1000
        return f"{minutes}m {seconds:.0f}s"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated text
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def timestamp_now() -> str:
    """Get current timestamp as ISO format string."""
    return datetime.now().isoformat()


def parse_timestamp(ts: str) -> Optional[datetime]:
    """Parse an ISO format timestamp string."""
    try:
        return datetime.fromisoformat(ts)
    except:
        return None
