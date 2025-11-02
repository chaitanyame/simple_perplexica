<!--
SYNC IMPACT REPORT

Version change: 0.1.0 -> 0.2.0

Modified principles:
- (new) MVP Scope & API-First -> defines minimal required features and excludes media searches from MVP
- (updated) Provider Flexibility & Portability -> adds default LLM: OpenRouter and search pipeline preference
- (existing) Privacy & Data Locality, Verifiable Answers & Citations, Test-First & Observability — reiterated

Added sections:
- MVP Scope & Search Pipeline

Removed sections: none

Templates reviewed:
- .specify/templates/plan-template.md ✅ reviewed (no constitution-specific blockers found)
- .specify/templates/spec-template.md ✅ reviewed (no constitution-specific blockers found)
- .specify/templates/tasks-template.md ✅ reviewed (no constitution-specific blockers found)
- .specify/templates/commands/*.md ⚠ pending (commands directory missing; manual check recommended)

Follow-up TODOs:
- TODO(RATIFICATION_DATE): original adoption date unknown — please supply the project's original ratification date or leave as adopted-on amendment date.
- Verify presence/contents of `.specify/templates/commands` and update any agent-specific references.
-->

# Perplexica Constitution

## Core Principles

### Privacy & Data Locality (MUST)
Perplexica is PRIVACY-FIRST. User data, search history, uploaded files, and derived embeddings MUST be stored locally by default
and never exfiltrated to third-party telemetry systems without explicit opt-in. Configuration that enables remote or cloud
storage MUST be opt-in, documented, and clearly labeled with the expected privacy trade-offs.

Rationale: This project advertises local LLM support and private search. Privacy guarantees are a primary product differentiator
and a legal/ethical obligation for deployments advertising local-only behavior.

### Verifiable Answers & Citations (MUST)
Search results and assistant responses that summarize external content MUST include cited sources or links to the underlying
evidence used. Where structured source metadata is available (title, url, snippet), that metadata MUST be included in API
responses and UI displays. When answers are speculative or synthesized without direct sources, responses MUST indicate so.

Rationale: Users rely on Perplexica for research and decisions; transparent sourcing preserves trust and enables verification.

### Provider Flexibility & Portability (MUST)
Perplexica MUST support a variety of model providers (local LLMs, Ollama, OpenAI, Anthropic/Claude, Groq, etc.) through a
clear provider abstraction. Provider configuration MUST be pluggable, documented, and avoid hard-coding vendor-specific
semantics in core business logic. For general deployments the project SHOULD prefer local or self-hosted providers when
privacy and operational constraints make that feasible. For the MVP the documented default provider is OpenRouter and
deployments MUST be able to override the default via configuration.

Rationale: Portability reduces vendor lock-in and allows Perplexica to run in air-gapped or privacy-sensitive environments.
Softening the preference to a "SHOULD" preserves the project's support for local-first deployments while avoiding a
hard requirement that conflicts with the MVP decision to default to OpenRouter.

### MVP Scope & API-First (MUST)
For the minimal viable product (MVP), Perplexica's required surface is API endpoints only. The application MUST function as a
service that exposes the documented HTTP APIs for search and provider management — UI and additional client-side features are
optional for MVP and treated as separate deliverables.

MVP feature constraints (MUST):
- The MVP MUST focus on web search results (news, sports, current events, etc.).
- Focus modes present in the project (webSearch, academicSearch, writingAssistant, wolframAlphaSearch, youtubeSearch, redditSearch)
	MUST be retained as logical modes; however, for MVP there is NO requirement to implement image or video search features.
- Image and video search functionality is explicitly OUT OF SCOPE for the MVP and MUST be gated behind separate feature flags
	and follow-up plans.

Rationale: Prioritizing API-first and search-only MVP reduces scope and accelerates delivery of the core value proposition.

### Test-First & Quality Gates (MUST)
New features and changes to existing features MUST include tests that cover unit, contract, and integration expectations where
applicable. Pull requests that modify behavior visible to users or external APIs MUST provide tests and pass CI checks before
merging. The project uses a "tests-first" mindset: write failing tests that capture the expected behavior, then implement.

Rationale: The project integrates multiple external systems (search engines, LLMs, providers). Tests prevent regressions and
ensure reproducible behavior across provider configurations.

### Observability, Simplicity & Semantic Versioning (MUST)
Perplexica MUST emit structured logs for key operations (search requests, provider calls, errors) and preserve minimal
observability to diagnose failures. The codebase SHOULD default to simple, well-documented behavior; complexity requires
explicit justification and an associated maintenance plan. Public APIs and any deployed binaries MUST follow semantic
versioning (MAJOR.MINOR.PATCH) and document breaking changes in release notes.

Search pipeline defaults (MUST):
- The search pipeline MUST attempt to use SearxNG as the primary search engine for web search queries.
- If SearxNG calls fail or return no usable results, the system MUST attempt a fallback to SerperDev (or a configured
	alternative) as a secondary provider.

LLM provider defaults (MUST):
- For LLM endpoints used in generation/synthesis or assistant-style responses, the default external provider MUST be OpenRouter.
- The provider abstraction MUST still allow other providers to be configured, but OpenRouter MUST be the documented default for
	MVP deployments.

Rationale: Observability reduces time-to-diagnose. Simplicity keeps the project maintainable. Semver makes upgrades predictable for
deployers.

## Security & Compliance

Security and secrets handling MUST follow best practices: secrets stored in environment variables or encrypted stores, not in
repository source. Dependencies MUST be periodically scanned for vulnerabilities and updated in a timely fashion. Where the
project integrates third-party services (e.g., WolframAlpha, SearxNG), configuration defaults MUST err on the side of least
privilege and explicit opt-in for external network calls.

Compliance notes: This constitution does not prescribe jurisdictional legal compliance (e.g., GDPR). Deployers are responsible for
ensuring legal compliance for their environment; the project will provide guidance and configuration knobs to assist compliance
efforts where feasible.

## Development Workflow

Code contributions SHOULD follow these minimum quality gates:
- Pull Requests: require at least one approving review from a maintainer other than the author.
- Tests: CI MUST run unit and integration tests for changed code paths; PRs that affect public APIs or provider adapters MUST
	include contract tests.
- Linting & Formatting: PRs MUST pass lint and formatting checks.
- Releases: every release MUST include a changelog entry that documents user-visible changes and any migration steps.

Backwards compatibility: When a change is backwards-incompatible for public APIs, follow the Versioning rules below and document
migration steps in the changelog.

## Governance

Amendments
- Propose changes via a Pull Request that includes: (a) proposed text, (b) rationale, (c) affected files and migration notes,
	and (d) suggested version bump (MAJOR, MINOR, PATCH) with justification.
- Approval: A constitution amendment requires approval by two maintainers (or, if fewer than two maintainers exist, unanimous
	approval of the active maintainers listed in `CONTRIBUTING.md`).
- Implementation: Amendments that change behavior MUST include a migration plan and tests demonstrating the new/changed
	behavior.

Versioning policy
- MAJOR: Backwards-incompatible governance or principle removals/redefinitions, or API-breaking changes that require
	consumers to modify their code.
- MINOR: New principle/section added or material expansion of guidance that influences how features should be implemented.
- PATCH: Typo fixes, clarifications, or non-semantic wording improvements.

Compliance review
- Major/minor amendments SHOULD trigger a compliance review and a short migration guide. For security-related amendments,
	provide an implementation timeline and, if relevant, CVE disclosures for any dependency changes.

**Version**: 0.2.0 | **Ratified**: TODO(RATIFICATION_DATE): original adoption date unknown | **Last Amended**: 2025-11-01

