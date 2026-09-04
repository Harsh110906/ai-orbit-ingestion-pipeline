from typing import List, Dict
from ai_orbit.discovery.base import BaseAdapter
from ai_orbit.validation.schemas import ToolContent, EntityType, FullRecord, SourceProvenance
import datetime
import logging

logger = logging.getLogger(__name__)

class ToolsAdapter(BaseAdapter):
    async def discover(self) -> List[Dict[str, str]]:
        # For demonstration without massive crawling of TAAFT which might block us,
        # we provide a few legitimate AI tool URLs to extract from directly.
        return [
            {"name": "ChatGPT", "url": "https://openai.com/chatgpt"},
            {"name": "Midjourney", "url": "https://www.midjourney.com/"},
            {"name": "Perplexity", "url": "https://www.perplexity.ai/"}
        ]

    async def fetch_and_process(self) -> List[FullRecord]:
        items = await self.discover()
        records = []
        for item in items:
            result = await self.process_item(item, ToolContent, EntityType.TOOL)
            if result:
                resolved_id, content = result
                record = FullRecord(
                    id=resolved_id,
                    recordType=EntityType.TOOL,
                    source=SourceProvenance(name="Official Website", url=item["url"]),
                    content=content,
                    collectedAt=datetime.datetime.utcnow().isoformat()
                )
                records.append(record)
        return records
