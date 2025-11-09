from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class ModelRef(BaseModel):
    providerId: str
    key: str


class OptimizationMode(str, Enum):
    speed = "speed"
    balanced = "balanced"
    quality = "quality"


class FocusMode(str, Enum):
    webSearch = "webSearch"
    academicSearch = "academicSearch"
    writingAssistant = "writingAssistant"
    wolframAlphaSearch = "wolframAlphaSearch"
    youtubeSearch = "youtubeSearch"
    redditSearch = "redditSearch"


class SearchStrategy(str, Enum):
    """Strategy for executing search queries"""
    single = "single"  # Single optimized query
    multi = "multi"    # Multiple decomposed queries


class SearchRequest(BaseModel):
    chatModel: Optional[ModelRef] = None
    embeddingModel: Optional[ModelRef] = None
    optimizationMode: OptimizationMode = Field(default=OptimizationMode.balanced)
    focusMode: FocusMode
    query: str
    history: Optional[List[List[str]]] = None
    systemInstructions: Optional[str] = None
    stream: Optional[bool] = False

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v or not v.strip() or len(v.strip()) < 2:
            raise ValueError("query must be at least 2 characters")
        return v


class Source(BaseModel):
    title: str
    url: str
    pageContent: Optional[str] = None


class DecompositionInfo(BaseModel):
    """Information about query decomposition process"""
    strategy: SearchStrategy  # single or multi
    optimized_queries: List[str]  # Queries that were actually executed
    query_count: int = Field(default=1)  # Number of decomposed queries


class SearchResponse(BaseModel):
    message: str
    sources: List[Source]
    decomposition: Optional[DecompositionInfo] = None  # Optional decomposition metadata


class ProviderModel(BaseModel):
    name: str
    key: str


class Provider(BaseModel):
    id: str
    name: str
    chatModels: List[ProviderModel]
    embeddingModels: List[ProviderModel]


class ProvidersResponse(BaseModel):
    providers: List[Provider]


class DecisionOutput(BaseModel):
    """Output from LLM decision on whether to search and query optimization"""
    need_search: bool
    optimized_queries: List[str]  # Can be single or multiple queries
    search_strategy: SearchStrategy = Field(default=SearchStrategy.single)
    links: List[str] = Field(default_factory=list)  # URLs mentioned in query
