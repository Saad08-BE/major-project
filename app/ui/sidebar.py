"""Sidebar navigation with New Chat, Searchable History, and Fixed Bottom Settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import streamlit as st

from app.config.settings import AppSettings
from app.ui.chat_state import ChatSession, get_current_session


def render_sidebar_navigation(st_module, settings: AppSettings) -> dict[str, bool]:
    """Render the full left sidebar navigation."""
    actions = {
        "new_chat_clicked": False,
        "settings_clicked": False,
    }

    # 1. Top Section: New Chat Button
    st_module.sidebar.title("🩺 HealthAI Local")
    if st_module.sidebar.button("➕ New Chat", use_container_width=True, type="primary"):
        new_sess = ChatSession.create_new()
        st_module.session_state.sessions[new_sess.session_id] = new_sess
        st_module.session_state.active_session_id = new_sess.session_id
        st_module.session_state.temp_mode = False
        st_module.rerun()

    st_module.sidebar.divider()

    # 2. Middle Section: Searchable Chat History
    st_module.sidebar.subheader("🕒 Recent Consultations")

    search_query = st_module.sidebar.text_input(
        "Search history...",
        placeholder="🔍 Search past consultations",
        label_visibility="collapsed",
        key="search_chat_history",
    ).strip().lower()

    # Filter non-temporary sessions
    sessions: dict[str, ChatSession] = st_module.session_state.sessions
    matching_sessions = []

    for sid, s in sorted(sessions.items(), key=lambda item: item[1].created_at, reverse=True):
        if s.is_temporary:
            continue
        # Check title or message content match
        if not search_query:
            matching_sessions.append((sid, s))
        else:
            title_match = search_query in s.title.lower()
            msg_match = any(search_query in m.get("content", "").lower() for m in s.messages)
            if title_match or msg_match:
                matching_sessions.append((sid, s))

    if not matching_sessions:
        if search_query:
            st_module.sidebar.caption("No matching consultations found.")
        else:
            st_module.sidebar.caption("No past consultations yet.")
    else:
        for sid, s in matching_sessions:
            is_active = (sid == st_module.session_state.active_session_id and not st_module.session_state.temp_mode)
            btn_label = f"{'👉 ' if is_active else '💬 '}{s.title}"
            if st_module.sidebar.button(btn_label, key=f"session_btn_{sid}", use_container_width=True):
                st_module.session_state.active_session_id = sid
                st_module.session_state.temp_mode = False
                st_module.rerun()

    # 3. Bottom Section: Fixed Settings Icon Button
    st_module.sidebar.divider()
    if st_module.sidebar.button("⚙️ Settings & System Status", use_container_width=True, key="btn_open_settings"):
        st_module.session_state.show_settings_dialog = True
        st_module.rerun()

    return actions
