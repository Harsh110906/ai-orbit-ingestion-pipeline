import datetime
import logging
from typing import List, Dict
from ai_orbit.discovery.base import BaseAdapter
from ai_orbit.validation.schemas import EntityType, FullRecord, SourceProvenance, JobContent
from ai_orbit.normalization.dates import is_within_24_hours

logger = logging.getLogger(__name__)

class JobsAdapter(BaseAdapter):
    async def discover(self) -> List[Dict[str, str]]:
        url = "https://remotive.com/api/remote-jobs?category=software-dev&limit=10"
        headers = {"User-Agent": "AI-Orbit-Data-Pipeline/1.0"}
        
        async with self.http_client.session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                items = []
                for job in data.get("jobs", []):
                    published = job.get("publication_date", "")
                    if is_within_24_hours(published):
                        items.append({
                            "name": job["title"],
                            "url": job["url"],
                            "company": job["company_name"],
                            "published": published,
                            "description": job["description"]
                        })
                return items
            else:
                logger.warning(f"Jobs API returned {resp.status}")
                return []

    async def fetch_and_process(self) -> List[FullRecord]:
        items = await self.discover()
        records = []
        for item in items:
            resolved_id, status = self.resolver.resolve(EntityType.JOB, item["name"], item["url"])
            if status in ["EXACT_URL", "EXACT_NAME", "ALIAS"]:
                continue
                
            combined_text = f"Job Title: {item['name']}\nCompany: {item['company']}\nPublished: {item['published']}\nURL: {item['url']}\nDescription: {item['description'][:2000]}"
            
            try:
                extracted_data = await self.llm.extract(combined_text, JobContent)
                record = FullRecord(
                    id=resolved_id,
                    recordType=EntityType.JOB,
                    source=SourceProvenance(name="Remotive API", url=item["url"]),
                    content=extracted_data,
                    collectedAt=datetime.datetime.utcnow().isoformat()
                )
                records.append(record)
            except Exception as e:
                logger.error(f"Failed to extract Job from {item['url']}: {e}")
                
        return records
