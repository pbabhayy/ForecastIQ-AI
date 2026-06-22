"""
Page: Ask ForecastIQ
====================
RAG-augmented chat about the loaded dataset (Groq → Ollama).
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from ai import chat_engine
from components import empty_states, error_states, theme
from components.sidebar import render_sidebar
from utils import session_manager
from utils.logger import get_logger

logger = get_logger(__name__)


def _bootstrap() -> None:
    theme.configure_page("Ask ForecastIQ")
    session_manager.init_session_state()
    theme.inject_premium_css()
    render_sidebar(active_page="chat")


def _dataset_key() -> str | None:
    uploaded = session_manager.get_state(session_manager.UPLOADED_FILE) or {}
    if not uploaded.get("name"):
        return None
    return f"{uploaded.get('name')}:{uploaded.get('size_bytes')}"


def _ensure_chat_history() -> list[dict[str, str]]:
    key = _dataset_key()
    stored_key = session_manager.get_state(session_manager.CHAT_DATASET_KEY)
    history = session_manager.get_state(session_manager.CHAT_HISTORY)
    if key != stored_key:
        history = []
        session_manager.update_state(
            {session_manager.CHAT_HISTORY: history, session_manager.CHAT_DATASET_KEY: key}
        )
    return list(history or [])


def _persist_history(history: list[dict[str, str]]) -> None:
    session_manager.set_state(session_manager.CHAT_HISTORY, history)


def _render_messages(history: list[dict[str, str]]) -> None:
    for msg in history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def main() -> None:
    _bootstrap()
    theme.page_header(
        "Ask ForecastIQ",
        "Chat with your data — answers grounded in your uploaded dataset.",
        eyebrow="Chat",
    )

    if not session_manager.is_data_loaded():
        empty_states.show_no_data()
        return

    if not chat_engine.chat_available():
        error_states.show_warning(
            "Configure Groq (GROQ_API_KEY) or start Ollama to use chat. "
            "The rule-based engine does not support conversational Q&A.",
            title="Chat unavailable",
        )
        return

    dataset_id = session_manager.get_state(session_manager.DATASET_ID)
    history = _ensure_chat_history()
    _render_messages(history)

    prompt = st.chat_input("Ask about revenue, forecasts, risks, or recommendations…")
    if not prompt:
        return

    history.append({"role": "user", "content": prompt})
    _persist_history(history)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Searching context and composing answer…"):
                reply, provider = chat_engine.generate_chat_reply(
                    prompt, history[:-1], dataset_id=dataset_id
                )
            st.caption(f"via {provider}")
            st.write_stream(chat_engine.stream_reply_text(reply))
            history.append({"role": "assistant", "content": reply})
            _persist_history(history)
        except RuntimeError as exc:
            error_states.show_error(str(exc), title="Chat failed")
        except Exception:
            logger.exception("Chat error")
            error_states.show_error("Something went wrong generating a reply.", title="Chat failed")


if __name__ == "__main__":
    main()
