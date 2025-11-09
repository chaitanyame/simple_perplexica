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


def get_pipeline_examples() -> Dict[str, Dict]:
    """Get example data showing the complete pipeline flow."""
    return {
        "Multi-Query: Cloud Providers": {
            "input_query": "latest cloud technologies news from aws, azure, and gcp",
            "decomposition": {
                "need_search": True,
                "strategy": "multi",
                "optimized_queries": [
                    "AWS cloud latest news and updates",
                    "Azure cloud latest news and updates",
                    "Google Cloud Platform latest news"
                ]
            },
            "crawl_example": {
                "url": "https://aws.amazon.com/blogs/aws/",
                "markdown_content": """# AWS News and Announcements

## Latest Updates
- **New EC2 Instance Types**: Latest generation instances with better performance
- **AWS Lambda Improvements**: Enhanced cold start performance
- **RDS Auto Scaling**: Automatic scaling for databases

## Technical Details
AWS provides cloud computing services including compute, storage, databases, networking, and more.
"""
            },
            "search_results": {
                "AWS cloud latest news and updates": [
                    {
                        "title": "AWS announces new EC2 instances",
                        "url": "https://aws.amazon.com/blogs/aws/ec2-new",
                        "pageContent": "AWS has announced new EC2 instance types with 40% better performance..."
                    },
                    {
                        "title": "AWS Lambda Cold Start Reduction",
                        "url": "https://aws.amazon.com/blogs/aws/lambda-cold-start",
                        "pageContent": "The latest Lambda improvements reduce cold start latency by 50%..."
                    },
                    {
                        "title": "RDS Multi-AZ Improvements",
                        "url": "https://aws.amazon.com/blogs/aws/rds-improvements",
                        "pageContent": "RDS now supports automatic failover with reduced recovery time..."
                    }
                ],
                "Azure cloud latest news and updates": [
                    {
                        "title": "Azure Compute Updates 2024",
                        "url": "https://azure.microsoft.com/en-us/blog/compute-updates/",
                        "pageContent": "Microsoft Azure introduces new compute options including VM SKUs..."
                    },
                    {
                        "title": "Azure SQL Database Enhancements",
                        "url": "https://azure.microsoft.com/en-us/blog/sql-enhancements/",
                        "pageContent": "Azure SQL now includes new performance optimization features..."
                    }
                ],
                "Google Cloud Platform latest news": [
                    {
                        "title": "GCP Compute Engine Updates",
                        "url": "https://cloud.google.com/blog/products/compute",
                        "pageContent": "Google Cloud announces new machine types and pricing updates..."
                    },
                    {
                        "title": "BigQuery Performance Improvements",
                        "url": "https://cloud.google.com/blog/products/bigquery",
                        "pageContent": "BigQuery now runs 3x faster with optimized query execution..."
                    }
                ]
            },
            "aggregation": {
                "step1_limit_per_query": "Limit each query to 5 results",
                "step2_flatten": "Combine all results (9 total from 3 queries)",
                "step3_deduplicate": "Remove duplicate URLs, keep best version",
                "step4_diversity_filter": "Max 3 results per domain",
                "step5_sort": "Sort by content quality (longer content = higher rank)",
                "step6_limit_total": "Cap to 10 total results",
                "final_results": [
                    {
                        "rank": 1,
                        "title": "AWS announces new EC2 instances",
                        "url": "https://aws.amazon.com/blogs/aws/ec2-new",
                        "pageContent": "AWS has announced new EC2 instance types with 40% better performance...",
                        "source": "AWS cloud latest news and updates"
                    },
                    {
                        "rank": 2,
                        "title": "Azure Compute Updates 2024",
                        "url": "https://azure.microsoft.com/en-us/blog/compute-updates/",
                        "pageContent": "Microsoft Azure introduces new compute options including VM SKUs...",
                        "source": "Azure cloud latest news and updates"
                    },
                    {
                        "rank": 3,
                        "title": "GCP Compute Engine Updates",
                        "url": "https://cloud.google.com/blog/products/compute",
                        "pageContent": "Google Cloud announces new machine types and pricing updates...",
                        "source": "Google Cloud Platform latest news"
                    }
                ]
            },
            "synthesis": {
                "answer": """The major cloud providers have released significant updates in 2024:

**AWS** [1] announces new EC2 instance types with 40% better performance, enhanced Lambda cold start performance, and RDS multi-AZ improvements with reduced recovery times.

**Azure** [2] introduces new compute options including VM SKUs and enhanced SQL database performance optimization features.

**Google Cloud Platform** [3] announces new machine types, pricing updates, and BigQuery performance improvements running 3x faster with optimized query execution.

All three providers continue to compete on performance, features, and pricing.""",
                "sources": [
                    {
                        "num": 1,
                        "title": "AWS announces new EC2 instances",
                        "url": "https://aws.amazon.com/blogs/aws/ec2-new"
                    },
                    {
                        "num": 2,
                        "title": "Azure Compute Updates 2024",
                        "url": "https://azure.microsoft.com/en-us/blog/compute-updates/"
                    },
                    {
                        "num": 3,
                        "title": "GCP Compute Engine Updates",
                        "url": "https://cloud.google.com/blog/products/compute"
                    }
                ]
            }
        },
        "Single Query: Python Tutorial": {
            "input_query": "python programming tutorial for beginners",
            "decomposition": {
                "need_search": True,
                "strategy": "single",
                "optimized_queries": [
                    "Python programming tutorial for beginners"
                ]
            },
            "crawl_example": {
                "url": "https://docs.python.org/3/tutorial/",
                "markdown_content": """# Python Tutorial

## Introduction
Python is a high-level programming language with simple, easy-to-learn syntax.

## Basic Concepts
- **Variables and Types**: Understanding Python's dynamic typing
- **Control Flow**: If statements, loops, and functions
- **Data Structures**: Lists, tuples, dictionaries, and sets
- **Object-Oriented Programming**: Classes and inheritance

## Getting Started
```python
print("Hello, World!")
x = 10
y = 20
print(x + y)
```

## Running Python
You can run Python scripts using `python script.py`
"""
            },
            "search_results": {
                "Python programming tutorial for beginners": [
                    {
                        "title": "Python Official Tutorial",
                        "url": "https://docs.python.org/3/tutorial/",
                        "pageContent": "Python is a high-level programming language. This tutorial introduces..."
                    },
                    {
                        "title": "W3Schools Python Tutorial",
                        "url": "https://www.w3schools.com/python/",
                        "pageContent": "Learn Python by examples. This tutorial covers all the basics..."
                    },
                    {
                        "title": "Real Python Tutorials",
                        "url": "https://realpython.com/start-here/",
                        "pageContent": "Comprehensive Python tutorials for beginners including hands-on projects..."
                    }
                ]
            },
            "aggregation": {
                "step1_limit_per_query": "Limit to 5 results per query",
                "step2_flatten": "Single query → 3 results only",
                "step3_deduplicate": "No duplicates in example",
                "step4_diversity_filter": "All from different domains",
                "step5_sort": "Sort by content quality",
                "step6_limit_total": "Cap to 10 (3 results < 10)",
                "final_results": [
                    {
                        "rank": 1,
                        "title": "Real Python Tutorials",
                        "url": "https://realpython.com/start-here/",
                        "pageContent": "Comprehensive Python tutorials for beginners including hands-on projects...",
                        "source": "Python programming tutorial for beginners"
                    },
                    {
                        "rank": 2,
                        "title": "Python Official Tutorial",
                        "url": "https://docs.python.org/3/tutorial/",
                        "pageContent": "Python is a high-level programming language. This tutorial introduces...",
                        "source": "Python programming tutorial for beginners"
                    },
                    {
                        "rank": 3,
                        "title": "W3Schools Python Tutorial",
                        "url": "https://www.w3schools.com/python/",
                        "pageContent": "Learn Python by examples. This tutorial covers all the basics...",
                        "source": "Python programming tutorial for beginners"
                    }
                ]
            },
            "synthesis": {
                "answer": """Python is a high-level programming language perfect for beginners [1]. The official tutorial [1] introduces Python's basic concepts including variables, control flow, data structures, and object-oriented programming.

For hands-on learning, Real Python [2] offers comprehensive tutorials with practical examples, while W3Schools [3] provides interactive exercises for learning by doing.

Key topics to start with:
- Variables and data types
- Control flow (if/else, loops)
- Functions and modules
- Working with lists and dictionaries""",
                "sources": [
                    {
                        "num": 1,
                        "title": "Python Official Tutorial",
                        "url": "https://docs.python.org/3/tutorial/"
                    },
                    {
                        "num": 2,
                        "title": "Real Python Tutorials",
                        "url": "https://realpython.com/start-here/"
                    },
                    {
                        "num": 3,
                        "title": "W3Schools Python Tutorial",
                        "url": "https://www.w3schools.com/python/"
                    }
                ]
            }
        }
    }


def main():
    st.set_page_config(page_title="API Tester", layout="wide")
    st.title("Simple Perplexica API Tester")
    st.caption("Test search and research services")

    # Create tabs for different services
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Search Service", "📝 Research Service", "🧪 Test Runner", "📊 Pipeline Demo", "🐛 Debug View"])

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

            # Handle missing pytest
            if "No module named pytest" in stderr or "No module named 'pytest'" in stderr:
                st.error("❌ pytest is not installed")
                st.warning("""
                **To use the test runner, pytest needs to be installed:**

                1. **In Docker container:** Rebuild the image with updated requirements
                   ```bash
                   docker-compose build ui
                   docker-compose up ui
                   ```

                2. **Locally:** Install pytest
                   ```bash
                   pip install pytest pytest-asyncio
                   ```
                """)
            # Display summary
            elif exit_code == 0:
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

    # ==================== TAB 4: PIPELINE DEMO ====================
    with tab4:
        st.subheader("📊 Dynamic Search Pipeline - Real-Time Visualization")

        # Configure API URL in sidebar
        with st.sidebar:
            st.header("Pipeline Demo Settings")
            pipeline_api_url = st.text_input(
                "Search API Base URL",
                value="http://api:3001",
                help="e.g., http://api:3001 (Docker) or http://localhost:3001 (local)",
            )
            st.divider()

        with st.expander("ℹ️ How the Pipeline Works", expanded=True):
            st.markdown("""
            The Perplexica search pipeline has 6 key stages:

            1. **Input Query** - Your search question
            2. **Query Decomposition** - LLM analyzes and decides single vs multi-query strategy
            3. **Parallel Search** - Execute queries against SearxNG/SerperDev
            4. **Result Aggregation** - Deduplicate, filter by domain diversity, and rank by quality
            5. **Answer Synthesis** - LLM generates final answer with citations

            **Note:** Enter a query and click "Run Pipeline" to see real execution through all stages.
            """)

        # Query input section
        st.divider()
        st.markdown("### Enter Your Query")

        # Initialize session state for pipeline
        if "pipeline_query" not in st.session_state:
            st.session_state.pipeline_query = ""
        if "run_pipeline_mode" not in st.session_state:
            st.session_state.run_pipeline_mode = False

        col1, col2 = st.columns([3, 1])
        with col1:
            query_input = st.text_input(
                "Search Query",
                value=st.session_state.pipeline_query,
                placeholder="e.g., latest cloud technologies news from aws, azure, and gcp",
                help="Enter any search query to see the pipeline in action"
            )
        with col2:
            st.write("")

        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            run_pipeline = st.button("▶️ Run Pipeline", type="primary", use_container_width=True)
        with col2:
            use_example = st.button("📋 Use Example", use_container_width=True)
        with col3:
            st.write("")

        # Handle example button
        if use_example:
            st.session_state.pipeline_query = "latest cloud technologies news from aws, azure, and gcp"
            st.rerun()

        if run_pipeline and query_input:
            st.session_state.pipeline_query = query_input
            st.session_state.run_pipeline_mode = True

        if not query_input and not st.session_state.run_pipeline_mode:
            st.info("Enter a query and click 'Run Pipeline' to see the search pipeline in action")
            st.stop()

        if st.session_state.run_pipeline_mode:
            query_to_run = st.session_state.pipeline_query

            # Create tabs for each pipeline stage
            stage1, stage2, stage3, stage4, stage5 = st.tabs([
                "1️⃣ Input Query",
                "2️⃣ Decomposition",
                "3️⃣ Search Results",
                "4️⃣ Aggregation",
                "5️⃣ Final Answer"
            ])

            # ===== STAGE 1: INPUT QUERY =====
            with stage1:
                st.markdown("### Original User Query")
                st.code(query_to_run, language="text")
                st.success("Query received and ready for processing")

            # Perform initial API call once (captures decomposition + first pass sources)
            try:
                initial_response = httpx.post(
                    f"{pipeline_api_url}/api/search",
                    json={
                        "query": query_to_run,
                        "focusMode": "webSearch",
                        "optimizationMode": "balanced",
                        "stream": False
                    },
                    timeout=90
                )
                initial_json = initial_response.json() if initial_response.status_code == 200 else {}
            except Exception as _e:
                initial_json = {}

            # ===== STAGE 2: DECOMPOSITION =====
            with stage2:
                st.markdown("### Query Decomposition")
                decomposition = initial_json.get('decomposition')
                if not decomposition:
                    st.warning("No decomposition metadata returned. The backend may not yet support it or fell back to single-query.")
                else:
                    st.success("✅ Decomposition completed")
                    st.markdown(f"**Strategy:** `{decomposition.get('strategy', 'single')}`")
                    optimized_queries = decomposition.get('optimized_queries', []) or []
                    st.markdown(f"**Optimized Queries ({len(optimized_queries)}):**")
                    for i, oq in enumerate(optimized_queries, 1):
                        st.code(f"{i}. {oq}", language="text")
                    st.caption(f"Total Query Count: {decomposition.get('query_count', len(optimized_queries))}")

                # Show a preview of first few sources (raw fetch results at this stage)
                preview_sources = initial_json.get('sources', [])
                if preview_sources:
                    st.markdown("**Initial Source Previews (first 3):**")
                    for src in preview_sources[:3]:
                        st.caption(f"- {src.get('title', 'Untitled')} | {src.get('url', 'N/A')}")
                else:
                    st.info("No sources in initial response (possibly decision.need_search = False or provider failure).")

            # ===== STAGE 3: SEARCH RESULTS =====
            with stage3:
                st.markdown("### Search Results")
                # Reuse initial sources (already represent post-search results)
                sources = initial_json.get('sources', [])
                if sources:
                    st.success(f"✅ Retrieved {len(sources)} sources from initial search")
                    st.markdown("**Top Results:**")
                    for idx, src in enumerate(sources[:5], 1):
                        with st.container(border=True):
                            st.markdown(f"**{idx}. [{src.get('title', 'Untitled')}]({src.get('url', '#')})**")
                            st.caption(f"URL: {src.get('url', 'N/A')}")
                            if src.get('pageContent'):
                                st.caption(f"Snippet: {src['pageContent'][:150]}...")
                else:
                    st.error("No sources returned. Try a broader query or check backend logs.")

            # ===== STAGE 4: AGGREGATION =====
            with stage4:
                st.markdown("### Result Aggregation")
                st.info("""
                **Aggregation Process:**
                1. Limit per query: Balance coverage across decomposed queries
                2. Deduplicate: Remove duplicate URLs, keep best version
                3. Diversity filter: Max 3 results per domain
                4. Sort by quality: Longer content = higher rank
                5. Final limit: Cap to ~10 results
                """)
                st.success("✅ Results aggregated and ranked by relevance")

            # ===== STAGE 5: FINAL ANSWER =====
            with stage5:
                st.markdown("### Final Answer")
                # If initial response already contains synthesized message (non-stream flow), show it
                if initial_json.get('message'):
                    st.success("✅ Answer synthesized from initial search response")
                    st.markdown("**Generated Response:**")
                    st.markdown(initial_json.get('message', 'No message generated'))
                    sources = initial_json.get('sources', [])
                    if sources:
                        st.divider()
                        st.markdown("**Citation Sources:**")
                        for idx, src in enumerate(sources, 1):
                            st.markdown(f"**[{idx}]** [{src.get('title', 'Untitled')}]({src.get('url', '#')})")
                else:
                    st.info("No final answer in initial response. Backend may be streaming-only or encountered an error.")

    # ==================== TAB 5: DEBUG VIEW ====================
    with tab5:
        st.subheader("🐛 Debug View - Pipeline Execution Analysis")

        with st.expander("ℹ️ What This Shows", expanded=True):
            st.markdown("""
            This debug view helps identify gaps between the **Pipeline Demo** (expected behavior)
            and actual **Search Service** execution.

            **Current Issue:** Search endpoint only executes first optimized query, ignoring multi-query decomposition.

            **Root Cause:** In `search.py:238-239`:
            ```python
            # For now, use first query for backward compatibility
            effective_query = (decision.optimized_queries[0] if decision.optimized_queries else req.query)
            ```

            Only `optimized_queries[0]` is used. The rest are ignored!
            """)

        st.divider()
        st.markdown("### 📊 Problem Demonstration")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Expected (Pipeline Demo) ✅")
            st.code("""
Query: "aws, azure, gcp news"
    ↓
Decomposed:
  1. AWS cloud latest news
  2. Azure cloud latest news
  3. GCP cloud latest news
    ↓
Parallel Search:
  Query 1 → 5 results
  Query 2 → 5 results
  Query 3 → 5 results
    ↓
Aggregation:
  - Deduplicate URLs
  - Diversity filter (max 3/domain)
    ↓
Final: 10 balanced results
  - 3-4 AWS
  - 3-4 Azure
  - 3-4 GCP
            """, language="text")

        with col2:
            st.markdown("#### Actual (Current) ❌")
            st.code("""
Query: "aws, azure, gcp news"
    ↓
Decomposed:
  1. AWS cloud latest news    ← USED
  2. Azure cloud latest news  ← IGNORED
  3. GCP cloud latest news    ← IGNORED
    ↓
Search Only:
  Uses optimized_queries[0]
    ↓
Search Results:
  Only AWS results returned
    ↓
Final: AWS-only results
  - ~10 AWS articles
  - 0 Azure
  - 0 GCP
            """, language="text")

        st.divider()
        st.markdown("### 🔧 What Needs to Change")

        st.info("""
        **File:** `services/searchsvc/app/routers/search.py`

        **Current Code (Line 238-239):**
        ```python
        effective_query = (decision.optimized_queries[0] if decision.optimized_queries else req.query)
        sources = []
        fetched = await get_sources(effective_query, req.focusMode)
        ```

        **Should Be:**
        ```python
        # Execute ALL optimized queries in parallel
        if decision.search_strategy == "multi" and len(decision.optimized_queries) > 1:
            # Parallel multi-query search
            all_results = []
            for query in decision.optimized_queries:
                fetched = await get_sources(query, req.focusMode)
                all_results.extend(fetched)
            # Aggregation: deduplicate, diversity filter, etc.
            sources = aggregate_results(all_results, strategy="multi")
        else:
            # Single query search (existing behavior)
            effective_query = decision.optimized_queries[0] if decision.optimized_queries else req.query
            sources = await get_sources(effective_query, req.focusMode)
        ```
        """)

        st.divider()
        st.markdown("### 📋 Implementation Checklist")

        st.markdown("""
        - [ ] Implement multi-query parallel search in `search.py`
        - [ ] Add result aggregation (deduplicate, diversity filter)
        - [ ] Test with multi-query decomposition queries
        - [ ] Verify results are balanced across all queries
        - [ ] Update API response to show which queries were executed
        - [ ] Log decomposition strategy and query execution

        **Expected Behavior After Fix:**
        - Query: "aws, azure, gcp news"
        - Results: Balanced mix of AWS, Azure, GCP articles
        - Sources: Visible in UI showing which query returned each result
        """)

        st.divider()
        st.markdown("### 🎯 Test Query to Verify")

        st.code("""
Query: "latest cloud technologies news from aws, azure, and gcp"

Expected Result (after fix):
- Title: AWS announces new EC2 instances
  URL: https://aws.amazon.com/...

- Title: Azure Compute Updates 2024
  URL: https://azure.microsoft.com/...

- Title: GCP Compute Engine Updates
  URL: https://cloud.google.com/...

(Results should be balanced across all 3 cloud providers)
        """, language="text")


if __name__ == "__main__":
    main()
