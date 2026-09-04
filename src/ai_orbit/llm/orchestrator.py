import logging
import asyncio
from typing import Type, TypeVar, Any
from pydantic import BaseModel
import instructor
from openai import AsyncOpenAI
import google.generativeai as genai

from ai_orbit.config import Config
from ai_orbit.llm.prompts import EXTRACTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

class LLMOrchestrator:
    def __init__(self):
        self.clients = []
        
        if Config.OPENAI_API_KEY:
            self.clients.append({
                "name": "openai",
                "client": instructor.from_openai(AsyncOpenAI(api_key=Config.OPENAI_API_KEY)),
                "model": "gpt-4o-mini"
            })
            
        if Config.GEMINI_API_KEY:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            self.clients.append({
                "name": "gemini",
                "client": instructor.from_gemini(
                    client=genai.GenerativeModel(
                        model_name="models/gemini-1.5-flash-latest"
                    )
                ),
                "model": "gemini-1.5-flash"
            })
            
        if Config.GROQ_API_KEY:
            self.clients.append({
                "name": "groq",
                "client": instructor.from_openai(
                    AsyncOpenAI(
                        base_url="https://api.groq.com/openai/v1",
                        api_key=Config.GROQ_API_KEY
                    ),
                    mode=instructor.Mode.JSON
                ),
                "model": "llama-3.1-8b-instant"
            })
            
        if Config.DEEPSEEK_API_KEY:
            self.clients.append({
                "name": "deepseek",
                "client": instructor.from_openai(
                    AsyncOpenAI(
                        base_url="https://api.deepseek.com/v1",
                        api_key=Config.DEEPSEEK_API_KEY
                    ),
                    mode=instructor.Mode.JSON
                ),
                "model": "deepseek-chat"
            })
            
    async def extract(self, text: str, response_model: Type[T]) -> T:
        if not self.clients:
            logger.warning("No LLM API keys provided. Using deterministic mock fallback for demo mode.")
            return self._mock_fallback(text, response_model)

        for provider in self.clients:
            logger.info(f"Attempting extraction with {provider['name']} ({provider['model']})")
            try:
                # Add timeout to prevent hanging
                result = await asyncio.wait_for(
                    self._call_provider(provider, text, response_model),
                    timeout=30.0
                )
                logger.info(f"Successfully extracted with {provider['name']}")
                return result
            except Exception as e:
                logger.warning(f"{provider['name']} failed: {e}")
                continue
                
        raise RuntimeError("All LLM providers failed to extract data.")

    async def _call_provider(self, provider: dict, text: str, response_model: Type[T]) -> T:
        if provider["name"] == "gemini":
            # Gemini specific call format via instructor
            return provider["client"].messages.create(
                messages=[
                    {"role": "user", "content": EXTRACTION_SYSTEM_PROMPT + "\n\nRaw Text:\n" + text}
                ],
                response_model=response_model,
            )
        else:
            return await provider["client"].chat.completions.create(
                model=provider["model"],
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ],
                response_model=response_model,
            )

    def _mock_fallback(self, text: str, response_model: Type[T]) -> T:
        # Mock deterministic fallback when no API keys are provided
        mock_data = {}
        for field_name, field in response_model.model_fields.items():
            if field.annotation == str:
                mock_data[field_name] = "Mock Data"
            elif field.annotation == int:
                mock_data[field_name] = 100
            elif field.annotation == bool:
                mock_data[field_name] = True
            elif field.annotation == float:
                mock_data[field_name] = 50.0
            elif getattr(field.annotation, '__origin__', None) is list or getattr(field.annotation, '__name__', '') == 'list':
                mock_data[field_name] = ["Mock Item"]
            else:
                mock_data[field_name] = None
        
        # specific hardcoded values for names if possible
        if "name" in mock_data:
            mock_data["name"] = "Mock Demo Entity"
        if "title" in mock_data:
            mock_data["title"] = "Mock Demo Title"
            
        return response_model(**mock_data)
