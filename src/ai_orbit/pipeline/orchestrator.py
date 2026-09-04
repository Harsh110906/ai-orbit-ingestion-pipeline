import asyncio
import logging
from typing import List

from ai_orbit.config import Config
from ai_orbit.crawling.http import AsyncHTTPClient
from ai_orbit.llm.orchestrator import LLMOrchestrator
from ai_orbit.entity_resolution.resolver import EntityResolver

from ai_orbit.discovery.papers import ArxivAdapter
from ai_orbit.discovery.tools import ToolsAdapter
from ai_orbit.discovery.github import GitHubAdapter
from ai_orbit.discovery.huggingface import HuggingFaceAdapter
from ai_orbit.discovery.news import NewsAdapter
from ai_orbit.discovery.jobs import JobsAdapter

from ai_orbit.validation.schemas import EntityType, ToolContent, AgentContent, MCPContent, DeviceContent, RobotContent, CompanyContent

from ai_orbit.storage.json import JSONStorage
from ai_orbit.storage.csv import CSVStorage
from ai_orbit.relationships.graph import RelationshipGraph

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    def __init__(self):
        self.llm = LLMOrchestrator()
        self.resolver = EntityResolver()
        self.graph = RelationshipGraph()

    async def run(self, mode: str = "demo", modules: List[str] = None):
        logger.info(f"Starting pipeline in {mode} mode for modules: {modules}")
        
        async with AsyncHTTPClient() as http_client:
            tasks = []
            
            # 1. Papers (ArXiv)
            if "papers" in modules or "all" in modules:
                tasks.append(self._run_adapter(ArxivAdapter(http_client, self.llm, self.resolver), "papers.json", "Papers.csv"))
                
            # 2. Tools (TAAFT/Direct blocked fallback + GitHub)
            if "tools" in modules or "all" in modules:
                tasks.append(self._run_adapter(ToolsAdapter(http_client, self.llm, self.resolver), "tools_direct.json", "Tools_Direct.csv"))
                tasks.append(self._run_github(GitHubAdapter(http_client, self.llm, self.resolver), "ai-tools", ToolContent, EntityType.TOOL, "tools.json", "Tools.csv"))
                
            # 3. Agents (GitHub)
            if "agents" in modules or "all" in modules:
                tasks.append(self._run_github(GitHubAdapter(http_client, self.llm, self.resolver), "ai-agents", AgentContent, EntityType.AGENT, "agents.json", "Agents.csv"))

            # 4. MCP (GitHub)
            if "mcp" in modules or "all" in modules:
                tasks.append(self._run_github(GitHubAdapter(http_client, self.llm, self.resolver), "mcp-server", MCPContent, EntityType.MCP, "mcp.json", "MCP.csv"))

            # 5. Devices (GitHub)
            if "devices" in modules or "all" in modules:
                tasks.append(self._run_github(GitHubAdapter(http_client, self.llm, self.resolver), "ai-hardware", DeviceContent, EntityType.DEVICE, "devices.json", "Devices.csv"))

            # 6. Robots (GitHub)
            if "robots" in modules or "all" in modules:
                tasks.append(self._run_github(GitHubAdapter(http_client, self.llm, self.resolver), "ai-robotics", RobotContent, EntityType.ROBOT, "robots.json", "Robots.csv"))

            # 7. Companies (GitHub)
            if "companies" in modules or "all" in modules:
                tasks.append(self._run_github(GitHubAdapter(http_client, self.llm, self.resolver), "ai-startup", CompanyContent, EntityType.COMPANY, "companies.json", "Companies.csv"))

            # 8. Models (HuggingFace)
            if "models" in modules or "all" in modules:
                tasks.append(self._run_adapter(HuggingFaceAdapter(http_client, self.llm, self.resolver), "models.json", "Models.csv"))

            # 9. News (RSS)
            if "news" in modules or "all" in modules:
                tasks.append(self._run_adapter(NewsAdapter(http_client, self.llm, self.resolver), "news.json", "News.csv"))

            # 10. Jobs (Remotive API)
            if "jobs" in modules or "all" in modules:
                tasks.append(self._run_adapter(JobsAdapter(http_client, self.llm, self.resolver), "jobs.json", "Jobs.csv"))

            # Run concurrently
            await asyncio.gather(*tasks)
            
        # Export entity mapping logs
        mapping_logs = self.resolver.get_logs()
        JSONStorage.save("entity_mapping.json", mapping_logs)
        CSVStorage.save("Entity_Mapping_Log.csv", mapping_logs)
        
        # Export relationships
        relationships = self.graph.get_relationships()
        JSONStorage.save("relationships.json", relationships)
        
        logger.info("Pipeline execution completed.")

    async def _run_adapter(self, adapter, json_file: str, csv_file: str):
        try:
            records = await adapter.fetch_and_process()
            JSONStorage.save(json_file, records)
            CSVStorage.save(csv_file, records)
            logger.info(f"Successfully processed {len(records)} records for {json_file}")
        except Exception as e:
            logger.error(f"Adapter failed for {json_file}: {e}")

    async def _run_github(self, adapter: GitHubAdapter, topic: str, schema: type, entity_type: EntityType, json_file: str, csv_file: str):
        try:
            records = await adapter.fetch_and_process_module(topic, schema, entity_type)
            JSONStorage.save(json_file, records)
            CSVStorage.save(csv_file, records)
            logger.info(f"Successfully processed {len(records)} records for {json_file}")
        except Exception as e:
            logger.error(f"GitHub Adapter failed for {topic}: {e}")
