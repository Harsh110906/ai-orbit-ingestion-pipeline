from datetime import datetime, timedelta
import re

def normalize_date(date_str: str) -> str:
    if not date_str:
        return ""
    
    date_str = date_str.lower().strip()
    
    # Handle relative dates
    if "today" in date_str:
        return datetime.utcnow().isoformat()
    if "yesterday" in date_str:
        return (datetime.utcnow() - timedelta(days=1)).isoformat()
        
    match = re.search(r'(\d+)\s*(hour|day|month|year)s?\s*ago', date_str)
    if match:
        val = int(match.group(1))
        unit = match.group(2)
        if unit == "hour":
            return (datetime.utcnow() - timedelta(hours=val)).isoformat()
        elif unit == "day":
            return (datetime.utcnow() - timedelta(days=val)).isoformat()
        elif unit == "month":
            return (datetime.utcnow() - timedelta(days=val*30)).isoformat()
        elif unit == "year":
            return (datetime.utcnow() - timedelta(days=val*365)).isoformat()

    try:
        # Try to parse standard formats
        for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%B %d, %Y", "%b %d, %Y"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.isoformat()
            except ValueError:
                continue
    except Exception:
        pass
        
    return ""

def is_within_24_hours(iso_timestamp: str) -> bool:
    if not iso_timestamp:
        return False
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        # If naive, make it aware (assuming UTC)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=None)
            now = datetime.utcnow()
        else:
            now = datetime.now(dt.tzinfo)
        return now - dt <= timedelta(hours=24)
    except ValueError:
        return False
