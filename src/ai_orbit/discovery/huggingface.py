import datetime
import logging
from typing import List, Dict
from ai_orbit.discovery.base import BaseAdapter
from ai_orbit.validation.schemas import EntityType, FullRecord, SourceProvenance, ModelContent

logger = logging.getLogger(__name__)

class HuggingFaceAdapter(BaseAdapter):
    async def discover(self, max_results: int = 5) -> List[Dict[str, str]]:
        url = f"https://huggingface.co/api/models?sort=downloads&direction=-1&limit={max_results}"
        headers = {"User-Agent": "AI-Orbit-Data-Pipeline/1.0"}
        
        async with self.http_client.session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                items = []
                for model in data:
                    items.append({
                        "name": model["id"],
                        "url": f"https://huggingface.co/{model['id']}",
                        "pipeline_tag": model.get("pipeline_tag", ""),
                        "downloads": model.get("downloads", 0),
                        "tags": model.get("tags", [])
                    })
                return items
            else:
                logger.warning(f"HF API returned {resp.status}")
                return []

    async def fetch_and_process(self) -> List[FullRecord]:
        items = await self.discover()
        records = []
        for item in items:
            resolved_id, status = self.resolver.resolve(EntityType.MODEL, item["name"], item["url"])
            if status in ["EXACT_URL", "EXACT_NAME", "ALIAS"]:
                continue
                
            combined_text = f"Model Name: {item['name']}\nTask: {item['pipeline_tag']}\nDownloads: {item['downloads']}\nTags: {', '.join(item['tags'])}\nURL: {item['url']}"
            
            try:
                extracted_data = await self.llm.extract(combined_text, ModelContent)
                record = FullRecord(
                    id=resolved_id,
                    recordType=EntityType.MODEL,
                    source=SourceProvenance(name="HuggingFace", url=item["url"]),
                    content=extracted_data,
                    collectedAt=datetime.datetime.utcnow().isoformat()
                )
                records.append(record)
            except Exception as e:
                logger.error(f"Failed to extract Model from HF {item['url']}: {e}")
                
        return records
