from fastapi import APIRouter
from ..models import ProvidersResponse, Provider, ProviderModel
import uuid
import os

router = APIRouter()


@router.get("/providers", response_model=ProvidersResponse)
async def providers():
    # Reflect env-configured models so the UI sees real values
    chat_key = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1:free")
    emb_key = os.getenv(
        "OPENROUTER_EMBEDDING_MODEL",
        os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    )
    chat_name = chat_key
    emb_name = emb_key
    openrouter_provider = Provider(
        id=str(uuid.uuid4()),
        name="OpenRouter",
        chatModels=[ProviderModel(name=chat_name, key=chat_key)],
        embeddingModels=[ProviderModel(name=emb_name, key=emb_key)],
    )
    return ProvidersResponse(providers=[openrouter_provider])
