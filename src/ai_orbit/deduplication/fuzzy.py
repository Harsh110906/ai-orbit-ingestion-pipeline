import difflib

def fuzzy_match(name1: str, name2: str, threshold: float = 0.85) -> bool:
    """Returns True if the similarity ratio is above the threshold."""
    if not name1 or not name2:
        return False
    ratio = difflib.SequenceMatcher(None, name1.lower(), name2.lower()).ratio()
    return ratio >= threshold
