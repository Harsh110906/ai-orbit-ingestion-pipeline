import feedparser
from typing import List, Dict
from ai_orbit.discovery.base import BaseAdapter
from ai_orbit.validation.schemas import PaperContent, EntityType, FullRecord, SourceProvenance
from ai_orbit.normalization.dates import normalize_date
import datetime

class ArxivAdapter(BaseAdapter):
    async def discover(self) -> List[Dict[str, str]]:
        # Use arXiv API for cs.AI (Artificial Intelligence)
        url = "http://export.arxiv.org/api/query?search_query=cat:cs.AI&start=0&max_results=10&sortBy=submittedDate&sortOrder=descending"
        
        # We can just fetch it as text, or use feedparser
        # feedparser handles the ATOM feed nicely
        try:
            # Doing a blocking call here for simplicity, but could be async
            feed = feedparser.parse(url)
            items = []
            for entry in feed.entries:
                items.append({
                    "name": entry.title,
                    "url": entry.link,
                    "published": entry.published,
                    "authors": [author.name for author in entry.authors],
                    "summary": entry.summary
                })
            return items
        except Exception:
            return []

    async def fetch_and_process(self) -> List[FullRecord]:
        items = await self.discover()
        records = []
        for item in items:
            resolved_id, status = self.resolver.resolve(EntityType.RESEARCH_PAPER, item["name"], item["url"])
            if status in ["EXACT_URL", "EXACT_NAME", "ALIAS"]:
                continue
                
            content = PaperContent(
                title=item["name"],
                authors=item["authors"],
                abstract=item["summary"],
                publication_date=normalize_date(item["published"]),
                github_url=None, # In a real scenario, we'd search the abstract for github links
                github_stars=None
            )
            
            record = FullRecord(
                id=resolved_id,
                recordType=EntityType.RESEARCH_PAPER,
                source=SourceProvenance(name="arXiv", url=item["url"]),
                content=content,
                collectedAt=datetime.datetime.utcnow().isoformat()
            )
            records.append(record)
        return records
