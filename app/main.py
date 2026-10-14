"""Local Streamlit entry point for the healthcare intelligence system."""

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


@st.cache_resource(show_spinner="Initializing local healthcare intelligence engine...")
def get_pipeline(settings: AppSettings) -> HealthcareRAGPipeline:
    """Cache the loaded RAG pipeline across user interactions for instant responses."""
    return HealthcareRAGPipeline.initialize(settings)


def run() -> None:
    """Render the full local-only Streamlit healthcare RAG application."""
    st.set_page_config(
        page_title="Local Healthcare Intelligence",
        page_icon="🩺",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 1. Configuration & Path Verification
    try:
        settings = AppSettings.from_environment()
        settings.paths.create_runtime_directories()
    except SettingsError as exc:
        st.error(f"Local configuration error: {exc}")
        st.stop()

    # 2. Session State Initialization
    initialize_session_state(st)

    # 3. Settings Dialog / Modal check
    if st.session_state.show_settings_dialog:
        with st.container():
            render_settings_dialog(st, settings)
            if st.button("✕ Close Settings", type="secondary"):
                st.session_state.show_settings_dialog = False
                st.rerun()
            st.divider()

    # 4. Left Sidebar Navigation: Top "New Chat", Searchable History, Fixed Bottom "Settings"
    render_sidebar_navigation(st, settings)

    # 5. Main Header & Banner
    current_session = get_current_session(st)

    if st.session_state.temp_mode:
        st.markdown(
            """
            <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 10px 14px; border-radius: 4px; margin-bottom: 15px;">
                <strong style="color: #b91c1c;">🔒 Temporary Consultation Mode Active:</strong>
                <span style="color: #991b1b;"> Messages in this session will not be saved to your consultation history.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="background-color: #f0fdf4; border-left: 4px solid #16a34a; padding: 10px 14px; border-radius: 4px; margin-bottom: 15px;">
                <strong style="color: #15803d;">🔒 Privacy-First Guarantee:</strong>
                <span style="color: #166534;"> All queries, healthcare records, medical PDFs, embeddings, and language model inference run <strong>100% locally on your machine</strong>. Zero cloud telemetry.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.subheader(f"💬 {current_session.title}")
    st.caption(f"Educational System Notice: {healthcare_disclaimer()}")

    # 6. Render Current Session Messages
    for msg in current_session.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "response" in msg and msg["response"] is not None:
                render_evidence_panel(st, msg["response"])

    # 7. Action Bar above Chat Input (+ PDF, Model Picker, Temporary Chat toggle)
    selected_model, is_temp = render_input_controls(st, settings)

    # 8. Chat Input Box
    user_query = st.chat_input("Ask a healthcare question, describe symptoms, or inquire about uploaded medical reports...")

    if user_query:
        # Append user message
        current_session.add_message(role="user", content=user_query)
        with st.chat_message("user"):
            st.markdown(user_query)

        # Run pipeline with preferred model override
        pipeline = get_pipeline(settings)
        with st.chat_message("assistant"):
            with st.spinner(f"Analyzing local clinical evidence using `{selected_model}`..."):
                response: RAGResponse = pipeline.answer_question(
                    user_query,
                    model_override=selected_model,
                )

            # Display urgent warning if triggered
            if response.urgent_warning:
                st.warning("⚠️ **Urgent Medical Notice**: Emergency or severe symptoms detected. Please seek immediate professional or emergency care.")

            # Display answer
            st.markdown(response.answer)

            # Execution badge
            mode_badge = f"🟢 Local LLM ({response.llm_model})" if not response.is_offline_fallback else "🟡 Direct Evidence Synthesis (LLM Offline)"
            st.caption(
                f"⏱️ Latency: `{response.total_latency_seconds:.2f}s` | "
                f"Execution mode: {mode_badge} | "
                f"Evidence: `{len(response.document_sources)}` PDF doc(s), `{len(response.retrieved_cases)}` clinical case(s)"
            )

            # Render Grounding Evidence Panel
            render_evidence_panel(st, response)

            # Save assistant response
            current_session.add_message(role="assistant", content=response.answer, response=response)


if __name__ == "__main__":
    run()
