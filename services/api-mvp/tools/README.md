# Vetuku API Streamlit Tester

A lightweight Streamlit UI to exercise the API-only MVP endpoints with and without streaming.

## Setup

Create a virtual environment (optional but recommended) and install dependencies:

```pwsh
python -m venv .venv-tools
./.venv-tools/Scripts/Activate.ps1
pip install -r services/api-mvp/tools/requirements.txt
```

## Run

Ensure the API is running and reachable. Then start Streamlit:

```pwsh
$env:API_BASE_URL = "http://localhost:3001"
streamlit run services/api-mvp/tools/streamlit_app.py
```

- Use the sidebar to pick a focus mode and toggle streaming.
- Click "Check Providers" to verify `/api/providers`.
- Enter a query and run a search.

## Notes

- The streaming UI expects NDJSON events with types: `init`, `sources`, `response`, and `done`.
- For non-streaming, the endpoint should return `{ message: string, sources: Source[] }`.
