from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Any, Dict
from datetime import datetime
from enum import Enum

class PricingModel(str, Enum):
    FREE = "FREE"
    FREEMIUM = "FREEMIUM"
    PAID = "PAID"
    ENTERPRISE = "ENTERPRISE"
    UNKNOWN = "UNKNOWN"

class EntityType(str, Enum):
    TOOL = "TOOL"
    COMPANY = "COMPANY"
    AGENT = "AGENT"
    MCP = "MCP"
    MODEL = "MODEL"
    ROBOT = "ROBOT"
    DEVICE = "DEVICE"
    NEWS = "NEWS"
    RESEARCH_PAPER = "RESEARCH_PAPER"
    PRODUCT = "PRODUCT"
    JOB = "JOB"

class SourceProvenance(BaseModel):
    name: str = Field(..., description="Name of the discovery source, e.g., TAAFT, Creati.ai, Crunchbase")
    url: str = Field(..., description="URL where the entity was discovered")

class VerificationMetadata(BaseModel):
    verified: bool = Field(default=False, description="Whether the record was verified against official source")
    officialUrl: Optional[str] = Field(default=None, description="The official website of the entity")
    lastVerified: Optional[str] = Field(default=None, description="ISO-8601 timestamp of last verification")

class QualityMetrics(BaseModel):
    score: float = Field(default=0, description="Overall quality score (0-100)")
    
class CanonicalEntity(BaseModel):
    id: str = Field(..., description="Stable, deterministic ID (e.g., domain or hash)")
    schemaVersion: str = Field(default="1.0")
    recordType: EntityType
    source: SourceProvenance
    verification: VerificationMetadata = Field(default_factory=VerificationMetadata)
    quality: QualityMetrics = Field(default_factory=QualityMetrics)
    collectedAt: str = Field(..., description="ISO-8601 timestamp when collected")

# Specific Entity Content Schemas

class ToolContent(BaseModel):
    name: str
    company_or_developer: Optional[str] = None
    description: str
    primary_task: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    pricing_model: Optional[PricingModel] = None
    is_open_source: Optional[bool] = None
    launch_date: Optional[str] = None
    status: Optional[str] = None
    official_website: Optional[str] = None
    inputs: Optional[str] = None
    outputs: Optional[str] = None
    supported_platforms: Optional[str] = None
    has_api: Optional[bool] = None
    logo_url: Optional[str] = None
    last_verified: Optional[str] = None

class CompanyContent(BaseModel):
    name: str
    description: str
    founded_year: Optional[int] = None
    is_ai_native: bool = Field(default=False)
    ai_category: Optional[str] = None
    funding_raised: Optional[str] = None
    valuation: Optional[str] = None

class AgentContent(BaseModel):
    name: str
    description: str
    category: Optional[str] = None
    company_or_creator: Optional[str] = None
    pricing_model: Optional[PricingModel] = None
    is_open_source: Optional[bool] = None
    supported_models: List[str] = Field(default_factory=list)
    primary_use_case: Optional[str] = None

class MCPContent(BaseModel):
    name: str
    description: str
    creator: Optional[str] = None
    category: Optional[str] = None
    is_server: bool = Field(default=True)
    github_url: Optional[str] = None
    github_stars: Optional[int] = None

class ModelContent(BaseModel):
    name: str
    provider: str
    model_family: Optional[str] = None
    modalities: List[str] = Field(default_factory=list)
    context_window: Optional[int] = None
    is_open_source: Optional[bool] = None

class RobotContent(BaseModel):
    name: str
    manufacturer: str
    description: str
    maturity_status: Optional[str] = None

class DeviceContent(BaseModel):
    name: str
    manufacturer: str
    description: str
    device_type: Optional[str] = None

class NewsContent(BaseModel):
    title: str
    summary: str
    publisher: str
    publication_date: str

class PaperContent(BaseModel):
    title: str
    authors: List[str]
    abstract: str
    publication_date: str
    github_url: Optional[str] = None
    github_stars: Optional[int] = None

class ProductContent(BaseModel):
    name: str
    company: str
    description: str
    pricing_model: Optional[PricingModel] = None

class JobContent(BaseModel):
    title: str
    company: str
    role_family: Optional[str] = None
    is_remote: Optional[bool] = None
    posted_date: str

class FullRecord(CanonicalEntity):
    content: Any
