import json
import os
from typing import List, Dict, Any
from ai_orbit.config import Config

class JSONStorage:
    @staticmethod
    def save(filename: str, data: Any):
        filepath = os.path.join(Config.OUTPUT_DIR, filename)
        
        # Handle pydantic models
        if isinstance(data, list) and len(data) > 0 and hasattr(data[0], "model_dump"):
            data = [d.model_dump() for d in data]
        elif hasattr(data, "model_dump"):
            data = data.model_dump()
            
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
