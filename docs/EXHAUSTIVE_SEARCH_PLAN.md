# Exhaustive Scheduled Search: Options and Plan

This document proposes concrete options to make the daily scheduled search exhaustive, accurate, and reliable. Pick a tier below and we can phase in.

## Success criteria
- High coverage: all major entities/topics captured per run
- Freshness: captures latest within last N hours/days
- Accuracy: relevant, deduped, balanced across entities/domains
- Reliability: retries, fallbacks, observability, and alerts
- Reproducibility: deterministic configs + versioned prompts/models

---

## Option A — Minimal (1–2 days)
Quick wins without large infra changes.

- Query strategy
  - Keep multi-query decomposition; add per-entity seed queries in config (YAML/JSON), e.g., aws, azure, gcp, plus 3–5 synonyms each.
  - Cap per-subquery results (already added) and enforce domain diversity.
- Providers
  - Use SearxNG primary + SerperDev fallback (already wired). Ensure both API keys set and timeouts tuned.
- URL enrichment
  - Balanced: fetch top 2 URLs; Quality: top 5 URLs; ensure re-aggregation after enrichment (implemented).
- Scheduling
  - Add a simple cron/compose service to call /api/search with predefined topics 3–6× per day; store JSON to disk (bind mount) as an archive.
- Logging/metrics
  - Structured logs with query, subqueries, counts, provider used, latency, failures.
  - Emit basic Prometheus-style counters via FastAPI middleware or log-based dashboards.

Pros: Fast to ship. Cons: May still miss niche sources; ranking depends on heuristics.

---

## Option B — Standard (1–2 weeks)
Better recall, stability, and evaluation.

- Query generation and recall
  - Entity taxonomy: maintain a config of entities/topics (providers, products, services) with aliases. Expand sub-queries per run based on recency (e.g., add "site:blogs.aws.amazon.com" variants).
  - Freshness filter: add time-bounded search operators where possible (e.g., last 7 days) and rank-boost by recency.
  - Multi-engine blend: configure SearxNG with more engines (news, tech blogs, Reddit, YouTube) and weight by signal; keep SerperDev fallback.
- Reranking & quality
  - Use bi-encoder similarity as primary score (already supported). Add re-rank weighting: 60% semantic match + 20% recency + 20% domain authority.
  - Hard caps: max 2–3 results per domain and per-product per run.
- Enrichment
  - Expand URL fetch concurrency; extract canonical URL and do aggressive dedupe by canonical + normalized title.
  - Use readable text extraction with fallbacks (we already have BeautifulSoup fallback) and drop content < 400 chars.
- Storage & history
  - Persist each run in a store (SQLite/Postgres) with run_id, queries, sources, hash of each doc; skip unchanged content next run; highlight deltas.
- Scheduling & retries
  - Use a lightweight scheduler (cron in a sidecar or GitHub Actions) with exponential backoff on provider failures; keep a per-run report artifact.
- Evaluation
  - Define a small gold set (10–20 topics) and nightly compare coverage, unique domains, freshness (<48h), and relevancy score.

Pros: Good coverage and quality with moderate cost. Cons: Some infra work.

---

## Option C — Advanced (3–6 weeks)
Maximize coverage, reduce hallucinations, and add strong observability.

- Advanced retrieval
  - Add site-specific crawlers for top domains (AWS/Azure/GCP blogs, release notes, product pages). Run headless if needed and cache.
  - Embed-and-index fetched pages in a vector store (e.g., SQLite+FAISS or pgvector). Use incremental refresh (ETag/Last-Modified) and rate-limit per site.
- LLM planning
  - Agent plans daily subtopics per entity (services, SKUs, regions), expands sub-queries with event awareness (re: conferences, re:Invent/Ignite/Next) and seasonal terms.
  - De-duplicate at the “fact” level: Extract claims, dates, and products into structured events; cluster by event identity.
- Robust ranking
  - Bi-encoder for coarse rerank + cross-encoder for top-k precision (e.g., re-rank top 50 down to 15 with cross-encoder).
  - Temporal weighting + novelty penalty (down-rank items too similar to the last N runs).
- Quality guardrails
  - Source reputation scoring; blocklist spam; language filter; minimum text length & readability score.
- Observability & SLOs
  - Prometheus metrics: per-provider latency, fail rates; per-run: total queries, total sources, unique domains, median freshness, top errors.
  - Alerting: run fails, result count below threshold, zero coverage for any entity.
- Human-in-the-loop QA
  - Weekly sampling UI to label “useful/not useful”; feed back into re-rank weights.

Pros: Highest coverage/quality with auditability. Cons: More complexity and cost.

---

## Concrete next steps

1) Short term (this week)
- [ ] Provide a topics/entities config (JSON/YAML) for the scheduler.
- [ ] Enable balanced or quality mode for scheduled runs.
- [ ] Set SERPERDEV_API_KEY and OPENROUTER_API_KEY in Docker/Env.
- [ ] Persist raw run JSON to a mounted folder with timestamp and run_id.
- [ ] Add per-subquery cap and domain diversity thresholds to config.

2) Medium term (1–2 weeks)
- [ ] Add run storage (SQLite/Postgres) with migrations and a small dashboard.
- [ ] Implement time-bounded searches and recency weighting.
- [ ] Add cross-run dedupe using content hashing; report deltas since last run.
- [ ] Add simple evaluation harness comparing to a gold set.

3) Long term (3–6 weeks)
- [ ] Build site-specific crawlers for AWS/Azure/GCP blogs and release notes.
- [ ] Add cross-encoder re-rank for top-50 candidates.
- [ ] Instrument metrics and set alerts.

---

## Configuration sketch

- scheduler/topics.yaml

```
runs_per_day: 4
window_days: 2
entities:
  - name: aws
    queries:
      - "AWS cloud latest news"
      - "site:aws.amazon.com/blogs/aws/"
  - name: azure
    queries:
      - "Azure cloud latest news"
      - "site:azure.microsoft.com/en-us/blog/"
  - name: gcp
    queries:
      - "Google Cloud latest news"
      - "site:cloud.google.com/blog"
limits:
  per_entity: 5
  per_domain: 3
optimizationMode: balanced
```

- docker-compose scheduled job (sketch)

```
  scheduler:
    build: ./services/searchsvc
    command: ["python", "-m", "app.tools.schedule_run", "/config/topics.yaml", "/data/runs"]
    volumes:
      - ./config:/config
      - ./runs:/data/runs
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - SERPERDEV_API_KEY=${SERPERDEV_API_KEY}
      - API_BASE=http://api:3001
```

If you want, I can scaffold the scheduler module and a minimal topics.yaml next.