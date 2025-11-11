"""Streamlit UI for Research Service - Quick MVP."""

import json
import os
from datetime import datetime

import httpx
import streamlit as st

# Configuration - Use environment variable or default to port 8001
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001/api")

st.set_page_config(
    page_title="Research Service",
    page_icon="🔍",
    layout="wide",
)

# Initialize session state
if "search_history" not in st.session_state:
    st.session_state.search_history = []
if "research_history" not in st.session_state:
    st.session_state.research_history = []


def main():
    """Main Streamlit app."""
    st.title("🔍 Research Service")
    st.caption("Advanced Search & Research powered by Multi-Agent AI")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        mode = st.radio("Mode", ["Search", "Research"], index=0)

        st.subheader("Query Optimization")
        search_mode = st.radio(
            "Search Mode",
            options=["⚡ SPEED", "⚖️ BALANCED", "🔍 DEEP"],
            index=1,  # Default to BALANCED
            help="Choose the search mode based on your needs",
        )
        
        # Extract mode string (speed, balanced, deep)
        mode_map = {
            "⚡ SPEED": "speed",
            "⚖️ BALANCED": "balanced",
            "🔍 DEEP": "deep",
        }
        selected_mode = mode_map[search_mode]
        
        # Display mode info
        mode_info = {
            "speed": {
                "sources": "5 sources",
                "timeout": "15 seconds",
                "features": "Snippets only, no crawling",
                "use_case": "Quick lookups",
            },
            "balanced": {
                "sources": "10 sources",
                "timeout": "45 seconds",
                "features": "Selective crawling (5 URLs), reranking enabled",
                "use_case": "Default for most queries",
            },
            "deep": {
                "sources": "20 sources",
                "timeout": "60 seconds",
                "features": "Full crawling, reranking, RAG with history",
                "use_case": "Comprehensive research",
            },
        }
        
        info = mode_info[selected_mode]
        st.info(
            f"**{info['sources']}** | **{info['timeout']}**\n\n"
            f"✨ {info['features']}\n\n"
            f"💡 Best for: {info['use_case']}"
        )

        st.subheader("Advanced Parameters")
        if mode == "Search":
            max_sources = st.slider("Max Sources (override)", 5, 50, 20, help="Leave default to use mode setting")
            timeout = st.slider("Timeout (s, override)", 10, 300, 60, help="Leave default to use mode setting")
        else:
            max_iterations = st.slider("Max Iterations", 1, 5, 3)
            timeout = st.slider("Timeout (s)", 60, 600, 300)

        model = st.selectbox(
            "Model",
            ["anthropic/claude-3.5-sonnet", "deepseek/deepseek-chat"],
            index=0,
        )

    # Main content
    if mode == "Search":
        render_search_mode(max_sources, timeout, model, selected_mode)
    else:
        render_research_mode(max_iterations, timeout, model, selected_mode)


def render_search_mode(max_sources: int, timeout: int, model: str, mode: str):
    """Render search interface."""
    st.header("🔎 Fast Search")
    st.write("Quick web search with multi-source aggregation")

    query = st.text_input(
        "Enter your search query",
        placeholder="What is Pydantic AI?",
        key="search_query",
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        search_btn = st.button("🔍 Search", type="primary", use_container_width=True)
    with col2:
        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.search_history = []
            st.rerun()

    if search_btn and query:
        with st.spinner("Searching..."):
            try:
                # Build request payload - mode will override max_sources/timeout if not explicitly set
                payload = {
                    "query": query,
                    "mode": mode,
                    "model": model,
                }
                # Only include overrides if user changed them from defaults
                if max_sources != 20:  # 20 is the default slider value
                    payload["max_sources"] = max_sources
                if timeout != 60:  # 60 is the default slider value
                    payload["timeout"] = timeout
                
                response = httpx.post(
                    f"{API_BASE_URL}/v1/search",
                    json=payload,
                    timeout=timeout + 10,
                )

                if response.status_code == 200:
                    data = response.json()
                    st.session_state.search_history.insert(
                        0,
                        {
                            "query": query,
                            "data": data,
                            "timestamp": datetime.now(),
                        },
                    )
                    st.success("✅ Search completed!")
                else:
                    error_data = response.json()
                    st.error(f"❌ Error: {error_data.get('message', 'Unknown error')}")

            except Exception as e:
                st.error(f"❌ Request failed: {str(e)}")

    # Display results
    if st.session_state.search_history:
        for idx, item in enumerate(st.session_state.search_history):
            with st.expander(
                f"🔍 {item['query'][:60]}... ({item['timestamp'].strftime('%H:%M:%S')})",
                expanded=(idx == 0),
            ):
                render_search_result(item["data"])


def render_search_result(data: dict):
    """Render search result."""
    # Answer
    st.markdown("### 📄 Answer")
    st.info(data.get("answer", "No answer available"))

    # Metadata
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Execution Time", f"{data.get('execution_time', 0):.2f}s")
    with col2:
        st.metric("Confidence", f"{data.get('confidence', 0):.2%}")
    with col3:
        st.metric("Sources", len(data.get("sources", [])))
    with col4:
        mode_display = data.get("mode", "balanced").upper()
        mode_emoji = {"SPEED": "⚡", "BALANCED": "⚖️", "DEEP": "🔍"}.get(mode_display, "⚖️")
        st.metric("Mode", f"{mode_emoji} {mode_display}")

    # Sub-queries
    if data.get("sub_queries"):
        st.markdown("### 🔗 Sub-Queries")
        for sq in data["sub_queries"]:
            st.markdown(f"- {sq.get('query', '')} *(Priority: {sq.get('priority', 0)})*")

    # Sources
    st.markdown("### 📚 Sources")
    for idx, source in enumerate(data.get("sources", []), 1):
        with st.container():
            st.markdown(
                f"**[{idx}] [{source.get('title', 'No title')}]({source.get('url', '#')})**"
            )
            st.caption(source.get("snippet", "No snippet"))
            st.progress(
                source.get("relevance", 0), text=f"Relevance: {source.get('relevance', 0):.2%}"
            )
            st.divider()

    # Export
    if st.button("📥 Export JSON", key=f"export_{data.get('session_id')}"):
        st.download_button(
            "Download",
            data=json.dumps(data, indent=2),
            file_name=f"search_{data.get('session_id')}.json",
            mime="application/json",
        )


def render_research_mode(max_iterations: int, timeout: int, model: str, mode: str):
    """Render research interface."""
    st.header("🔬 Deep Research")
    st.write("Comprehensive research with iterative synthesis")

    query = st.text_area(
        "Enter your research question",
        placeholder="Explain AI agents and how they work, including current applications",
        height=100,
        key="research_query",
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        research_btn = st.button("🔬 Research", type="primary", use_container_width=True)
    with col2:
        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.research_history = []
            st.rerun()

    if research_btn and query:
        with st.spinner("Researching... This may take a few minutes"):
            try:
                response = httpx.post(
                    f"{API_BASE_URL}/v1/research",
                    json={
                        "query": query,
                        "max_iterations": max_iterations,
                        "timeout": timeout,
                        "mode": mode,
                        "model": model,
                    },
                    timeout=timeout + 10,
                )

                if response.status_code == 200:
                    data = response.json()
                    st.session_state.research_history.insert(
                        0,
                        {
                            "query": query,
                            "data": data,
                            "timestamp": datetime.now(),
                        },
                    )
                    st.success("✅ Research completed!")
                else:
                    error_data = response.json()
                    st.error(f"❌ Error: {error_data.get('message', 'Unknown error')}")

            except Exception as e:
                st.error(f"❌ Request failed: {str(e)}")

    # Display results
    if st.session_state.research_history:
        for idx, item in enumerate(st.session_state.research_history):
            with st.expander(
                f"🔬 {item['query'][:60]}... ({item['timestamp'].strftime('%H:%M:%S')})",
                expanded=(idx == 0),
            ):
                render_research_result(item["data"])


def render_research_result(data: dict):
    """Render research result."""
    # Research Plan
    st.markdown("### 📋 Research Plan")
    plan = data.get("research_plan", {})
    st.write(f"**Focus Areas:** {', '.join(plan.get('focus_areas', []))}")
    st.write(f"**Estimated Sources:** {plan.get('estimated_sources', 0)}")

    if plan.get("queries"):
        st.markdown("**Queries:**")
        for q in plan["queries"]:
            st.markdown(f"- {q}")

    # Findings
    st.markdown("### 🔍 Key Findings")
    for idx, finding in enumerate(data.get("findings", []), 1):
        st.markdown(f"{idx}. {finding}")

    # Synthesis
    st.markdown("### 📝 Synthesis")
    st.success(data.get("synthesis", "No synthesis available"))

    # Metadata
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Execution Time", f"{data.get('execution_time', 0):.2f}s")
    with col2:
        st.metric("Confidence", f"{data.get('confidence', 0):.2%}")

    # Citations
    st.markdown("### 📚 Citations")
    for cite in data.get("citations", []):
        with st.container():
            used = "✅" if cite.get("used_in_synthesis") else "📄"
            st.markdown(
                f"{used} **[{cite.get('id')}] [{cite.get('title', 'No title')}]({cite.get('url', '#')})**"
            )
            st.caption(cite.get("snippet", "No snippet"))
            st.progress(cite.get("relevance", 0), text=f"Relevance: {cite.get('relevance', 0):.2%}")
            st.divider()

    # Export
    if st.button("📥 Export JSON", key=f"export_{data.get('session_id')}"):
        st.download_button(
            "Download",
            data=json.dumps(data, indent=2),
            file_name=f"research_{data.get('session_id')}.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()
