"""Local Streamlit entry point for the healthcare intelligence system with Gemini-styled UI."""

from __future__ import annotations

import streamlit as st

from app.config import AppSettings, SettingsError
from app.llm.rag_pipeline import HealthcareRAGPipeline, RAGResponse
from app.safety import healthcare_disclaimer
from app.ui.chat_state import get_current_session, initialize_session_state
from app.ui.evidence_viewer import render_evidence_panel
from app.ui.input_controls import render_input_controls
from app.ui.settings_dialog import render_settings_dialog
from app.ui.sidebar import render_sidebar_navigation
from app.ui.theme import apply_gemini_theme


@st.cache_resource(show_spinner="Initializing local healthcare intelligence engine...")
def get_pipeline(settings: AppSettings) -> HealthcareRAGPipeline:
    """Cache the loaded RAG pipeline across user interactions for instant responses."""
    return HealthcareRAGPipeline.initialize(settings)


def run() -> None:
    """Render the full local-only Streamlit healthcare RAG application in Gemini-inspired dark UI."""
    st.set_page_config(
        page_title="HealthAI",
        page_icon="✨",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 1. Apply Dark Gemini Aesthetic
    apply_gemini_theme(st)

    # 2. Configuration & Path Verification
    try:
        settings = AppSettings.from_environment()
        settings.paths.create_runtime_directories()
    except SettingsError as exc:
        st.error(f"Local configuration error: {exc}")
        st.stop()

    # 3. Session State Initialization
    initialize_session_state(st)

    # 4. Settings Dialog / Modal check
    if st.session_state.show_settings_dialog:
        with st.container():
            render_settings_dialog(st, settings)
            if st.button("✕ Close Settings", type="secondary"):
                st.session_state.show_settings_dialog = False
                st.rerun()
            st.divider()

    # 5. Left Sidebar Navigation (Matching screenshot: New Chat, Recent, User profile & ⚙️)
    render_sidebar_navigation(st, settings)

    # 6. Main Content Area
    current_session = get_current_session(st)

    # Top Status Bar
    top_col1, top_col2 = st.columns([6, 2])
    with top_col1:
        if st.session_state.temp_mode:
            st.markdown(
                '<span class="temp-pill">🔒 Incognito Consultation (Not saved)</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<span class="privacy-pill">🔒 100% Local Apple Silicon Architecture</span>',
                unsafe_allow_html=True,
            )
    with top_col2:
        st.markdown(
            f"<div style='text-align: right; color: #9aa0a6; font-size: 0.8rem;'>Model: <code>{settings.llm_model}</code></div>",
            unsafe_allow_html=True,
        )

    # 7. Hero Screen (If session is new and has no messages, show "Where should we start?")
    if not current_session.messages:
        st.markdown(
            """
            <div class="gemini-hero-container">
                <div class="gemini-hero-title">Where should we start?</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Quick Suggestion Cards (Clinical & Healthcare focused)
        sug_col1, sug_col2, sug_col3 = st.columns(3)
        with sug_col1:
            if st.button("🩺 Explain acute fever & cough home care", use_container_width=True):
                st.session_state.preset_prompt = "What supportive home care is advised for acute fever and cough?"
                st.rerun()
        with sug_col2:
            if st.button("📊 Common symptoms of Type 2 Diabetes", use_container_width=True):
                st.session_state.preset_prompt = "What are the common symptoms and treatment outcomes for Type 2 Diabetes?"
                st.rerun()
        with sug_col3:
            if st.button("📄 Check uploaded medical guidelines", use_container_width=True):
                st.session_state.preset_prompt = "What clinical guidelines are available in my uploaded documents?"
                st.rerun()

        st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    else:
        # Render Conversation Message Thread
        for msg in current_session.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if "response" in msg and msg["response"] is not None:
                    render_evidence_panel(st, msg["response"])

    # 8. Action Bar above Chat Input (➕ PDF, Model Selector, Incognito toggle)
    selected_model, is_temp = render_input_controls(st, settings)

    # 9. Floating Chat Input Bar (Gemini-style)
    preset_query = st.session_state.pop("preset_prompt", None)
    user_query = st.chat_input("Ask a healthcare question or inquire about medical PDFs...")

    query_to_run = user_query or preset_query

    if query_to_run:
        # Append user message
        current_session.add_message(role="user", content=query_to_run)
        with st.chat_message("user"):
            st.markdown(query_to_run)

        # Run pipeline with preferred model override
        pipeline = get_pipeline(settings)
        with st.chat_message("assistant"):
            with st.spinner(f"Consulting local clinical evidence using `{selected_model}`..."):
                response: RAGResponse = pipeline.answer_question(
                    query_to_run,
                    model_override=selected_model,
                )

            # Urgent notice
            if response.urgent_warning:
                st.warning("⚠️ **Urgent Medical Notice**: Emergency symptoms detected. Seek immediate emergency medical care.")

            # Display answer
            st.markdown(response.answer)

            # Metadata footer
            mode_badge = f"🟢 Local LLM ({response.llm_model})" if not response.is_offline_fallback else "🟡 Offline Evidence Synthesis"
            st.caption(
                f"⏱️ Latency: `{response.total_latency_seconds:.2f}s` | "
                f"Mode: {mode_badge} | "
                f"Citations: `{len(response.document_sources)}` PDF doc(s), `{len(response.retrieved_cases)}` clinical case(s)"
            )

            # Render Grounding Evidence Panel
            render_evidence_panel(st, response)

            # Save assistant response
            current_session.add_message(role="assistant", content=response.answer, response=response)

    # Footer Disclaimer
    st.markdown(
        f"<div style='text-align: center; color: #5f6368; font-size: 0.72rem; margin-top: 30px;'>{healthcare_disclaimer()}</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    run()
