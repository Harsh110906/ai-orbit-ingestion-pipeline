import re

def normalize_name(name: str) -> str:
    if not name:
        return ""
    # Remove Inc., LLC, etc.
    name = re.sub(r'(?i)\b(inc|llc|corp|ltd|co)\.?\b', '', name)
    # Remove special chars and extra spaces
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip().lower()
