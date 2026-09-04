import logging
from typing import Dict, Any, Tuple
from ai_orbit.normalization.urls import normalize_url
from ai_orbit.normalization.names import normalize_name
from ai_orbit.deduplication.fuzzy import fuzzy_match
from ai_orbit.deduplication.exact import generate_deterministic_id
from datetime import datetime

logger = logging.getLogger(__name__)

class EntityResolver:
    def __init__(self):
        self.entities = {} # url/id -> record
        self.name_index = {} # normalized_name -> list of ids
        self.mapping_log = []

    def resolve(self, entity_type: str, raw_name: str, raw_url: str, aliases: list = None) -> Tuple[str, str]:
        """
        6-step resolution:
        1. canonical URL/domain
        2. normalized exact name
        3. aliases
        4. stable external IDs
        5. fuzzy matching
        6. manual-review state for uncertain matches
        
        Returns (resolved_id, resolution_status)
        """
        clean_url = normalize_url(raw_url)
        clean_name = normalize_name(raw_name)
        
        # 1. Canonical URL
        if clean_url and clean_url in self.entities:
            self._log_mapping(raw_name, clean_name, entity_type, "URL Match", 1.0, raw_url)
            return self.entities[clean_url], "EXACT_URL"
            
        # 2. Normalized Name
        if clean_name in self.name_index:
            matched_id = self.name_index[clean_name][0]
            self._log_mapping(raw_name, clean_name, entity_type, "Exact Name Match", 1.0, raw_url)
            return matched_id, "EXACT_NAME"
            
        # 3. Aliases (simplified)
        if aliases:
            for alias in aliases:
                clean_alias = normalize_name(alias)
                if clean_alias in self.name_index:
                    matched_id = self.name_index[clean_alias][0]
                    self._log_mapping(raw_name, clean_name, entity_type, "Alias Match", 0.9, raw_url)
                    return matched_id, "ALIAS"
                    
        # 4 & 5. Fuzzy Match
        for existing_name, ids in self.name_index.items():
            if fuzzy_match(clean_name, existing_name):
                matched_id = ids[0]
                self._log_mapping(raw_name, clean_name, entity_type, "Fuzzy Match", 0.85, raw_url)
                return matched_id, "REVIEW" # Require manual review for fuzzy
                
        # New entity
        new_id = generate_deterministic_id(clean_url, clean_name)
        if clean_url:
            self.entities[clean_url] = new_id
        if clean_name:
            if clean_name not in self.name_index:
                self.name_index[clean_name] = []
            self.name_index[clean_name].append(new_id)
            
        return new_id, "NEW"

    def _log_mapping(self, original: str, canonical: str, type_str: str, method: str, confidence: float, url: str):
        log_entry = {
            "original_value": original,
            "canonical_value": canonical,
            "entity_type": type_str,
            "matching_method": method,
            "confidence": confidence,
            "reason": f"Matched via {method}",
            "source_url": url,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.mapping_log.append(log_entry)
        
    def get_logs(self):
        return self.mapping_log
