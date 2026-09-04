from abc import ABC, abstractmethod
from typing import List, Dict, Any, Type
from pydantic import BaseModel
from ai_orbit.crawling.http import AsyncHTTPClient
from ai_orbit.llm.orchestrator import LLMOrchestrator
from ai_orbit.llm.chunking import chunk_text
from ai_orbit.entity_resolution.resolver import EntityResolver
import logging

logger = logging.getLogger(__name__)

class BaseAdapter(ABC):
    def __init__(self, http_client: AsyncHTTPClient, llm: LLMOrchestrator, resolver: EntityResolver):
        self.http_client = http_client
        self.llm = llm
        self.resolver = resolver
        
    @abstractmethod
    async def discover(self) -> List[Dict[str, str]]:
        """Returns a list of dicts with 'url' and 'name' discovering the items."""
        pass
        
    async def process_item(self, item: Dict[str, str], schema: Type[BaseModel], entity_type: str) -> Any:
        url = item.get("url")
        name = item.get("name")
        
        # 1. Resolve Entity ID early to skip if already processed
        resolved_id, status = self.resolver.resolve(entity_type, name, url)
        if status in ["EXACT_URL", "EXACT_NAME", "ALIAS"]:
            logger.info(f"Skipping duplicate {entity_type}: {name}")
            return None # Already exists
            
        # 2. Fetch Text
        text = await self.http_client.extract_text(url)
        if not text:
            return None
            
        # 3. Handle 413 by chunking (for simple extraction we can take the first chunk or merge)
        chunks = chunk_text(text)
        if not chunks:
            return None
            
        target_text = chunks[0] # Take first 15k chars for basic extraction to avoid massive LLM calls for demo
        
        # 4. LLM Extraction
        try:
            extracted_data = await self.llm.extract(target_text, schema)
            return (resolved_id, extracted_data)
        except Exception as e:
            logger.error(f"Failed to extract {entity_type} from {url}: {e}")
            return None
