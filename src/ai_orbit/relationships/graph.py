from typing import List, Dict, Any

class RelationshipGraph:
    def __init__(self):
        self.relationships = []

    def add_relationship(self, source_id: str, target_id: str, relation_type: str):
        self.relationships.append({
            "source": source_id,
            "target": target_id,
            "type": relation_type
        })
        
    def get_relationships(self) -> List[Dict[str, str]]:
        return self.relationships
