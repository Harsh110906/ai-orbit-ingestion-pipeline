import re
from typing import List

def chunk_text(text: str, max_chars: int = 15000) -> List[str]:
    """
    Intelligently splits text into chunks to handle HTTP 413 Payload Too Large.
    Splits by double newline, then single newline, then sentences if necessary.
    """
    if not text:
        return []
        
    if len(text) <= max_chars:
        return [text]

    chunks = []
    current_chunk = ""
    
    # Split by paragraphs
    paragraphs = re.split(r'\n\s*\n', text)
    
    for p in paragraphs:
        if len(current_chunk) + len(p) + 2 <= max_chars:
            current_chunk += p + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            if len(p) > max_chars:
                # Fallback to hard split if a single paragraph is too large
                for i in range(0, len(p), max_chars):
                    chunks.append(p[i:i+max_chars])
                current_chunk = ""
            else:
                current_chunk = p + "\n\n"
                
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks
