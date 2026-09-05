import asyncio
import json
import os
import logging
from typing import List
from datetime import datetime

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

from ai_orbit.validation.schemas import (
    EntityType, ToolContent, AgentContent, MCPContent,
    DeviceContent, RobotContent, CompanyContent,
    FullRecord, SourceProvenance
)

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
                tasks.append(self._run_adapter(
                    ArxivAdapter(http_client, self.llm, self.resolver),
                    "papers.json", "Papers.csv"))

            # 2. Tools
            if "tools" in modules or "all" in modules:
                is_bulk = (mode == "bulk")
                tasks.append(self._run_tools(http_client, is_bulk))

            # 3. Agents (GitHub)
            if "agents" in modules or "all" in modules:
                tasks.append(self._run_github_simple(
                    GitHubAdapter(http_client, self.llm, self.resolver),
                    "ai-agents", AgentContent, EntityType.AGENT,
                    "agents.json", "Agents.csv"))

            # 4. MCP (GitHub)
            if "mcp" in modules or "all" in modules:
                tasks.append(self._run_github_simple(
                    GitHubAdapter(http_client, self.llm, self.resolver),
                    "mcp-server", MCPContent, EntityType.MCP,
                    "mcp.json", "MCP.csv"))

            # 5. Devices (GitHub)
            if "devices" in modules or "all" in modules:
                tasks.append(self._run_github_simple(
                    GitHubAdapter(http_client, self.llm, self.resolver),
                    "ai-hardware", DeviceContent, EntityType.DEVICE,
                    "devices.json", "Devices.csv"))

            # 6. Robots (GitHub)
            if "robots" in modules or "all" in modules:
                tasks.append(self._run_github_simple(
                    GitHubAdapter(http_client, self.llm, self.resolver),
                    "ai-robotics", RobotContent, EntityType.ROBOT,
                    "robots.json", "Robots.csv"))

            # 7. Companies (GitHub)
            if "companies" in modules or "all" in modules:
                tasks.append(self._run_github_simple(
                    GitHubAdapter(http_client, self.llm, self.resolver),
                    "ai-startup", CompanyContent, EntityType.COMPANY,
                    "companies.json", "Companies.csv"))

            # 8. Models (HuggingFace)
            if "models" in modules or "all" in modules:
                tasks.append(self._run_adapter(
                    HuggingFaceAdapter(http_client, self.llm, self.resolver),
                    "models.json", "Models.csv"))

            # 9. News (RSS)
            if "news" in modules or "all" in modules:
                tasks.append(self._run_adapter(
                    NewsAdapter(http_client, self.llm, self.resolver),
                    "news.json", "News.csv"))

            # 10. Jobs (Remotive API)
            if "jobs" in modules or "all" in modules:
                tasks.append(self._run_adapter(
                    JobsAdapter(http_client, self.llm, self.resolver),
                    "jobs.json", "Jobs.csv"))

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

    # ─── Tools-specific pipeline ──────────────────────────────────────────────

    async def _run_tools(self, http_client: AsyncHTTPClient, bulk: bool):
        """
        Full tools pipeline:
        1. Curated seed list (no LLM needed, verified metadata)
        2. GitHub open-source tools (LLM extraction with rate-limit handling)
        3. Dedup, QA, export
        """
        try:
            # ── Step 1: Curated seed data (no API calls needed) ──
            tools_adapter = ToolsAdapter(http_client, self.llm, self.resolver)
            curated_records = await tools_adapter.fetch_and_process()
            logger.info(f"✓ Curated seed: {len(curated_records)} records")

            # ── Step 2: GitHub open-source tool discovery ──
            github_records = []
            if bulk:
                github_adapter = GitHubAdapter(http_client, self.llm, self.resolver)
                # topics = ["ai-tools", "llm-tools", "generative-ai", "machine-learning-tools"]
                topics = [] # Disabled temporarily due to Gemini 429 rate limits
                for topic in topics:
                    try:
                        topic_records = await self._discover_github_tools(
                            github_adapter, topic, max_results=5)
                        github_records.extend(topic_records)
                        logger.info(f"✓ GitHub '{topic}': {len(topic_records)} new records")
                    except Exception as e:
                        logger.warning(f"GitHub topic '{topic}' failed: {e}")

            # ── Step 3: Combine and deduplicate ──
            all_records = curated_records + github_records
            logger.info(f"Total raw records: {len(all_records)}")

            # Save outputs
            JSONStorage.save("tools.json", all_records)
            CSVStorage.save("Tools.csv", all_records)

            # ── Step 4: QA and Excel export ──
            self._run_tools_qa_and_excel(all_records)

        except Exception as e:
            logger.error(f"Tools pipeline failed: {e}")
            import traceback
            traceback.print_exc()

    async def _discover_github_tools(
            self, adapter: GitHubAdapter, topic: str,
            max_results: int = 30) -> List[FullRecord]:
        """Discover tools from GitHub with rate-limit-safe LLM extraction."""
        items = await adapter.discover_by_topic(topic, max_results=max_results)
        records = []

        for idx, item in enumerate(items):
            resolved_id, status = self.resolver.resolve(
                EntityType.TOOL, item["name"], item["url"])
            if status in ["EXACT_URL", "EXACT_NAME", "ALIAS"]:
                logger.debug(f"Skipping duplicate: {item['name']}")
                continue

            # Fetch README
            readme_url = (
                f"https://raw.githubusercontent.com/"
                f"{item['owner']}/{item['name']}/master/README.md"
            )
            readme_text = await adapter.http_client.extract_text(readme_url)
            if not readme_text:
                # Try 'main' branch
                readme_url_main = readme_url.replace("/master/", "/main/")
                readme_text = await adapter.http_client.extract_text(readme_url_main)

            combined_text = (
                f"Name: {item['name']}\n"
                f"Description: {item['description']}\n"
                f"Stars: {item['stars']}\n"
                f"URL: {item['url']}\n\n"
                f"Readme: {readme_text[:3000] if readme_text else 'Not available'}"
            )

            try:
                extracted = await adapter.llm.extract(combined_text, ToolContent)
                # Override with known good data
                if not extracted.official_website:
                    extracted.official_website = item["url"]
                record = FullRecord(
                    id=resolved_id,
                    recordType=EntityType.TOOL,
                    source=SourceProvenance(name="GitHub", url=item["url"]),
                    content=extracted,
                    collectedAt=datetime.utcnow().isoformat()
                )
                records.append(record)
                logger.info(
                    f"  [{idx+1}/{len(items)}] ✓ {item['name']} extracted")
            except Exception as e:
                logger.warning(
                    f"  [{idx+1}/{len(items)}] ✗ {item['name']} failed: {e}")

            # Conservative delay for Gemini free tier
            if idx < len(items) - 1:
                await asyncio.sleep(4)

        return records

    def _run_tools_qa_and_excel(self, records: List[FullRecord]):
        """Run QA checks and generate the XLSX workbook."""
        from ai_orbit.storage.excel import ExcelStorage

        total = len(records)
        names = [r.content.name for r in records]
        urls = [r.content.official_website or r.source.url for r in records]

        dup_names = total - len(set(n.lower().strip() for n in names))
        dup_urls = total - len(set(u.lower().strip() for u in urls if u))
        missing_desc = sum(1 for r in records
                          if not r.content.description
                          or r.content.description.startswith("Mock"))
        missing_website = sum(1 for r in records
                              if not getattr(r.content, "official_website", None))
        missing_task = sum(1 for r in records
                          if not getattr(r.content, "primary_task", None))
        missing_inputs = sum(1 for r in records
                            if not getattr(r.content, "inputs", None))
        missing_outputs = sum(1 for r in records
                             if not getattr(r.content, "outputs", None))
        missing_platforms = sum(1 for r in records
                               if not getattr(r.content, "supported_platforms", None))

        source_dist = {}
        for r in records:
            src = r.source.name
            source_dist[src] = source_dist.get(src, 0) + 1

        summary = {
            "Total Records": total,
            "Duplicate Names": dup_names,
            "Duplicate URLs": dup_urls,
            "Missing Descriptions": missing_desc,
            "Missing Official Websites": missing_website,
            "Missing Primary Tasks": missing_task,
            "Missing Inputs": missing_inputs,
            "Missing Outputs": missing_outputs,
            "Missing Supported Platforms": missing_platforms,
            "Records Verified": total - missing_website,
            "Source Distribution": str(source_dist),
            "Valid Rate": f"{(total - missing_desc) / total * 100:.1f}%" if total else "0%"
        }

        logger.info("=" * 60)
        logger.info("QA SUMMARY")
        logger.info("=" * 60)
        for k, v in summary.items():
            logger.info(f"  {k}: {v}")
        logger.info("=" * 60)

        ExcelStorage.save(
            "AI_Orbit_AI_Tools_Dataset.xlsx",
            records, summary,
            self.resolver.get_logs())

        logger.info(f"✓ Excel workbook saved to data/output/AI_Orbit_AI_Tools_Dataset.xlsx")

    # ─── Generic adapters ─────────────────────────────────────────────────────

    async def _run_adapter(self, adapter, json_file: str, csv_file: str):
        try:
            records = await adapter.fetch_and_process()
            JSONStorage.save(json_file, records)
            CSVStorage.save(csv_file, records)
            logger.info(f"Successfully processed {len(records)} records for {json_file}")
        except Exception as e:
            logger.error(f"Adapter failed for {json_file}: {e}")

    async def _run_github_simple(
            self, adapter: GitHubAdapter, topic: str,
            schema: type, entity_type: EntityType,
            json_file: str, csv_file: str):
        try:
            records = await adapter.fetch_and_process_module(topic, schema, entity_type)
            JSONStorage.save(json_file, records)
            CSVStorage.save(csv_file, records)
            logger.info(f"Successfully processed {len(records)} records for {json_file}")
        except Exception as e:
            logger.error(f"GitHub Adapter failed for {topic}: {e}")
