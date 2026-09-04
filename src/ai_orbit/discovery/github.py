import datetime
import logging
from typing import List, Dict
from ai_orbit.discovery.base import BaseAdapter
from ai_orbit.validation.schemas import EntityType, FullRecord, SourceProvenance, ToolContent, AgentContent, MCPContent, ModelContent, RobotContent, DeviceContent, CompanyContent

logger = logging.getLogger(__name__)

class GitHubAdapter(BaseAdapter):
    async def discover(self) -> List[Dict[str, str]]:
        return await self.discover_by_topic("ai")

    async def discover_by_topic(self, topic: str, max_results: int = 5) -> List[Dict[str, str]]:
        url = f"https://api.github.com/search/repositories?q=topic:{topic}&sort=stars&order=desc&per_page={max_results}"
        # We need a proper user-agent
        headers = {"User-Agent": "AI-Orbit-Data-Pipeline/1.0", "Accept": "application/vnd.github.v3+json"}
        
        async with self.http_client.session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                items = []
                for repo in data.get("items", []):
                    items.append({
                        "name": repo["name"],
                        "url": repo["html_url"],
                        "description": repo.get("description", ""),
                        "owner": repo["owner"]["login"],
                        "stars": repo["stargazers_count"],
                        "created_at": repo["created_at"],
                        "updated_at": repo["updated_at"]
                    })
                return items
            else:
                logger.warning(f"GitHub API returned {resp.status} for topic {topic}")
                return []

    async def fetch_and_process_module(self, topic: str, schema: type, entity_type: EntityType) -> List[FullRecord]:
        items = await self.discover_by_topic(topic)
        records = []
        for item in items:
            resolved_id, status = self.resolver.resolve(entity_type, item["name"], item["url"])
            if status in ["EXACT_URL", "EXACT_NAME", "ALIAS"]:
                continue
                
            # Try to fetch readme for detailed extraction if needed
            readme_url = f"https://raw.githubusercontent.com/{item['owner']}/{item['name']}/master/README.md"
            readme_text = await self.http_client.extract_text(readme_url)
            
            combined_text = f"Name: {item['name']}\nDescription: {item['description']}\nStars: {item['stars']}\nURL: {item['url']}\n\nReadme: {readme_text[:5000] if readme_text else ''}"
            
            try:
                extracted_data = await self.llm.extract(combined_text, schema)
                record = FullRecord(
                    id=resolved_id,
                    recordType=entity_type,
                    source=SourceProvenance(name="GitHub", url=item["url"]),
                    content=extracted_data,
                    collectedAt=datetime.datetime.utcnow().isoformat()
                )
                records.append(record)
            except Exception as e:
                logger.error(f"Failed to extract {entity_type} from GitHub {item['url']}: {e}")
                
        return records
