# Data Model: API-only MVP Web Search

Created: 2025-11-01

## Entities

### SearchRequest
- query: string (required, min length > 1)
- focusMode: enum { webSearch, academicSearch, writingAssistant, wolframAlphaSearch, youtubeSearch, redditSearch }
- optimizationMode: enum { speed, balanced } (optional)
- history: array<[role, text]> (optional)
- systemInstructions: string (optional)
- stream: boolean (optional)

### SearchResponse (non-stream)
- message: string
- sources: array<Source>

### Source
- title: string
- url: string
- pageContent: string (optional)

### ProvidersResponse
- providers: array<Provider>

### Provider
- id: string (UUID or stable ID)
- name: string
- chatModels: array<Model>
- embeddingModels: array<Model>

### Model
- name: string
- key: string

## Validation Rules
- query is required and must be non-empty
- focusMode must be one of allowed values
- if stream=true, server streams SSE with types: init, sources, response, done
