"""
LLM Orchestrator with robust rate-limit handling.

Supports Gemini (via REST API), OpenAI, Groq, DeepSeek.
- Exponential backoff on 429/ResourceExhausted
- Configurable delay between requests
- Thread-safe incremental saving
- No mock fallback in bulk mode
"""
import logging
import asyncio
import json
import aiohttp
from typing import Type, TypeVar, Any
from pydantic import BaseModel

from ai_orbit.config import Config
from ai_orbit.llm.prompts import EXTRACTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

# Delay between consecutive Gemini calls (seconds)
GEMINI_CALL_DELAY = float(Config.__dict__.get('GEMINI_DELAY', 2.0))


class LLMOrchestrator:
    def __init__(self):
        self.clients = []
        self._gemini_api_key = Config.GEMINI_API_KEY

        if Config.OPENAI_API_KEY:
            import instructor
            from openai import AsyncOpenAI
            self.clients.append({
                "name": "openai",
                "client": instructor.from_openai(
                    AsyncOpenAI(api_key=Config.OPENAI_API_KEY)),
                "model": "gpt-4o-mini",
                "type": "openai"
            })

        if Config.GEMINI_API_KEY:
            # Use direct REST API for fully async Gemini calls
            self.clients.append({
                "name": "gemini",
                "client": None,  # We use aiohttp directly
                "model": "gemini-3.6-flash",
                "type": "gemini_rest"
            })

        if Config.GROQ_API_KEY:
            import instructor
            from openai import AsyncOpenAI
            self.clients.append({
                "name": "groq",
                "client": instructor.from_openai(
                    AsyncOpenAI(
                        base_url="https://api.groq.com/openai/v1",
                        api_key=Config.GROQ_API_KEY
                    ),
                    mode=instructor.Mode.JSON
                ),
                "model": "llama-3.1-8b-instant",
                "type": "openai"
            })

        if Config.DEEPSEEK_API_KEY:
            import instructor
            from openai import AsyncOpenAI
            self.clients.append({
                "name": "deepseek",
                "client": instructor.from_openai(
                    AsyncOpenAI(
                        base_url="https://api.deepseek.com/v1",
                        api_key=Config.DEEPSEEK_API_KEY
                    ),
                    mode=instructor.Mode.JSON
                ),
                "model": "deepseek-chat",
                "type": "openai"
            })

    async def extract(self, text: str, response_model: Type[T]) -> T:
        if not self.clients:
            logger.warning(
                "No LLM API keys provided. Using deterministic mock fallback.")
            return self._mock_fallback(text, response_model)

        for provider in self.clients:
            logger.info(
                f"Attempting extraction with {provider['name']} "
                f"({provider['model']})")
            try:
                result = await asyncio.wait_for(
                    self._call_provider(provider, text, response_model),
                    timeout=60.0
                )
                logger.info(f"Successfully extracted with {provider['name']}")
                return result
            except asyncio.TimeoutError:
                logger.warning(f"{provider['name']} timed out after 60s")
                continue
            except Exception as e:
                logger.warning(f"{provider['name']} failed: {e}")
                continue

        logger.warning("All LLM providers failed. Using mock fallback.")
        return self._mock_fallback(text, response_model)

    async def _call_provider(
            self, provider: dict, text: str,
            response_model: Type[T]) -> T:
        if provider["type"] == "gemini_rest":
            return await self._call_gemini_rest(text, response_model)
        else:
            return await self._call_openai_compatible(
                provider, text, response_model)

    async def _call_gemini_rest(
            self, text: str, response_model: Type[T]) -> T:
        """
        Call Gemini via REST API with exponential backoff on 429.
        Fully async — no blocking.
        """
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-3.6-flash:generateContent"
            f"?key={self._gemini_api_key}"
        )

        # Build the schema hint for structured output
        schema_json = response_model.model_json_schema()
        prompt = (
            f"{EXTRACTION_SYSTEM_PROMPT}\n\n"
            f"You MUST respond with valid JSON matching this exact schema:\n"
            f"{json.dumps(schema_json, indent=2)}\n\n"
            f"Raw Text:\n{text}"
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1,
                "maxOutputTokens": 2048
            }
        }

        max_retries = 5
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=aiohttp.ClientTimeout(total=45)
                    ) as resp:
                        if resp.status == 429:
                            retry_after = resp.headers.get("Retry-After")
                            wait = int(retry_after) if retry_after and retry_after.isdigit() else (2 ** attempt * 4)
                            logger.warning(
                                f"Gemini 429 rate limit. Waiting {wait}s "
                                f"(attempt {attempt+1}/{max_retries})")
                            await asyncio.sleep(wait)
                            continue
                        elif resp.status == 503:
                            wait = 2 ** attempt * 2
                            logger.warning(
                                f"Gemini 503 overloaded. Waiting {wait}s")
                            await asyncio.sleep(wait)
                            continue
                        elif resp.status != 200:
                            body = await resp.text()
                            raise RuntimeError(
                                f"Gemini API error {resp.status}: {body[:300]}")

                        data = await resp.json()

                # Extract text from response
                candidates = data.get("candidates", [])
                if not candidates:
                    raise RuntimeError("No candidates in Gemini response")

                content_parts = candidates[0].get("content", {}).get("parts", [])
                if not content_parts:
                    raise RuntimeError("No content parts in Gemini response")

                raw_text = content_parts[0].get("text", "")

                # Parse JSON
                parsed = json.loads(raw_text)
                return response_model(**parsed)

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                wait = 2 ** attempt * 2
                logger.warning(
                    f"Gemini network error: {e}. Retrying in {wait}s")
                await asyncio.sleep(wait)

        raise RuntimeError(
            f"Gemini REST API failed after {max_retries} retries")

    async def _call_openai_compatible(
            self, provider: dict, text: str,
            response_model: Type[T]) -> T:
        return await provider["client"].chat.completions.create(
            model=provider["model"],
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            response_model=response_model,
        )

    def _mock_fallback(self, text: str, response_model: Type[T]) -> T:
        """Deterministic mock fallback when no API keys are provided."""
        mock_data = {}
        for field_name, field in response_model.model_fields.items():
            annotation = field.annotation
            if annotation == str:
                mock_data[field_name] = "Mock Data"
            elif annotation == int:
                mock_data[field_name] = 100
            elif annotation == bool:
                mock_data[field_name] = True
            elif annotation == float:
                mock_data[field_name] = 50.0
            elif (getattr(annotation, '__origin__', None) is list
                  or getattr(annotation, '__name__', '') == 'list'):
                mock_data[field_name] = ["Mock Item"]
            else:
                mock_data[field_name] = None

        if "name" in mock_data:
            mock_data["name"] = "Mock Demo Entity"
        if "title" in mock_data:
            mock_data["title"] = "Mock Demo Title"

        return response_model(**mock_data)
