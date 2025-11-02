import os
import json
from typing import Iterator, Optional

import httpx
import streamlit as st


def get_api_base_url() -> str:
    return os.getenv("API_BASE_URL", "http://localhost:3001")


def post_search(
    base_url: str,
    query: str,
    focus_mode: str,
    optimization_mode: str,
    system_instructions: Optional[str],
    stream: bool,
):
    url = f"{base_url}/api/search"
    payload = {
        "query": query,
        "focusMode": focus_mode,
        "optimizationMode": optimization_mode,
        "stream": stream,
    }
    if system_instructions:
        payload["systemInstructions"] = system_instructions

    return httpx.post(url, json=payload, timeout=60)


def stream_search(
    base_url: str,
    query: str,
    focus_mode: str,
    optimization_mode: str,
    system_instructions: Optional[str],
) -> Iterator[dict]:
    url = f"{base_url}/api/search"
    payload = {
        "query": query,
        "focusMode": focus_mode,
        "optimizationMode": optimization_mode,
        "stream": True,
    }
    if system_instructions:
        payload["systemInstructions"] = system_instructions

    with httpx.stream("POST", url, json=payload, timeout=None) as resp:
        resp.raise_for_status()
        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            try:
                event = json.loads(raw_line)
                yield event
            except json.JSONDecodeError:
                # Ignore malformed keep-alives
                continue


def render_sources(sources: list[dict]):
    if not sources:
        st.info("No sources returned.")
        return
    for s in sources:
        title = s.get("title") or "Untitled"
        url = s.get("url") or ""
        snippet = s.get("pageContent") or ""
        st.markdown(
            f"- [{title}]({url})\n\n  {snippet[:200]}{'…' if len(snippet) > 200 else ''}"
        )


def post_generate_content(
    base_url: str,
    topic: str,
    temperature: float,
) -> dict:
    """Call the researchsvc /api/generate endpoint"""
    url = f"{base_url}/api/generate"
    payload = {
        "topic": topic,
        "temperature": temperature,
    }
    return httpx.post(url, json=payload, timeout=180)


def main():
    st.set_page_config(page_title="API Tester", layout="wide")
    st.title("Simple Perplexica API Tester")
    st.caption("Test search and research services")

    # Create tabs for different services
    tab1, tab2 = st.tabs(["🔍 Search Service", "📝 Research Service"])

    # Create tabs for different services
    tab1, tab2 = st.tabs(["🔍 Search Service", "📝 Research Service"])

    # ==================== TAB 1: SEARCH SERVICE ====================
    with tab1:
        with st.sidebar:
            st.header("Search Settings")
            search_base_url = st.text_input(
                "Search API Base URL",
                value="http://api:3001",
                help="e.g. http://localhost:3000",
            )
            focus_mode = st.selectbox(
                "Focus Mode",
                [
                    "webSearch",
                    "academicSearch",
                    "writingAssistant",
                    "wolframAlphaSearch",
                    "youtubeSearch",
                    "redditSearch",
                ],
                index=0,
            )
            optimization_mode = st.selectbox(
                "Optimization Mode",
                ["speed", "balanced", "quality"],
                index=1,  # Default to balanced
                help="Speed: Fast, snippets only | Balanced: Moderate, some URL fetching | Quality: Slow, full URL content",
            )
            use_stream = st.toggle("Stream results", value=False)
            st.divider()
            if st.button("Check Providers"):
                try:
                    r = httpx.get(f"{search_base_url}/api/providers")
                    r.raise_for_status()
                    st.success("Providers ok")
                    st.code(json.dumps(r.json(), indent=2))
                except Exception as e:
                    st.error(f"Providers error: {e}")

        query = st.text_area("Query", placeholder="Ask something…", height=120)
        system_instructions = st.text_area(
            "System Instructions (optional)",
            placeholder="You are a helpful search assistant…",
            height=100,
        )

        col1, col2 = st.columns([1, 3])
        with col1:
            run = st.button("Run Search", type="primary")
        with col2:
            st.write("")

        st.divider()

        if run:
            if not query.strip():
                st.warning("Please enter a query.")
            elif not use_stream:
                with st.spinner("Requesting…"):
                    try:
                        r = post_search(
                            search_base_url,
                            query,
                            focus_mode,
                            optimization_mode,
                            system_instructions,
                            stream=False,
                        )
                        if r.status_code >= 400:
                            st.error(f"Error {r.status_code}: {r.text}")
                        else:
                            data = r.json()
                            st.subheader("Answer")
                            st.write(data.get("message", ""))
                            st.subheader("Sources")
                            render_sources(data.get("sources") or [])
                    except Exception as e:
                        st.error(f"Request error: {e}")
            else:
                # Streaming mode
                st.subheader("Answer (streaming)")
                answer_box = st.empty()
                sources_box = st.container()
                log_box = st.expander("Events", expanded=False)

                acc_answer = ""
                streamed_sources: list[dict] = []
                try:
                    for event in stream_search(
                        search_base_url,
                        query,
                        focus_mode,
                        optimization_mode,
                        system_instructions,
                    ):
                        etype = event.get("type")
                        edata = event.get("data")
                        with log_box:
                            st.code(json.dumps(event))

                        if etype == "sources" and isinstance(edata, list):
                            streamed_sources = edata
                            with sources_box:
                                st.subheader("Sources")
                                render_sources(streamed_sources)
                        elif etype == "response":
                            # In this simple protocol, the whole message arrives at once
                            chunk = edata or ""
                            acc_answer = str(chunk)
                            answer_box.write(acc_answer)
                        elif etype == "done":
                            break
                        else:
                            # init or unknown types
                            pass
                except httpx.HTTPStatusError as e:
                    st.error(f"HTTP error: {e.response.status_code} {e.response.text}")
                except Exception as e:
                    st.error(f"Stream error: {e}")

    # ==================== TAB 2: RESEARCH SERVICE ====================
    with tab2:
        with st.sidebar:
            st.header("Research Settings")
            research_base_url = st.text_input(
                "Research API Base URL",
                value="http://researchsvc:3002",
                help="e.g. http://localhost:3002",
            )
            st.divider()
            if st.button("Check Research Health"):
                try:
                    r = httpx.get(f"{research_base_url}/health")
                    r.raise_for_status()
                    st.success("Research service is healthy!")
                    st.code(json.dumps(r.json(), indent=2))
                except Exception as e:
                    st.error(f"Health check error: {e}")

        st.subheader("AI-Powered Research & Content Generation")
        st.info(
            "🤖 This service uses a multi-agent system (Research Analyst + Content Writer) to create comprehensive blog posts based on web research."
        )

        topic = st.text_area(
            "Research Topic",
            placeholder="e.g., The impact of AI on software development",
            height=100,
            help="Enter a topic you want the AI agents to research and write about",
        )

        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.1,
            help="Controls creativity: 0.0 = focused/deterministic, 1.0 = creative/diverse",
        )

        col1, col2 = st.columns([1, 3])
        with col1:
            generate = st.button("Generate Content", type="primary")
        with col2:
            st.write("")

        st.divider()

        if generate:
            if not topic.strip():
                st.warning("Please enter a research topic.")
            else:
                with st.spinner(
                    "🔍 Researching and writing... This may take 1-2 minutes..."
                ):
                    try:
                        response = post_generate_content(
                            research_base_url, topic, temperature
                        )
                        if response.status_code >= 400:
                            st.error(f"Error {response.status_code}: {response.text}")
                        else:
                            data = response.json()

                            st.success("✅ Content generated successfully!")

                            # Display topic
                            st.subheader("📌 Topic")
                            st.write(data.get("topic", ""))

                            # Display generated content
                            st.subheader("📝 Generated Content")
                            content = data.get("content", "")
                            if content:
                                st.markdown(content)
                            else:
                                st.warning("No content was generated.")

                            # Display status if available
                            if data.get("status"):
                                st.caption(f"Status: {data['status']}")

                            # Show raw JSON in expander
                            with st.expander("📄 View Raw JSON Response"):
                                st.json(data)
                    except httpx.TimeoutException:
                        st.error(
                            "⏱️ Request timed out. The research process may take longer. Try increasing the timeout or check the service logs."
                        )
                    except Exception as e:
                        st.error(f"❌ Request error: {e}")


if __name__ == "__main__":
    main()
