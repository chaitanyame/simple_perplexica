# Tasks: API-only MVP Web Search (Feature 001-api-mvp-web-search)

This is a strict, phased checklist to deliver the API-only MVP web search per spec and plan. Keep outputs text-only; include citations; prefer SearxNG with fallback to SerperDev; OpenRouter is the default LLM provider. Each task lists concrete artifacts/paths and acceptance criteria. Tasks within a phase may run in parallel unless dependencies are noted.

References
- Spec: ./spec.md
- Plan: ./plan.md (Constitution gates PASS)
- Data model: ./data-model.md
- Contracts: ./contracts/openapi.yaml
- Research: ./research.md

Definition of Done (overall)
- All P1–P3 user stories pass their independent tests
- contracts/openapi.yaml is accurate to implementation
- Docker Compose runs: searxng, api-mvp (port 3001), vetuku (unchanged UI), with .env configured
- No image/video payloads returned by MVP endpoints
- Observability: structured logs with request IDs; secrets from environment

---

## Phase 0 – Prereqs & Alignment (sequential)

- [ ] Verify Constitution alignment in code and docs
  - Artifacts: .specify/memory/constitution.md
  - Accept: Constitution includes MVP scope, SearxNG→SerperDev defaults, OpenRouter default, and API-only guarantee.
- [ ] Ensure feature branch exists and is current
  - Action: git checkout -b 001-api-mvp-web-search (or ensure branch up to date)
  - Accept: Branch present; no uncommitted conflicts.
- [ ] Confirm Docker Compose services and env template
  - Artifacts: docker-compose.yaml; .env.example
  - Accept: Services: searxng (8080), api-mvp (3001), vetuku (3000) present; .env.example includes OPENROUTER_API_KEY, OPENROUTER_MODEL, SEARXNG_URL, SERPERDEV_API_KEY.

Dependencies: none

---

## Phase 1 – Foundational scaffolding (can parallelize)

- [ ] Service structure and configuration wiring
  - Paths: services/api-mvp/app/__init__.py, services/api-mvp/app/main.py, services/api-mvp/app/core/config.py (or inline), services/api-mvp/requirements.txt, services/api-mvp/Dockerfile
  - Accept: FastAPI app boots locally with a health endpoint; config reads env vars with sane defaults.
- [ ] Pydantic data models
  - Paths: services/api-mvp/app/models.py
  - Accept: SearchRequest, SearchResponse, Source, ProvidersResponse align with ./data-model.md; invalid focusMode/query validation errors.
- [ ] HTTP clients for providers
  - Paths: services/api-mvp/app/search_clients/searxng.py, services/api-mvp/app/search_clients/serperdev.py, services/api-mvp/app/providers/openrouter.py
  - Accept: Each client has timeout, error handling, and returns normalized sources or text; unit tests cover happy/timeout/error.
- [ ] API routers and wiring
  - Paths: services/api-mvp/app/routers/search.py, services/api-mvp/app/routers/providers.py; register in main.py
  - Accept: Endpoints registered at /api/search and /api/providers; OpenAPI auto-docs render schemas.

Dependencies: Phase 0

---

## Phase P1 – User Story 1: Web search via API with citations (highest priority)

- [ ] Implement SearxNG → SerperDev fallback pipeline
  - Paths: services/api-mvp/app/routers/search.py; search_clients/*
  - Accept: If SearxNG returns usable results, they are used; on failure/empty, SerperDev is used; both unavailable → 502 with helpful message.
- [ ] Synthesis via OpenRouter with citations
  - Paths: services/api-mvp/app/providers/openrouter.py; services/api-mvp/app/routers/search.py
  - Accept: Non-streaming response includes message and sources[{title,url,pageContent?}]; message references sources.
- [ ] Streaming (newline-delimited JSON events)
  - Paths: services/api-mvp/app/routers/search.py
  - Accept: When stream=true, server emits events: init, sources, response (chunks), done; connection close safe.
- [ ] Contract tests for /api/search
  - Paths: services/api-mvp/tests/contract/test_search_contract.py; specs/001-api-mvp-web-search/contracts/openapi.yaml
  - Accept: Schema compatibility checked (response shape and error codes 400/500+ mapped as needed).
- [ ] Integration test happy-path (with local SearxNG)
  - Paths: services/api-mvp/tests/integration/test_search_searxng.py
  - Accept: With searxng up from compose, a real query returns >=1 citation and a message.
- [ ] Edge-case tests
  - Paths: services/api-mvp/tests/unit/test_validation.py; services/api-mvp/tests/integration/test_fallback.py
  - Accept: Empty query → 422; invalid focusMode → 422; both providers down → 502.

Dependencies: Phase 1

---

## Phase P2 – User Story 2: Focus modes (text-only behavior)

- [ ] Map focusMode to search/prompt adjustments
  - Paths: services/api-mvp/app/routers/search.py; optional: services/api-mvp/app/core/prompting.py
  - Accept: Modes (webSearch, academicSearch, writingAssistant, wolframAlphaSearch, youtubeSearch, redditSearch) influence retrieval/prompt; still text-only.
- [ ] Tests for each mode
  - Paths: services/api-mvp/tests/unit/test_focus_modes.py
  - Accept: Each mode yields textual answer; no image/video payloads; includes citations.

Dependencies: P1 core endpoint

---

## Phase P3 – User Story 3: Providers discovery endpoint

- [ ] Implement /api/providers
  - Paths: services/api-mvp/app/routers/providers.py; services/api-mvp/app/providers/openrouter.py
  - Accept: Returns providers array; OpenRouter listed as default with chatModels and embeddingModels; handles missing creds gracefully.
- [ ] Tests for providers endpoint
  - Paths: services/api-mvp/tests/unit/test_providers.py
  - Accept: 200 with at least OpenRouter present when configured; 200 with empty list when not configured (with warning/log).

Dependencies: Phase 1

---

## Phase 4 – Polish, Ops, and DX

- [ ] Observability and request IDs
  - Paths: services/api-mvp/app/main.py; services/api-mvp/app/core/logging.py (optional)
  - Accept: Logs include request_id; errors include correlation id; no PII logged by default.
- [ ] Config validation and helpful errors
  - Paths: services/api-mvp/app/core/config.py
  - Accept: On startup, missing critical envs produce clear warnings; runtime errors map to 5xx with user-safe messages.
- [ ] Security and CORS
  - Paths: services/api-mvp/app/main.py
  - Accept: CORS allows configured origins; secrets only via env; no secrets in logs.
- [ ] Docs and Quickstart
  - Paths: specs/001-api-mvp-web-search/quickstart.md; services/api-mvp/README.md
  - Accept: Quickstart instructions verified against local run on Windows (pwsh) and Linux shells.
- [ ] Docker Compose happy path
  - Paths: docker-compose.yaml; .env
  - Accept: docker compose up brings up searxng and api-mvp; GET /api/providers and POST /api/search work.
- [ ] Lint and test wiring
  - Paths: services/api-mvp/pyproject.toml or requirements + ruff config; services/api-mvp/tests/
  - Accept: pytest passes; ruff check passes; minimal coverage on critical paths.

Dependencies: P1–P3

---

## Non-goals (explicitly out of scope for MVP)

- Image or video retrieval/streaming
- Authentication/authorization and rate-limiting
- Persistent storage of chats or analytics

---

## Risk Register (selected)

- Upstream availability: SearxNG/SerperDev outages → Mitigate with timeouts, retries, fallbacks
- Model drift/limits on OpenRouter → Make model configurable; provide graceful degradation
- Streaming disconnects → Ensure done/error signals and cleanup

---

## Execution Notes

- Parallelization guidance: Within each phase, tests/docs can be parallelized with implementation once interfaces stabilize.
- Windows (pwsh) compatibility: ensure docs include pwsh-flavored commands; avoid bash-only snippets.
- Timeouts: Prefer 3–5s HTTP client timeouts; cap response sizes.

---

## Checkpoints (suggested)

- [ ] Checkpoint 1: P1 endpoint non-streaming complete and tested
- [ ] Checkpoint 2: Fallback and streaming complete
- [ ] Checkpoint 3: Focus modes honored (text-only)
- [ ] Checkpoint 4: Providers endpoint complete
- [ ] Checkpoint 5: Compose run verified; docs updated; linters/tests green

- End of tasks.md -
