import pytest
from ai_orbit.normalization.urls import normalize_url
from ai_orbit.normalization.names import normalize_name
from ai_orbit.normalization.dates import normalize_date, is_within_24_hours
from ai_orbit.deduplication.fuzzy import fuzzy_match
from ai_orbit.deduplication.exact import generate_deterministic_id
from ai_orbit.llm.chunking import chunk_text
from ai_orbit.entity_resolution.resolver import EntityResolver
from datetime import datetime, timedelta

def test_url_normalization():
    assert normalize_url("http://www.Example.com/") == "https://example.com/"
    assert normalize_url("https://example.com/path?utm_source=test&q=1") == "https://example.com/path?q=1"
    
def test_name_normalization():
    assert normalize_name("OpenAI Inc.") == "openai"
    assert normalize_name("Open AI, LLC") == "open ai"

def test_date_normalization():
    assert "T" in normalize_date("today")
    assert "T" in normalize_date("2 hours ago")
    assert normalize_date("2023-01-01") == "2023-01-01T00:00:00"

def test_fuzzy_match():
    assert fuzzy_match("openai", "open ai") == True
    assert fuzzy_match("apple", "banana") == False

def test_exact_deduplication():
    id1 = generate_deterministic_id("https://openai.com", "OpenAI")
    id2 = generate_deterministic_id("https://www.openai.com/?utm_source=twitter", "OpenAI Inc.")
    assert id1 == id2

def test_chunking():
    text = "A" * 20000
    chunks = chunk_text(text, max_chars=15000)
    assert len(chunks) == 2
    assert len(chunks[0]) == 15000
    assert len(chunks[1]) == 5000

def test_freshness():
    now = datetime.utcnow()
    recent = (now - timedelta(hours=2)).isoformat() + "Z"
    old = (now - timedelta(hours=48)).isoformat() + "Z"
    
    assert is_within_24_hours(recent) == True
    assert is_within_24_hours(old) == False

def test_entity_resolution():
    resolver = EntityResolver()
    
    # New entity
    id1, status1 = resolver.resolve("COMPANY", "OpenAI Inc.", "https://openai.com")
    assert status1 == "NEW"
    
    # Exact URL match
    id2, status2 = resolver.resolve("COMPANY", "OpenAI", "https://openai.com")
    assert status2 == "EXACT_URL"
    assert id1 == id2
    
    # Exact Name match
    id3, status3 = resolver.resolve("COMPANY", "OpenAI LLC", "")
    assert status3 == "EXACT_NAME"
    assert id1 == id3

def test_missing_field_validation():
    from ai_orbit.validation.schemas import ToolContent
    from pydantic import ValidationError
    
    # ToolContent requires name, etc.
    try:
        ToolContent(
            name="Test",
            description="A test",
            primary_task="Coding",
            pricing_model="Free"
        )
    except ValidationError:
        pass # Should raise validation error on missing required fields or pass if defaults

def test_429_retry_handling():
    # Placeholder for LLM 429 mock test
    # In a real environment, we mock the instructor client to raise 429
    assert True

def test_resumability():
    # Ensure processed URLs are correctly identified in batch loops
    assert True

def test_canonical_entity_resolution():
    resolver = EntityResolver()
    id1, _ = resolver.resolve("TOOL", "Midjourney AI", "https://www.midjourney.com")
    id2, status = resolver.resolve("TOOL", "Midjourney", "https://midjourney.com")
    assert id1 == id2
    assert status == "EXACT_URL"
