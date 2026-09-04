import urllib.parse

def normalize_url(url: str) -> str:
    if not url:
        return ""
        
    try:
        parsed = urllib.parse.urlparse(url)
        # Force https and lowercase domain
        scheme = "https" if parsed.scheme in ["http", "https"] else parsed.scheme
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
            
        # Strip tracking params
        query_params = urllib.parse.parse_qsl(parsed.query)
        clean_params = [(k, v) for k, v in query_params if not k.startswith("utm_")]
        clean_query = urllib.parse.urlencode(clean_params)
        
        path = parsed.path.rstrip('/')
        if not path:
            path = "/"
            
        clean_url = urllib.parse.urlunparse((scheme, netloc, path, parsed.params, clean_query, ''))
        return clean_url
    except Exception:
        return url
