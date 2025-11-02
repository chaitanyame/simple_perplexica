# Implementation Plan: API-only MVP Web Search

**Branch**: `001-api-mvp-web-search` | **Date**: 2025-11-01 | **Spec**: ../spec.md
**Input**: Feature specification from `/specs/001-api-mvp-web-search/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Deliver a minimal, API-only backend that performs web search and returns textual answers with citations. Keep all focus modes
as logical modes (text-only for MVP), use SearxNG as the primary source with SerperDev as fallback, and use OpenRouter as the
default LLM provider for answer synthesis. Exclude image/video retrieval in MVP.

## Technical Context

**Language/Version**: Python 3.11 (assumption for MVP)  
**Primary Dependencies**: [NEEDS CLARIFICATION: FastAPI vs Flask]; OpenRouter client; HTTP clients for SearxNG + SerperDev  
**Storage**: [NEEDS CLARIFICATION] MVP could be stateless; optional SQLite for request logs/metrics  
**Testing**: pytest (unit, contract, integration)  
**Target Platform**: Docker container (Linux)  
**Project Type**: Single service API  
**Performance Goals**: 95% of valid searches return in ≤ 3s; streaming starts in ≤ 1s  
**Constraints**: Network-bound; graceful fallback if primary search is down  
**Scale/Scope**: MVP single service; single-tenant deployment

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Derived gates from constitution:
- Privacy & Data Locality: No telemetry by default; config opt-in for any remote behavior → PASS (MVP config-based)
- Verifiable Answers & Citations: Responses include sources → PASS (in spec)
- Provider Flexibility & Portability: OpenRouter default, configurable providers → PASS
- MVP Scope & API-First: API-only; no image/video in MVP → PASS
- Observability, Simplicity & Semver: Structured logs; simple service; semver for public APIs → PASS
- Search Pipeline Defaults: SearxNG primary → SerperDev fallback → PASS
- Security & Compliance: Secrets via env; least-privilege configs → PASS

Result: PASS (no blockers). Re-validate after design contracts.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
services/api-mvp/
├── app/
│   ├── routers/            # /api/search, /api/providers
│   ├── providers/          # OpenRouter client abstraction
│   ├── search_clients/     # searxng.py, serperdev.py
│   ├── models/             # request/response pydantic models
│   ├── core/               # config, logging
│   └── __init__.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── contract/
├── Dockerfile
├── pyproject.toml or requirements.txt
└── README.md
```

**Structure Decision**: Create a new isolated Python API service under `services/api-mvp/` to avoid touching existing
Next.js code. Tests organized by unit/integration/contract. Deployment via Docker.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
