from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import search, providers

app = FastAPI(title="API-only MVP Web Search")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix="/api")
app.include_router(providers.router, prefix="/api")


@app.get("/")
async def root():
    return {"status": "ok"}
