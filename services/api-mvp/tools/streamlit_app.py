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
    system_instructions: Optional[str],
    stream: bool,
):
    url = f"{base_url}/api/search"
    payload = {
        "query": query,
        "focusMode": focus_mode,
        "stream": stream,
    }
    if system_instructions:
        payload["systemInstructions"] = system_instructions

    return httpx.post(url, json=payload, timeout=60)


def stream_search(
    base_url: str,
    query: str,
    focus_mode: str,
    system_instructions: Optional[str],
) -> Iterator[dict]:
    url = f"{base_url}/api/search"
    payload = {
        "query": query,
        "focusMode": focus_mode,
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


def main():
    st.set_page_config(page_title="API MVP Tester", layout="wide")
    st.title("Vetuku API Tester (Streamlit)")
    st.caption("Test /api/search with streaming and non-streaming modes")

    with st.sidebar:
        st.header("Settings")
        base_url = st.text_input(
            "API Base URL", value=get_api_base_url(), help="e.g. http://localhost:3001"
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
        use_stream = st.toggle("Stream results", value=False)
        st.divider()
        if st.button("Check Providers"):
            try:
                r = httpx.get(f"{base_url}/api/providers")
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
            return

        if not use_stream:
            with st.spinner("Requesting…"):
                try:
                    r = post_search(
                        base_url, query, focus_mode, system_instructions, stream=False
                    )
                    if r.status_code >= 400:
                        st.error(f"Error {r.status_code}: {r.text}")
                        return
                    data = r.json()
                except Exception as e:
                    st.error(f"Request error: {e}")
                    return

            st.subheader("Answer")
            st.write(data.get("message", ""))
            st.subheader("Sources")
            render_sources(data.get("sources") or [])
            return

        # Streaming mode
        st.subheader("Answer (streaming)")
        answer_box = st.empty()
        sources_box = st.container()
        log_box = st.expander("Events", expanded=False)

        acc_answer = ""
        streamed_sources: list[dict] = []
        try:
            for event in stream_search(
                base_url, query, focus_mode, system_instructions
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


if __name__ == "__main__":
    main()
