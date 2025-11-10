import os
from typing import List

import streamlit as st

# Reuse core logic from existing script
from sistani_rag import (
    load_index,
    search_similar,
    generate_answer,
    INDEX_FILE,
    CHUNKS_FILE,
    TOP_K as DEFAULT_TOP_K,
)


def ensure_index_available() -> bool:
    if os.path.exists(INDEX_FILE) and os.path.exists(CHUNKS_FILE):
        return True
    return False


@st.cache_resource(show_spinner=False)
def cached_load_index():
    return load_index()


def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []  # list of dicts: {role, content, sources}
    # minimal state only for messages


def render_header():
    st.markdown(
        """
        <style>
        .title-center {text-align:center}
        .subtitle-center {text-align:center; color:white}
        .source-chip {display:inline-block; padding:4px 8px; margin:2px; border-radius:12px; background:#E8F5E9; color:#185A37; font-size:12px;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<h2 class='title-center'>🕌 Islamic Knowledge Chatbot</h2>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle-center'>Ask questions based on Ayatullah al-Sistani's rulings and references.</p>",
        unsafe_allow_html=True,
    )


def render_messages():
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            sources: List[str] = msg.get("sources", [])
            if sources:
                uniq_sources = []
                for s in sources:
                    if s not in uniq_sources:
                        uniq_sources.append(s)
                st.markdown("**Sources:** ")
                st.markdown(" ".join([f"<span class='source-chip'>{s}</span>" for s in uniq_sources]), unsafe_allow_html=True)


def answer_question(user_question: str):
    # Lazy-load index
    index, chunks, sources = cached_load_index()

    # Retrieve chunks
    top_chunks = search_similar(user_question, index, chunks, sources, k=DEFAULT_TOP_K)

    answer = generate_answer(top_chunks, user_question)

    used_sources = [src for _, src in top_chunks]
    return answer, used_sources


def main():
    st.set_page_config(page_title="Islamic Knowledge Chatbot", page_icon="🕌", layout="wide")
    init_session_state()
    render_header()

    index_ready = ensure_index_available()
    if not index_ready:
        st.info("No index found. From a terminal, run: python sistani_rag.py --build")
        return

    # Chat history
    render_messages()

    if prompt := st.chat_input("Ask about rulings, worship, jurisprudence..."):
        # Show the user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    reply, srcs = answer_question(prompt)
                except Exception as e:
                    st.error(f"Error generating answer: {e}")
                    return
                st.markdown(reply)
                if srcs:
                    uniq_sources = []
                    for s in srcs:
                        if s not in uniq_sources:
                            uniq_sources.append(s)
                    st.markdown("**Sources:** ")
                    st.markdown(" ".join([f"<span class='source-chip'>{s}</span>" for s in uniq_sources]), unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": reply, "sources": srcs})


if __name__ == "__main__":
    main()


