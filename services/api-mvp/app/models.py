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


class SearchResponse(BaseModel):
    message: str
    sources: List[Source]


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
