import os
import json
import subprocess
import re
from typing import Iterator, Optional, Dict, List, Tuple

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
    # Increase timeout to 5 minutes (300s) as CrewAI research can take time
    return httpx.post(url, json=payload, timeout=300)


def run_pytest_tests(test_path: str, verbose: bool = True) -> Tuple[int, str, str]:
    """
    Run pytest tests and return exit code, stdout, and stderr.

    Args:
        test_path: Path to test file or directory
        verbose: Whether to run with verbose output

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        cmd = ["python", "-m", "pytest", test_path]
        if verbose:
            cmd.append("-v")
        cmd.extend(["--tb=short", "--no-header"])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Test execution timed out (5 minutes)"
    except Exception as e:
        return 1, "", str(e)


def parse_pytest_output(output: str) -> List[Dict]:
    """
    Parse pytest output to extract individual test results.

    Args:
        output: Raw pytest output

    Returns:
        List of test results with status, name, and duration
    """
    tests = []

    # Pattern to match test results: "tests/path/to/test.py::test_name PASSED [50%]"
    pattern = r'(tests/[^\s]+::[^\s]+)\s+(PASSED|FAILED|SKIPPED|ERROR)\s+\[\s*(\d+)%\]'

    for match in re.finditer(pattern, output):
        test_name = match.group(1)
        status = match.group(2)

        # Extract duration if available
        duration = ""
        duration_pattern = rf'{re.escape(test_name)}.*?{status}\s+\[\s*\d+%\]\s+(\d+\.\d+s)'
        duration_match = re.search(duration_pattern, output)
        if duration_match:
            duration = duration_match.group(1)

        tests.append({
            "name": test_name,
            "status": status,
            "duration": duration,
        })

    return tests


def get_test_files(base_path: str = ".") -> Dict[str, str]:
    """Get available test files with descriptions."""
    return {
        "Phase 1: crawl4ai Integration": "tests/unit/test_crawl_wrapper.py",
        "Phase 1: Fallback BeautifulSoup": "tests/unit/test_crawl_fallback.py",
        "Phase 2a: Models & Decomposition": "tests/unit/test_models_decomposition.py",
        "Phase 2a: Query Decomposition": "tests/unit/test_query_decomposition.py",
        "Phase 2b-c: Result Aggregator": "tests/unit/test_result_aggregator.py",
        "Phase 2b-c: Parallel Search": "tests/unit/test_parallel_search.py",
        "Phase 2d-e: Multi-Query Reranking": "tests/unit/test_multi_query_reranking.py",
        "Phase 2d-e: Synthesis Enhancement": "tests/unit/test_synthesis_enhancement.py",
        "Phase 3: Caching": "tests/unit/test_caching.py",
        "Phase 4: E2E Integration": "tests/integration/test_e2e_integration.py",
        "All Unit Tests": "tests/unit/",
        "All Tests": "tests/",
    }


def main():
    st.set_page_config(page_title="API Tester", layout="wide")
    st.title("Simple Perplexica API Tester")
    st.caption("Test search and research services")

    # Create tabs for different services
    tab1, tab2, tab3 = st.tabs(["🔍 Search Service", "📝 Research Service", "🧪 Test Runner"])

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

        with st.expander("ℹ️ How it works", expanded=False):
            st.markdown("""
            **Multi-Agent Research System:**
            
            1. 🔍 **Research Analyst Agent** - Conducts comprehensive web research using SerperDev
               - Searches for recent developments and news
               - Analyzes industry trends and expert opinions
               - Gathers statistical data and market insights
               - Verifies sources and fact-checks information
               
            2. ✍️ **Content Writer Agent** - Transforms research into engaging content
               - Creates well-structured blog posts
               - Maintains factual accuracy with citations
               - Formats content with proper markdown
               - Includes hyperlinked references
               
            **Typical Process Time:** 2-4 minutes
            
            **Note:** The agents make multiple web searches and LLM calls, which takes time but produces high-quality, well-researched content.
            """)

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
                    "🔍 Researching and writing... This typically takes 2-4 minutes. The AI agents are searching the web, analyzing sources, and crafting your content..."
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

    # ==================== TAB 3: TEST RUNNER ====================
    with tab3:
        st.subheader("🧪 Test Suite Runner")

        with st.expander("ℹ️ About Tests", expanded=True):
            st.markdown("""
            **Comprehensive Test Suite:** 137 tests across 4 phases

            - **Phase 1:** crawl4ai integration & fallback (32 tests)
            - **Phase 2a:** Query decomposition models (29 tests)
            - **Phase 2b-c:** Result aggregation & parallel search (24 tests)
            - **Phase 2d-e:** Reranking & synthesis (25 tests)
            - **Phase 3:** Caching enhancements (12 tests)
            - **Phase 4:** End-to-end integration (15 tests)

            Each test can be run individually or in groups. Results will show detailed status for each test.
            """)

        col1, col2 = st.columns([2, 1])

        with col1:
            test_files = get_test_files()
            selected_test = st.selectbox(
                "Select Tests to Run",
                options=list(test_files.keys()),
                index=10,  # Default to "All Unit Tests"
            )

        with col2:
            run_verbose = st.checkbox("Verbose Output", value=True)

        st.divider()

        # Run button
        if st.button("▶️ Run Tests", type="primary", use_container_width=True):
            test_path = test_files[selected_test]

            with st.spinner(f"Running {selected_test}..."):
                exit_code, stdout, stderr = run_pytest_tests(test_path, verbose=run_verbose)

            st.divider()

            # Display summary
            if exit_code == 0:
                st.success(f"✅ All tests passed!")
            else:
                st.error(f"❌ Some tests failed (exit code: {exit_code})")

            # Parse and display individual test results
            tests = parse_pytest_output(stdout)

            if tests:
                st.subheader(f"Test Results ({len(tests)} tests)")

                # Create columns for better layout
                col_name, col_status, col_duration = st.columns([3, 1, 1])

                with col_name:
                    st.markdown("**Test Name**")
                with col_status:
                    st.markdown("**Status**")
                with col_duration:
                    st.markdown("**Duration**")

                st.divider()

                # Display each test
                for test in tests:
                    col_name, col_status, col_duration = st.columns([3, 1, 1])

                    with col_name:
                        st.code(test["name"], language="text")

                    with col_status:
                        status = test["status"]
                        if status == "PASSED":
                            st.success("✅ PASSED")
                        elif status == "FAILED":
                            st.error("❌ FAILED")
                        elif status == "SKIPPED":
                            st.warning("⏭️ SKIPPED")
                        else:
                            st.info(f"ℹ️ {status}")

                    with col_duration:
                        if test["duration"]:
                            st.caption(test["duration"])

            # Show summary statistics
            if tests:
                st.divider()

                passed = sum(1 for t in tests if t["status"] == "PASSED")
                failed = sum(1 for t in tests if t["status"] == "FAILED")
                skipped = sum(1 for t in tests if t["status"] == "SKIPPED")

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Total Tests", len(tests))
                with col2:
                    st.metric("Passed ✅", passed)
                with col3:
                    st.metric("Failed ❌", failed)
                with col4:
                    st.metric("Skipped ⏭️", skipped)

            # Show detailed output in expanders
            if stdout:
                with st.expander("📋 Full pytest Output"):
                    st.code(stdout, language="text")

            if stderr:
                with st.expander("⚠️ Error Output"):
                    st.code(stderr, language="text")


if __name__ == "__main__":
    main()
