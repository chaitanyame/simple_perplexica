# Research: API-only MVP Web Search

Created: 2025-11-01

## Unknowns and Decisions

1) Web framework selection (FastAPI vs Flask)
- Decision: FastAPI (assumption for MVP)
- Rationale: Built-in Pydantic models, typing-first, async support, good for streaming.
- Alternatives: Flask + flask-sse; Starlette directly. FastAPI offers quicker path for typed contracts.

2) Storage choice (stateful logs?)
- Decision: Start stateless (no DB). Add SQLite via Drizzle/ORM only if needed later for persistence.
- Rationale: MVP scope minimizes complexity.
- Alternatives: SQLite via SQLAlchemy/Drizzle-ORM; external DB.

3) Providers modeling (OpenRouter default, configurable others)
- Decision: Config-driven provider registry with OpenRouter default; env-based configuration.
- Rationale: Matches constitution (OpenRouter default, configurable providers).
- Alternatives: Hard-coded provider; separate services per provider.

## Patterns and Best Practices

- Search pipeline: try SearxNG then fallback to SerperDev; provide diagnostics when both fail.
- Streaming: use server-sent events or chunked JSON with proper types (init, sources, response, done).
- Observability: structured logging with correlation IDs per request; no telemetry without explicit opt-in.
- Security: secrets via environment variables; validate incoming parameters and sanitize outputs.

## Final Decisions

- Framework: FastAPI
- Streaming: SSE-style newline-delimited JSON
- Config: environment variables for provider URLs and keys; defaults for OpenRouter, SearxNG
- No image/video features in MVP; text-only responses with citations
