import hashlib

def generate_deterministic_id(url: str, name: str) -> str:
    """Generate a deterministic ID based on URL or Name as fallback."""
    from ai_orbit.normalization.urls import normalize_url
    from ai_orbit.normalization.names import normalize_name
    
    clean_url = normalize_url(url)
    clean_name = normalize_name(name)
    
    key = clean_url if clean_url else clean_name
    if not key:
        import uuid
        return str(uuid.uuid4())
        
    return hashlib.sha256(key.encode('utf-8')).hexdigest()

def is_exact_duplicate(id_set: set, record_id: str) -> bool:
    return record_id in id_set
