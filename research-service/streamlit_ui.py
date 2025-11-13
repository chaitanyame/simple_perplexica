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

        st.subheader("🔍 Search Engine")
        search_engine = st.radio(
            "Select Search Backend",
            options=[
                "🌐 SearXNG (Primary)", 
                "🚀 SerperDev (Alternative)", 
                "🧠 Perplexity AI (Direct)",
                "🔄 Auto (SearXNG + SerperDev + Perplexity Fallback)"
            ],
            index=3,  # Default to Auto with full cascade
            help="Choose which search engine to use for fetching results",
        )
        
        # Extract search engine preference
        engine_map = {
            "🌐 SearXNG (Primary)": "searxng",
            "🚀 SerperDev (Alternative)": "serperdev",
            "🧠 Perplexity AI (Direct)": "perplexity",
            "🔄 Auto (SearXNG + SerperDev + Perplexity Fallback)": "auto",
        }
        selected_engine = engine_map[search_engine]
        
        # Display engine info
        if selected_engine == "searxng":
            st.caption("✅ Open-source metasearch engine\n🌍 Multiple search engines aggregated\n🔒 Privacy-focused")
        elif selected_engine == "serperdev":
            st.caption("✅ Google search API\n⚡ Fast and reliable\n📊 Rich metadata")
        elif selected_engine == "perplexity":
            st.caption("✅ AI-powered search\n🤖 Direct answers with citations\n📝 Ready-to-use content")
        else:
            st.caption("✅ Best of all worlds\n🔄 3-tier automatic fallback\n🛡️ Maximum redundancy")

        st.subheader("🎯 Prompt Strategy")
        prompt_strategy_option = st.radio(
            "System Prompts",
            options=["🤖 Auto (Config)", "📝 Static (Fixed)", "✨ Dynamic (Context-Aware)"],
            index=0,  # Default to Auto
            help="Choose how system prompts are generated",
        )
        
        # Extract prompt strategy
        prompt_strategy_map = {
            "🤖 Auto (Config)": "auto",
            "📝 Static (Fixed)": "static",
            "✨ Dynamic (Context-Aware)": "dynamic",
        }
        selected_prompt_strategy = prompt_strategy_map[prompt_strategy_option]
        
        # Display prompt strategy info
        if selected_prompt_strategy == "static":
            st.caption("✅ Fixed prompts\n⚡ Always fast\n🎯 Predictable results")
        elif selected_prompt_strategy == "dynamic":
            st.caption("✅ Query-aware prompts\n🎨 Context-optimized\n📊 Type & domain detection")
        else:
            st.caption("✅ Uses ENABLE_DYNAMIC_PROMPTS setting\n⚙️ Default from config\n🔧 Change in .env")

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
            # Get mode-specific defaults from search_modes.py
            mode_defaults = {
                "speed": {"max_sources": 5, "timeout": 15},
                "balanced": {"max_sources": 10, "timeout": 45},
                "deep": {"max_sources": 20, "timeout": 60},
            }
            default_sources = mode_defaults[selected_mode]["max_sources"]
            default_timeout = mode_defaults[selected_mode]["timeout"]
            
            max_sources = st.slider(
                "Max Sources (override)", 
                5, 50, default_sources,
                help=f"Leave at {default_sources} to use {selected_mode.upper()} mode default"
            )
            timeout = st.slider(
                "Timeout (s, override)", 
                10, 300, default_timeout,
                help=f"Leave at {default_timeout}s to use {selected_mode.upper()} mode default"
            )
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
        render_search_mode(max_sources, timeout, model, selected_mode, selected_engine, selected_prompt_strategy)
    else:
        render_research_mode(max_iterations, timeout, model, selected_mode, selected_engine, selected_prompt_strategy)


def render_search_mode(max_sources: int, timeout: int, model: str, mode: str, search_engine: str, prompt_strategy: str):
    """Render search interface."""
    st.header("🔎 Fast Search")
    st.write(f"Quick web search with multi-source aggregation (via {search_engine.upper()})")

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
                # Get mode-specific defaults
                mode_defaults = {
                    "speed": {"max_sources": 5, "timeout": 15},
                    "balanced": {"max_sources": 10, "timeout": 45},
                    "deep": {"max_sources": 20, "timeout": 60},
                }
                default_sources = mode_defaults[mode]["max_sources"]
                default_timeout = mode_defaults[mode]["timeout"]
                
                payload = {
                    "query": query,
                    "mode": mode,
                    "model": model,
                    "search_engine": search_engine,  # Add search engine preference
                    "prompt_strategy": prompt_strategy,  # Add prompt strategy
                }
                # Only include overrides if user changed them from mode defaults
                if max_sources != default_sources:
                    payload["max_sources"] = max_sources
                if timeout != default_timeout:
                    payload["timeout"] = timeout
                
                # Choose endpoint based on search engine
                if search_engine == "perplexity":
                    endpoint = f"{API_BASE_URL}/v1/search/perplexity"
                    st.info("🧠 Using Perplexity AI for direct search with citations...")
                else:
                    endpoint = f"{API_BASE_URL}/v1/search"
                
                response = httpx.post(
                    endpoint,
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


def render_research_mode(max_iterations: int, timeout: int, model: str, mode: str, search_engine: str, prompt_strategy: str):
    """Render research interface."""
    st.header("🔬 Deep Research")
    st.write(f"Comprehensive research with iterative synthesis (via {search_engine.upper()})")

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
                        "search_engine": search_engine,  # Add search engine preference
                        "prompt_strategy": prompt_strategy,  # Add prompt strategy
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
    plan = data.get("plan", {})
    st.write(f"**Original Query:** {plan.get('original_query', 'N/A')}")
    st.write(f"**Estimated Time:** {plan.get('estimated_time', 0):.0f}s")
    st.write(f"**Complexity:** {plan.get('complexity', 'N/A').title()}")

    if plan.get("steps"):
        st.markdown("**Research Steps:**")
        for step in plan["steps"]:
            with st.expander(f"Step {step.get('step_number', 0)}: {step.get('description', 'N/A')}", expanded=False):
                st.markdown(f"**Search Query:** {step.get('search_query', 'N/A')}")
                st.markdown(f"**Expected Outcome:** {step.get('expected_outcome', 'N/A')}")
                if step.get('depends_on'):
                    st.markdown(f"**Depends On Steps:** {', '.join(map(str, step['depends_on']))}")

    # Findings (now a single string, not an array)
    st.markdown("### � Key Findings")
    findings_text = data.get("findings", "No findings available")
    st.markdown(findings_text)

    # Metadata
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Execution Time", f"{data.get('execution_time', 0):.2f}s")
    with col2:
        st.metric("Confidence", f"{data.get('confidence', 0):.2%}")
    with col3:
        st.metric("Model", data.get('model_used', 'N/A').split('/')[-1])

    # Citations
    st.markdown("### 📚 Citations")
    for idx, cite in enumerate(data.get("citations", []), 1):
        with st.container():
            relevance_emoji = "🔥" if cite.get("relevance", 0) >= 0.8 else "✅" if cite.get("relevance", 0) >= 0.6 else "📄"
            st.markdown(
                f"{relevance_emoji} **[{idx}] [{cite.get('title', 'No title')}]({cite.get('url', '#')})**"
            )
            st.caption(cite.get("excerpt", "No excerpt"))
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
