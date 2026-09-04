import csv
import os
from typing import List, Dict, Any
from ai_orbit.config import Config

class CSVStorage:
    @staticmethod
    def save(filename: str, data: List[Dict[str, Any]]):
        if not data:
            return
            
        filepath = os.path.join(Config.OUTPUT_DIR, filename)
        
        # Flatten Pydantic dicts if necessary
        flat_data = []
        for row in data:
            if hasattr(row, "model_dump"):
                row = row.model_dump()
            flat_row = {}
            for k, v in row.items():
                if isinstance(v, dict):
                    # stringify dicts
                    flat_row[k] = str(v)
                elif isinstance(v, list):
                    flat_row[k] = ", ".join([str(i) for i in v])
                else:
                    flat_row[k] = v
            flat_data.append(flat_row)
            
        keys = flat_data[0].keys()
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(flat_data)
