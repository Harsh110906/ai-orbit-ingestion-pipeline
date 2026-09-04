import aiohttp
import asyncio
import logging
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any

from ai_orbit.crawling.retry import async_retry, RateLimitError
from ai_orbit.config import Config

logger = logging.getLogger(__name__)

class AsyncHTTPClient:
    def __init__(self, max_concurrency: int = Config.MAX_CONCURRENCY):
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            "User-Agent": "AIOrbit-Ingestion-Pipeline/1.0 (Research & Discovery)"
        }

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT)
        self.session = aiohttp.ClientSession(timeout=timeout, headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    @async_retry(max_retries=3)
    async def fetch_html(self, url: str) -> Optional[str]:
        async with self.semaphore:
            if not self.session:
                raise RuntimeError("Session not initialized. Use async with context manager.")
            
            logger.info(f"Fetching: {url}")
            async with self.session.get(url) as response:
                if response.status == 429:
                    retry_after = response.headers.get("Retry-After")
                    retry_after = int(retry_after) if retry_after and retry_after.isdigit() else None
                    raise RateLimitError(retry_after)
                
                response.raise_for_status()
                return await response.text()
                
    async def extract_text(self, url: str) -> Optional[str]:
        try:
            html = await self.fetch_html(url)
            if not html:
                return None
            soup = BeautifulSoup(html, 'html.parser')
            # Remove scripts and styles
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            text = soup.get_text(separator=' ', strip=True)
            return text
        except Exception as e:
            logger.error(f"Failed to extract text from {url}: {e}")
            return None
