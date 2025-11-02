# Feature Specification: API-only MVP Web Search

**Feature Branch**: `001-api-mvp-web-search`  
**Created**: 2025-11-01  
**Status**: Draft  
**Input**: User description: "we need to update this existing app to incorporate the below changes and remove the functionality not needed. we need minimal functions of this app. this app is only needed for api endponts. keep all the focus mode. min mvp for this app is to search the web and get the content like current news, sports etc. no need of image, video searches use the openrouter for the LLM end points. use the search mechanism like searxng first  then if there are failures , then  fallback to serperdev dev."

## User Scenarios & Testing (mandatory)

### User Story 1 - Perform web search via API (Priority: P1)

An API client sends a search request for current events (e.g., news, sports) with a focus mode and receives a textual answer
with cited sources.

**Why this priority**: Delivers the core value of the MVP: web search answers with verifiable citations.

**Independent Test**: Call the search endpoint with a query (e.g., "Latest Premier League scores") and verify response text
and source citations are returned.

**Acceptance Scenarios**:
1. Given a valid query and focusMode, When the client calls the search API, Then the response includes an answer message and a
   list of sources with titles and URLs.
2. Given SearxNG is available, When the client calls the search API, Then results are derived from SearxNG results.
3. Given SearxNG fails, When the client calls the search API, Then the system transparently falls back to SerperDev and returns
   results if available.

---

### User Story 2 - Select focus modes (Priority: P2)

An API client can set focus modes (webSearch, academicSearch, writingAssistant, wolframAlphaSearch, youtubeSearch,
redditSearch) to influence how the system retrieves and synthesizes results; image and video retrieval are not included in MVP.

**Why this priority**: Preserves mode-based behavior while constraining scope to text-based answers for MVP.

**Independent Test**: Call search with different focusMode values and verify response content adheres to the focus intent and
returns textual answers with citations.

**Acceptance Scenarios**:
1. Given focusMode=webSearch, When queried, Then return a concise answer summarizing recent web content with citations.
2. Given focusMode=youtubeSearch, When queried, Then return textual summaries/citations (no video/image payloads in MVP).
3. Given focusMode=wolframAlphaSearch, When queried, Then return textual outputs referencing computed results where available.

---

### User Story 3 - List available providers and models (Priority: P3)

An API client can retrieve the configured model providers and models; OpenRouter is the default provider for LLM endpoints and
others may be configured.

**Why this priority**: Enables clients to discover usable model keys and provider IDs.

**Independent Test**: Call providers endpoint and verify OpenRouter appears as default with available chat/embedding models.

**Acceptance Scenarios**:
1. Given the system is configured, When the client calls the providers API, Then it returns provider IDs and model keys.
2. Given OpenRouter is default, When the client calls providers API, Then OpenRouter provider is present and identified as
   available.

### Edge Cases

- SearxNG and SerperDev both unavailable or return no results → return a clear error with guidance to retry later.
- Query too vague/empty → validation error indicating required fields.
- Invalid focusMode value → validation error listing accepted values.
- Provider rate limits or timeouts → degrade gracefully with partial results or a retry-after indication.
- Streaming requested but connection interrupted → terminate stream with done/error signal.

## Requirements (mandatory)

### Functional Requirements

- FR-001: The system MUST expose a search API endpoint that accepts: query (string), focusMode (one of: webSearch,
  academicSearch, writingAssistant, wolframAlphaSearch, youtubeSearch, redditSearch), optional optimizationMode
  (speed|balanced), optional history, optional systemInstructions, and optional stream flag.
- FR-002: The search pipeline MUST attempt SearxNG first to fetch sources; on failure or no usable results, it MUST fall back
  to SerperDev.
- FR-003: The response for non-streaming requests MUST include: message (string) and sources (array of {title, url, snippet}).
- FR-004: When stream=true, the API MUST stream newline-delimited JSON events of types: init, sources, response (text
  chunks), done.
- FR-005: The system MUST retain all focus modes as query modifiers for text-based output in MVP; image and video retrieval
  are out-of-scope and MUST NOT be returned.
- FR-006: The system MUST provide a providers discovery endpoint that returns configured providers and their available chat and
  embedding model keys; OpenRouter MUST be included as default for LLM endpoints.
- FR-007: All answers derived from external content MUST include citations (title and URL) in the response body.
- FR-008: Validation MUST reject empty queries and invalid focusMode values with clear error messages.
- FR-009: The system SHOULD return helpful diagnostics when neither SearxNG nor SerperDev produce results (e.g., message and
  guidance to retry).

### Key Entities (if data involved)

- SearchRequest: { query: string, focusMode: enum, optimizationMode?: enum, history?: [role,text][], systemInstructions?:
  string, stream?: boolean }
- SearchResponse (non-stream): { message: string, sources: Array<{ title: string, url: string, pageContent?: string }> }
- ProvidersResponse: { providers: Array<{ id: string, name: string, chatModels: Array<{ name: string, key: string }>,
  embeddingModels: Array<{ name: string, key: string }> }> }

## Success Criteria (mandatory)

### Measurable Outcomes

- SC-001: 95% of valid search requests return a textual answer with at least one citation within 3 seconds under normal load.
- SC-002: For upstream SearxNG outages, the system successfully falls back to SerperDev in ≥ 90% of affected requests.
- SC-003: 100% of responses contain citations when they summarize external content.
- SC-004: 0% of MVP responses include image or video payloads; all outputs are textual.
- SC-005: Provider discovery endpoint returns at least one provider (OpenRouter) 100% of the time when configured.

## Assumptions & Dependencies

- Assumption: Authentication/authorization and rate-limiting are out of scope for this MVP and will be added in future
  iterations if required.
- Assumption: OpenRouter is available to the deployment and configured with necessary credentials; other providers remain
  configurable.
- Dependency: At least one of SearxNG or SerperDev is reachable to satisfy most web queries.
