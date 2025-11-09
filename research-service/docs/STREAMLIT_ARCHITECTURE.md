# Streamlit Testing UI - Architecture & Implementation

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit Frontend                      │
│                     (Port 8501)                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │   Home   │  │   Test   │  │  Search  │  │ Research │  │
│  │  Status  │  │  Runner  │  │  Tester  │  │  Tester  │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│                                                             │
│  ┌──────────┐  ┌──────────┐                                │
│  │Dashboard │  │ Settings │                                │
│  └──────────┘  └──────────┘                                │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                   Shared Components                         │
│  • API Client      • Result Viewer    • Exporters          │
│  • Test Executor   • Metrics Collector • Formatters        │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP/REST
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Research Service API (Port 8001)               │
│           POST /v1/search    POST /v1/research              │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  PostgreSQL  │   │     Redis    │   │   Langfuse   │
│  + pgvector  │   │    Cache     │   │  Monitoring  │
└──────────────┘   └──────────────┘   └──────────────┘
```

---

## 📁 File Structure

```
research-service/
├── streamlit_app.py                 # Main entry point
├── requirements-streamlit.txt       # Streamlit dependencies
├── Dockerfile.streamlit             # Streamlit container
│
├── pages/                           # Streamlit pages
│   ├── 1_🏠_home.py                 # System status
│   ├── 2_🧪_test_runner.py          # Test execution
│   ├── 3_🔍_search_tester.py        # Search mode
│   ├── 4_🔬_research_tester.py      # Research mode
│   ├── 5_📊_dashboard.py            # Metrics
│   └── 6_⚙️_settings.py             # Configuration
│
├── components/                      # Reusable UI components
│   ├── __init__.py
│   ├── api_client.py                # Research API client
│   ├── test_executor.py             # Pytest subprocess runner
│   ├── metrics_collector.py         # Performance tracking
│   ├── result_viewer.py             # Result display widgets
│   ├── langfuse_widget.py           # Langfuse integration
│   ├── progress_tracker.py          # Progress bar components
│   └── source_viewer.py             # Source citation display
│
├── utils/                           # Utility functions
│   ├── __init__.py
│   ├── formatters.py                # Output formatting
│   ├── validators.py                # Input validation
│   ├── exporters.py                 # PDF/CSV/JSON export
│   └── session_state.py             # Streamlit state management
│
└── assets/                          # Static assets
    ├── styles.css                   # Custom CSS
    └── logo.png                     # Application logo
```

---

## 🔧 Component Breakdown

### 1. API Client (`components/api_client.py`)

```python
"""Research Service API Client."""

import httpx
import asyncio
from typing import Callable, Optional
import streamlit as st


class ResearchAPIClient:
    """Client for interacting with research service API."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.timeout = httpx.Timeout(300.0, connect=5.0)
    
    async def search(
        self,
        query: str,
        params: dict,
        progress_callback: Optional[Callable] = None
    ) -> dict:
        """Execute search mode with streaming progress."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/v1/search",
                    json={"query": query, **params}
                )
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException:
                return {"error": "Request timed out"}
            except httpx.HTTPError as e:
                return {"error": str(e)}
    
    async def research(
        self,
        query: str,
        params: dict,
        progress_callback: Optional[Callable] = None
    ) -> dict:
        """Execute research mode with streaming progress."""
        # Similar to search() but for research endpoint
        pass
    
    def health_check(self) -> dict:
        """Check API health status."""
        try:
            response = httpx.get(
                f"{self.base_url}/health",
                timeout=5.0
            )
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "latency_ms": response.elapsed.total_seconds() * 1000
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
```

### 2. Test Executor (`components/test_executor.py`)

```python
"""Pytest test execution via subprocess."""

import subprocess
import threading
from typing import Dict, List, Callable
import queue


class TestExecutor:
    """Execute pytest tests and stream output."""
    
    def __init__(self):
        self.process = None
        self.output_queue = queue.Queue()
    
    def run_tests(
        self,
        test_paths: List[str],
        options: Dict,
        output_callback: Callable[[str], None]
    ) -> Dict:
        """Run pytest tests with real-time output."""
        cmd = ["pytest"] + test_paths
        
        # Add options
        if options.get("verbose"):
            cmd.append("-v")
        if options.get("coverage"):
            cmd.extend(["--cov=src", "--cov-report=json"])
        if options.get("stop_on_fail"):
            cmd.append("-x")
        if markers := options.get("markers"):
            cmd.extend(["-m", markers])
        
        # Run in subprocess
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Stream output
        for line in self.process.stdout:
            output_callback(line.rstrip())
        
        self.process.wait()
        
        return {
            "exit_code": self.process.returncode,
            "passed": self.process.returncode == 0
        }
    
    def stop(self):
        """Stop running tests."""
        if self.process:
            self.process.terminate()
            self.process.wait()
```

### 3. Result Viewer (`components/result_viewer.py`)

```python
"""Reusable result display components."""

import streamlit as st
from typing import Dict, List


def render_search_result(result: Dict):
    """Render search mode result."""
    st.markdown("### 📄 Answer")
    st.markdown(result["answer"])
    
    st.markdown("### 📚 Sources")
    for idx, source in enumerate(result["sources"], 1):
        with st.expander(f"[{idx}] {source['title']}", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**URL:** {source['url']}")
                st.markdown(f"**Type:** {source['type']}")
                if snippet := source.get("snippet"):
                    st.caption(snippet)
            
            with col2:
                st.metric("Relevance", f"{source['relevance']:.2f}")
                if source.get("used_in_synthesis"):
                    st.success("Used ✓")


def render_metrics(metrics: Dict):
    """Render performance metrics."""
    cols = st.columns(4)
    
    with cols[0]:
        st.metric("Execution Time", f"{metrics['execution_time']:.1f}s")
    with cols[1]:
        st.metric("Total Tokens", f"{metrics['total_tokens']:,}")
    with cols[2]:
        st.metric("Cost", f"${metrics['cost']:.4f}")
    with cols[3]:
        st.metric("Sources", metrics['source_count'])


def render_langfuse_link(trace_id: str, base_url: str = "https://cloud.langfuse.com"):
    """Render Langfuse trace link."""
    trace_url = f"{base_url}/traces/{trace_id}"
    
    st.markdown(f"""
    🔗 **Langfuse Trace**  
    [View Full Trace]({trace_url}) | [View Analytics]({trace_url}/analytics)
    """)
```

### 4. Progress Tracker (`components/progress_tracker.py`)

```python
"""Real-time progress tracking components."""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List


class ProgressTracker:
    """Track and display pipeline execution progress."""
    
    def __init__(self, steps: List[str]):
        self.steps = steps
        self.current_step = 0
        self.step_times = {}
        self.start_time = datetime.now()
        
        # Initialize Streamlit placeholders
        self.status_text = st.empty()
        self.progress_bar = st.empty()
        self.step_container = st.empty()
        self.time_text = st.empty()
    
    def update_step(self, step_name: str, status: str = "processing"):
        """Update current step status."""
        self.step_times[step_name] = {
            "start": datetime.now(),
            "status": status
        }
        
        # Update UI
        self._render()
    
    def complete_step(self, step_name: str, elapsed_seconds: float):
        """Mark step as complete."""
        if step_name in self.step_times:
            self.step_times[step_name]["elapsed"] = elapsed_seconds
            self.step_times[step_name]["status"] = "completed"
        
        self.current_step += 1
        self._render()
    
    def _render(self):
        """Render progress UI."""
        # Status text
        current = self.steps[self.current_step] if self.current_step < len(self.steps) else "Complete"
        self.status_text.markdown(f"**Status:** {current}")
        
        # Progress bar
        progress = self.current_step / len(self.steps)
        self.progress_bar.progress(progress)
        
        # Step list
        with self.step_container.container():
            for step in self.steps:
                status = self.step_times.get(step, {}).get("status", "pending")
                elapsed = self.step_times.get(step, {}).get("elapsed", 0)
                
                icon = {
                    "completed": "✅",
                    "processing": "🔄",
                    "pending": "⏸️",
                    "failed": "❌"
                }.get(status, "⏸️")
                
                time_str = f"({elapsed:.1f}s)" if elapsed > 0 else ""
                st.markdown(f"{icon} {step} {time_str}")
        
        # Elapsed time
        total_elapsed = (datetime.now() - self.start_time).total_seconds()
        self.time_text.markdown(f"**Elapsed:** {total_elapsed:.1f}s")
```

---

## 🎨 Styling (`assets/styles.css`)

```css
/* Custom Streamlit styling */

/* Main container */
.main {
    padding: 2rem;
}

/* Headers */
h1 {
    color: #1f77b4;
    border-bottom: 2px solid #1f77b4;
    padding-bottom: 0.5rem;
}

/* Metric cards */
.metric-card {
    background: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* Status indicators */
.status-healthy {
    color: #28a745;
}

.status-unhealthy {
    color: #dc3545;
}

.status-warning {
    color: #ffc107;
}

/* Test output console */
.test-output {
    font-family: 'Courier New', monospace;
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 1rem;
    border-radius: 0.5rem;
    overflow-x: auto;
    max-height: 600px;
    overflow-y: auto;
}

/* Source cards */
.source-card {
    border-left: 3px solid #1f77b4;
    padding-left: 1rem;
    margin-bottom: 1rem;
}

/* Progress indicators */
.step-completed {
    color: #28a745;
}

.step-processing {
    color: #007bff;
    animation: pulse 1.5s infinite;
}

.step-pending {
    color: #6c757d;
}

.step-failed {
    color: #dc3545;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

/* Buttons */
.stButton > button {
    background: #1f77b4;
    color: white;
    border-radius: 0.5rem;
    padding: 0.5rem 2rem;
    font-weight: 500;
}

.stButton > button:hover {
    background: #1557a0;
}

/* Langfuse links */
.langfuse-link {
    color: #1f77b4;
    text-decoration: none;
    font-weight: 500;
}

.langfuse-link:hover {
    text-decoration: underline;
}
```

---

## 🚀 Main Entry Point (`streamlit_app.py`)

```python
"""Research Service Testing UI - Main Entry."""

import streamlit as st
from components.api_client import ResearchAPIClient

# Page configuration
st.set_page_config(
    page_title="Research Service Testing UI",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
with open("assets/styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Initialize session state
if "api_client" not in st.session_state:
    api_url = st.secrets.get("RESEARCH_API_URL", "http://localhost:8001")
    st.session_state.api_client = ResearchAPIClient(api_url)

if "test_history" not in st.session_state:
    st.session_state.test_history = []

# Sidebar
with st.sidebar:
    st.title("🔬 Research Testing")
    st.markdown("---")
    
    # API status
    st.subheader("API Status")
    health = st.session_state.api_client.health_check()
    
    if health["status"] == "healthy":
        st.success(f"✅ Connected ({health.get('latency_ms', 0):.0f}ms)")
    else:
        st.error(f"❌ {health.get('error', 'Disconnected')}")
    
    st.markdown("---")
    
    # Quick actions
    st.subheader("Quick Actions")
    if st.button("🔄 Refresh Status"):
        st.rerun()
    
    if st.button("🧪 Run All Tests"):
        st.switch_page("pages/2_🧪_test_runner.py")
    
    st.markdown("---")
    
    # About
    st.caption("Research Service Testing UI v0.1.0")
    st.caption("[Documentation](./docs/STREAMLIT_APP_SPEC.md)")

# Home page content
st.title("🔬 Research Service Testing UI")
st.markdown("""
Welcome to the comprehensive testing interface for the research service.

**Features:**
- 🧪 Run pytest test suites
- 🔍 Test search mode interactively
- 🔬 Test research mode with iterations
- 📊 Monitor performance metrics
- 🔗 Debug with Langfuse traces
""")

# Quick stats
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Tests Today", "127", "+12")

with col2:
    st.metric("Avg Search Time", "42.3s", "-3.2s")

with col3:
    st.metric("Avg Research Time", "3m 48s", "+15s")

with col4:
    st.metric("Success Rate", "97.2%", "+1.5%")

st.markdown("---")

# Recent sessions
st.subheader("📋 Recent Sessions")
st.dataframe(
    {
        "Session ID": ["abc123...", "def456...", "ghi789..."],
        "Query": ["AI agents", "Climate change", "Quantum computing"],
        "Mode": ["Search", "Research", "Search"],
        "Time": ["42.3s", "3m 48s", "38.1s"],
        "Status": ["✅ Success", "✅ Success", "✅ Success"]
    },
    use_container_width=True
)

# Navigation
st.markdown("---")
st.markdown("### 🧭 Navigate to:")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🧪 Test Runner", use_container_width=True):
        st.switch_page("pages/2_🧪_test_runner.py")

with col2:
    if st.button("🔍 Search Tester", use_container_width=True):
        st.switch_page("pages/3_🔍_search_tester.py")

with col3:
    if st.button("🔬 Research Tester", use_container_width=True):
        st.switch_page("pages/4_🔬_research_tester.py")
```

---

## 📦 Dependencies (`requirements-streamlit.txt`)

```txt
# Streamlit and UI
streamlit==1.29.0
streamlit-option-menu==0.3.6

# HTTP clients
httpx==0.25.2
requests==2.31.0

# Data handling
pandas==2.2.3
numpy==2.1.3

# Visualization
plotly==5.24.1
matplotlib==3.9.2

# Testing
pytest==8.3.4
pytest-asyncio==0.24.0

# Utilities
python-json-logger==3.2.1
markdown==3.7
python-dotenv==1.0.1

# PDF export
reportlab==4.2.5
weasyprint==62.3
```

---

## 🐳 Dockerfile (`Dockerfile.streamlit`)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PDF export
RUN apt-get update && apt-get install -y \
    build-essential \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-streamlit.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-streamlit.txt

# Copy application code
COPY streamlit_app.py .
COPY pages/ ./pages/
COPY components/ ./components/
COPY utils/ ./utils/
COPY assets/ ./assets/

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run Streamlit
CMD ["streamlit", "run", "streamlit_app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
```

---

## 🎯 Implementation Checklist

### Week 12
- [ ] Day 1: Setup project structure
- [ ] Day 2: Implement API client + test executor
- [ ] Day 3: Build home page + test runner
- [ ] Day 4: Build search tester page
- [ ] Day 5: Build research tester page

### Week 13
- [ ] Day 1: Build performance dashboard
- [ ] Day 2: Build settings page
- [ ] Day 3: Add export functionality
- [ ] Day 4: Styling and polish
- [ ] Day 5: Testing and documentation

---

**Status**: Architecture Complete - Ready for Implementation 🚀
