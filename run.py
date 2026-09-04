import argparse
import asyncio
import logging
from ai_orbit.pipeline.orchestrator import PipelineOrchestrator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    parser = argparse.ArgumentParser(description="AI Orbit Data Ingestion Pipeline")
    parser.add_argument("--mode", choices=["demo", "bulk"], default="demo", help="Execution mode")
    parser.add_argument("--module", choices=["all", "tools", "papers", "companies", "news", "agents", "mcp", "devices", "robots", "models", "jobs"], default="all", help="Module to run")
    
    args = parser.parse_args()
    
    modules = [args.module] if args.module != "all" else ["all"]
    
    orchestrator = PipelineOrchestrator()
    await orchestrator.run(mode=args.mode, modules=modules)

if __name__ == "__main__":
    asyncio.run(main())
