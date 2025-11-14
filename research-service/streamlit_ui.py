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
        mode = st.radio("Mode", ["Search", "Research", "Document Library"], index=0)

        st.subheader("🔍 Search Engine")
        search_engine = st.radio(
            "Select Search Backend",
            options=[
                "🌐 SearXNG (Primary)",
                "🚀 SerperDev (Alternative)",
                "🧠 Perplexity AI (Direct)",
                "🔄 Auto (SearXNG + SerperDev + Perplexity Fallback)",
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
            st.caption(
                "✅ Open-source metasearch engine\n🌍 Multiple search engines aggregated\n🔒 Privacy-focused"
            )
        elif selected_engine == "serperdev":
            st.caption("✅ Google search API\n⚡ Fast and reliable\n📊 Rich metadata")
        elif selected_engine == "perplexity":
            st.caption(
                "✅ AI-powered search\n🤖 Direct answers with citations\n📝 Ready-to-use content"
            )
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
            st.caption(
                "✅ Uses ENABLE_DYNAMIC_PROMPTS setting\n⚙️ Default from config\n🔧 Change in .env"
            )

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
                5,
                50,
                default_sources,
                help=f"Leave at {default_sources} to use {selected_mode.upper()} mode default",
            )
            timeout = st.slider(
                "Timeout (s, override)",
                10,
                300,
                default_timeout,
                help=f"Leave at {default_timeout}s to use {selected_mode.upper()} mode default",
            )
        else:
            max_iterations = st.slider("Max Iterations", 1, 5, 3)
            timeout = st.slider("Timeout (s)", 60, 600, 300)

        model = st.selectbox(
            "Model",
            [
                "google/gemini-2.0-flash-exp:free",
                "google/gemini-2.5-flash-lite",
                "deepseek/deepseek-chat",
            ],
            index=0,
        )

    # Main content
    if mode == "Search":
        render_search_mode(
            max_sources, timeout, model, selected_mode, selected_engine, selected_prompt_strategy
        )
    elif mode == "Research":
        render_research_mode(
            max_iterations, timeout, model, selected_mode, selected_engine, selected_prompt_strategy
        )
    else:
        render_document_library_mode()


def render_search_mode(
    max_sources: int, timeout: int, model: str, mode: str, search_engine: str, prompt_strategy: str
):
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


def render_research_mode(
    max_iterations: int,
    timeout: int,
    model: str,
    mode: str,
    search_engine: str,
    prompt_strategy: str,
):
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
            with st.expander(
                f"Step {step.get('step_number', 0)}: {step.get('description', 'N/A')}",
                expanded=False,
            ):
                st.markdown(f"**Search Query:** {step.get('search_query', 'N/A')}")
                st.markdown(f"**Expected Outcome:** {step.get('expected_outcome', 'N/A')}")
                if step.get("depends_on"):
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
        st.metric("Model", data.get("model_used", "N/A").split("/")[-1])

    # Citations
    st.markdown("### 📚 Citations")
    for idx, cite in enumerate(data.get("citations", []), 1):
        with st.container():
            relevance_emoji = (
                "🔥"
                if cite.get("relevance", 0) >= 0.8
                else "✅"
                if cite.get("relevance", 0) >= 0.6
                else "📄"
            )
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


def render_document_library_mode():
    """Render document library interface for upload, query, list, and delete."""
    st.header("📄 Document Library")
    st.write("Upload documents (PDF, Word, Excel, Text) and ask questions using RAG")

    # Initialize session state for documents
    if "documents" not in st.session_state:
        st.session_state.documents = []
    if "query_results" not in st.session_state:
        st.session_state.query_results = []

    # Create tabs for different operations
    tab1, tab2, tab3 = st.tabs(["📤 Upload", "🔍 Query Documents", "📚 My Documents"])

    # Tab 1: Upload Documents
    with tab1:
        st.subheader("Upload Document")

        col1, col2 = st.columns([2, 1])
        with col1:
            uploaded_file = st.file_uploader(
                "Choose a file",
                type=["pdf", "docx", "xlsx", "txt"],
                help="Supported formats: PDF, Word (.docx), Excel (.xlsx), Text (.txt)",
            )
        with col2:
            collection = st.text_input(
                "Collection",
                value="default",
                help="Group documents by collection name",
            )

        if st.button("📤 Upload Document", type="primary", disabled=uploaded_file is None):
            if uploaded_file:
                with st.spinner(f"Uploading {uploaded_file.name}..."):
                    try:
                        # Prepare multipart form data
                        files = {
                            "file": (
                                uploaded_file.name,
                                uploaded_file.getvalue(),
                                uploaded_file.type,
                            )
                        }
                        data = {"collection": collection}

                        response = httpx.post(
                            f"{API_BASE_URL}/v1/documents/upload",
                            files=files,
                            data=data,
                            timeout=120.0,
                        )

                        if response.status_code == 201:
                            result = response.json()
                            st.success(
                                f"✅ **{result['filename']}** uploaded successfully!\n\n"
                                f"📄 Document ID: `{result['document_id']}`\n\n"
                                f"📦 Chunks: {result['chunks_created']} | "
                                f"🧮 Dimensions: {result['embedding_dimension']} | "
                                f"📁 Collection: {result['collection']}"
                            )
                            # Refresh documents list
                            st.session_state.documents = []
                        else:
                            error_data = response.json()
                            st.error(
                                f"❌ Upload failed: {error_data.get('detail', 'Unknown error')}"
                            )

                    except Exception as e:
                        st.error(f"❌ Upload failed: {str(e)}")

        st.divider()
        st.info(
            "📋 **Supported Features:**\n\n"
            "✅ **PDF** - Extracts text, tables, and images\n\n"
            "✅ **Word (.docx)** - Full text extraction\n\n"
            "✅ **Excel (.xlsx)** - Converts tables to markdown\n\n"
            "✅ **Text (.txt)** - Direct text processing\n\n"
            "**Processing:**\n"
            "- Automatic chunking (1000 chars, 200 overlap)\n"
            "- Vector embeddings (384D)\n"
            "- Deduplication by content hash\n"
            "- Max file size: 50MB"
        )

    # Tab 2: Query Documents
    with tab2:
        st.subheader("Ask Questions")

        col1, col2 = st.columns([2, 1])
        with col1:
            query = st.text_input(
                "Your question",
                placeholder="What are the key findings in the research paper?",
                key="doc_query",
            )
        with col2:
            query_collection = st.text_input(
                "Collection",
                value="default",
                key="query_collection",
                help="Query documents from specific collection",
            )

        col3, col4, col5 = st.columns(3)
        with col3:
            top_k = st.slider(
                "Top K chunks", 5, 20, 10, help="Number of relevant chunks to retrieve"
            )
        with col4:
            similarity_threshold = st.slider(
                "Similarity threshold",
                0.0,
                1.0,
                0.3,
                step=0.05,
                help="Minimum similarity score (0-1)",
            )
        with col5:
            st.write("")  # Spacer
            query_btn = st.button("🔍 Ask", type="primary", use_container_width=True)

        if query_btn and query:
            with st.spinner("Searching documents..."):
                try:
                    response = httpx.post(
                        f"{API_BASE_URL}/v1/documents/query",
                        json={
                            "query": query,
                            "collection": query_collection,
                            "top_k": top_k,
                            "similarity_threshold": similarity_threshold,
                        },
                        timeout=60.0,
                    )

                    if response.status_code == 200:
                        result = response.json()

                        # Display answer
                        st.markdown("### 📝 Answer")
                        st.markdown(result["answer"])

                        # Display metadata
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("⏱️ Time", f"{result['execution_time']:.2f}s")
                        with col2:
                            st.metric("📄 Chunks Found", result["total_chunks_found"])
                        with col3:
                            st.metric("📊 Chunks Used", result["chunks_used"])

                        # Display sources
                        st.markdown("### 📚 Sources")
                        for idx, source in enumerate(result["sources"], 1):
                            with st.expander(
                                f"[{idx}] {source.get('metadata', {}).get('filename', 'Unknown')} "
                                f"(Similarity: {source.get('similarity', 0):.3f})",
                                expanded=False,
                            ):
                                st.markdown(f"**Content:**")
                                st.text(source["content"])

                                metadata = source.get("metadata", {})
                                st.markdown(f"**Metadata:**")
                                st.json(
                                    {
                                        "chunk_id": metadata.get("chunk_id"),
                                        "collection": metadata.get("collection"),
                                        "filename": metadata.get("filename"),
                                    }
                                )

                        # Store result in session state
                        st.session_state.query_results.insert(
                            0,
                            {
                                "query": query,
                                "result": result,
                                "timestamp": datetime.now(),
                            },
                        )

                    elif response.status_code == 404:
                        st.warning(
                            f"📭 No relevant documents found in collection '{query_collection}'.\n\n"
                            "Try:\n"
                            "- Uploading documents first\n"
                            "- Lowering the similarity threshold\n"
                            "- Checking the collection name"
                        )
                    else:
                        error_data = response.json()
                        st.error(f"❌ Query failed: {error_data.get('detail', 'Unknown error')}")

                except Exception as e:
                    st.error(f"❌ Query failed: {str(e)}")

        # Display query history
        if st.session_state.query_results:
            st.divider()
            st.markdown("### 📜 Query History")

            if st.button("🗑️ Clear History"):
                st.session_state.query_results = []
                st.rerun()

            for idx, item in enumerate(st.session_state.query_results[:5]):  # Show last 5
                with st.expander(
                    f"❓ {item['query'][:60]}... ({item['timestamp'].strftime('%H:%M:%S')})",
                    expanded=False,
                ):
                    st.markdown(f"**Answer:** {item['result']['answer'][:200]}...")
                    st.caption(
                        f"Sources: {item['result']['total_chunks_found']} | Time: {item['result']['execution_time']:.2f}s"
                    )

    # Tab 3: My Documents
    with tab3:
        st.subheader("Document Management")

        col1, col2 = st.columns([3, 1])
        with col1:
            list_collection = st.text_input(
                "Filter by collection",
                value="",
                placeholder="Leave empty for all collections",
                key="list_collection",
            )
        with col2:
            st.write("")  # Spacer
            if st.button("🔄 Refresh", use_container_width=True):
                st.session_state.documents = []

        # Fetch documents
        if not st.session_state.documents or st.button("Load Documents", key="hidden_load"):
            with st.spinner("Loading documents..."):
                try:
                    params = {}
                    if list_collection:
                        params["collection"] = list_collection

                    response = httpx.get(
                        f"{API_BASE_URL}/v1/documents",
                        params=params,
                        timeout=30.0,
                    )

                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.documents = result.get("documents", [])
                    else:
                        st.error("Failed to load documents")

                except Exception as e:
                    st.error(f"❌ Failed to load documents: {str(e)}")

        # Display documents
        if st.session_state.documents:
            st.info(f"📊 Total documents: {len(st.session_state.documents)}")

            for doc in st.session_state.documents:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

                    with col1:
                        st.markdown(f"**📄 {doc['filename']}**")
                        st.caption(
                            f"Collection: {doc['collection']} | "
                            f"Type: {doc['source_type']} | "
                            f"Chunks: {doc['chunks_count']}"
                        )

                    with col2:
                        st.caption(f"Created: {doc['created_at'][:10]}")

                    with col3:
                        if doc.get("access_count", 0) > 0:
                            st.caption(f"📊 {doc['access_count']} queries")

                    with col4:
                        if st.button(
                            "🗑️", key=f"delete_{doc['document_id']}", help="Delete document"
                        ):
                            with st.spinner("Deleting..."):
                                try:
                                    response = httpx.delete(
                                        f"{API_BASE_URL}/v1/documents/{doc['document_id']}",
                                        timeout=30.0,
                                    )

                                    if response.status_code == 200:
                                        st.success(f"✅ Deleted {doc['filename']}")
                                        st.session_state.documents = []
                                        st.rerun()
                                    else:
                                        error_data = response.json()
                                        st.error(
                                            f"❌ Delete failed: {error_data.get('detail', 'Unknown error')}"
                                        )

                                except Exception as e:
                                    st.error(f"❌ Delete failed: {str(e)}")

                    st.divider()
        else:
            st.info(
                "📭 No documents found.\n\nUpload documents in the **Upload** tab to get started!"
            )


if __name__ == "__main__":
    main()
