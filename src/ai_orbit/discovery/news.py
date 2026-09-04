import feedparser
import datetime
import logging
from typing import List, Dict
from ai_orbit.discovery.base import BaseAdapter
from ai_orbit.validation.schemas import EntityType, FullRecord, SourceProvenance, NewsContent
from ai_orbit.normalization.dates import is_within_24_hours

logger = logging.getLogger(__name__)

class NewsAdapter(BaseAdapter):
    def __init__(self, http_client, llm, resolver):
        super().__init__(http_client, llm, resolver)
        self.feeds = [
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"
        ]

    async def discover(self) -> List[Dict[str, str]]:
        items = []
        for feed_url in self.feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    published = entry.get("published", "")
                    # Filter freshness
                    if is_within_24_hours(published):
                        items.append({
                            "name": entry.title,
                            "url": entry.link,
                            "published": published,
                            "summary": entry.get("summary", "")
                        })
            except Exception as e:
                logger.warning(f"Failed to parse news feed {feed_url}: {e}")
        return items

    async def fetch_and_process(self) -> List[FullRecord]:
        items = await self.discover()
        records = []
        for item in items:
            resolved_id, status = self.resolver.resolve(EntityType.NEWS, item["name"], item["url"])
            if status in ["EXACT_URL", "EXACT_NAME", "ALIAS"]:
                continue
                
            combined_text = f"Title: {item['name']}\nSummary: {item['summary']}\nPublished: {item['published']}\nURL: {item['url']}"
            
            try:
                extracted_data = await self.llm.extract(combined_text, NewsContent)
                record = FullRecord(
                    id=resolved_id,
                    recordType=EntityType.NEWS,
                    source=SourceProvenance(name="RSS", url=item["url"]),
                    content=extracted_data,
                    collectedAt=datetime.datetime.utcnow().isoformat()
                )
                records.append(record)
            except Exception as e:
                logger.error(f"Failed to extract News from {item['url']}: {e}")
                
        return records
