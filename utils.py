"""Utility functions module"""
from typing import List

def parse_usernames(text: str) -> List[str]:
    """Parse usernames from text, handling various formats"""
    text = text.replace('@', '').replace(',', ' ').replace('\n', ' ')
    usernames = [username.strip().lower() for username in text.split() if username.strip()]
    return list(dict.fromkeys(usernames))  # Remove duplicates while preserving order

def format_elapsed_time(seconds: float) -> str:
    """Format elapsed time in human-readable format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = round(seconds % 60, 1)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return ' '.join(parts)

def format_count(count: int) -> str:
    """Format follower/following count with K/M suffixes"""
    if count >= 1_000_000:
        return f"{count/1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count/1_000:.1f}K"
    return str(count)

def is_admin(user_id: int, admin_ids: List[int]) -> bool:
    """Check if user is admin"""
    return user_id in admin_ids

def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text to max length with ellipsis"""
    if len(text) > max_length:
        return text[:max_length] + '...'
    return text