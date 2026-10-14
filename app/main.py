"""Local Streamlit entry point for the healthcare intelligence system."""

from __future__ import annotations

import streamlit as st

from app.config import AppSettings, SettingsError
from app.llm.rag_pipeline import HealthcareRAGPipeline, RAGResponse
from app.safety import healthcare_disclaimer
from app.ui.evidence_viewer import render_evidence_panel
from app.ui.status import render_sidebar_status
from app.ui.uploader import render_document_uploader


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

    # 2. Sidebar Navigation: Status & Document Ingestion
    status_info = render_sidebar_status(st, settings)
    reindexed = render_document_uploader(st, settings)
    if reindexed:
        st.cache_resource.clear()
        st.rerun()

    # 3. Main Header & Local Privacy Banner
    st.title("Local Privacy-Based Healthcare Intelligence System")
    st.markdown(
        """
        <div style="background-color: #f0fdf4; border-left: 4px solid #16a34a; padding: 10px 14px; border-radius: 4px; margin-bottom: 15px;">
            <strong style="color: #15803d;">🔒 Privacy-First Guarantee:</strong>
            <span style="color: #166534;"> All queries, healthcare datasets, medical PDFs, embeddings, and language model inference run <strong>100% locally on your machine</strong>. No data ever leaves your computer.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(f"Educational System Notice: {healthcare_disclaimer()}")

    # 4. Session State for Chat History
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # Clear chat button in sidebar
    if st.sidebar.button("🗑️ Clear Conversation History"):
        st.session_state.chat_messages = []
        st.rerun()

    # 5. Render Historical Chat Conversation
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "response" in msg and msg["response"] is not None:
                render_evidence_panel(st, msg["response"])

    # 6. Chat Input & Live Query Processing
    user_query = st.chat_input("Ask a healthcare question, describe symptoms, or inquire about uploaded medical reports...")

    if user_query:
        # Display user question
        st.session_state.chat_messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        # Execute Pipeline
        pipeline = get_pipeline(settings)
        with st.chat_message("assistant"):
            with st.spinner("Analyzing evidence from local datasets & medical reports..."):
                response: RAGResponse = pipeline.answer_question(user_query)

            # Display urgent warning if triggered
            if response.urgent_warning:
                st.warning("⚠️ **Urgent Medical Notice**: Emergency or severe symptoms detected. Please seek immediate professional or emergency care.")

            # Display response text
            st.markdown(response.answer)

            # Display meta-information footer
            mode_badge = "🟢 Local LLM" if not response.is_offline_fallback else "🟡 Direct Evidence Synthesis (LLM Offline)"
            st.caption(
                f"⏱️ Response latency: `{response.total_latency_seconds:.2f}s` | "
                f"Execution mode: {mode_badge} | "
                f"Evidence: `{len(response.document_sources)}` PDF doc(s), `{len(response.retrieved_cases)}` clinical case(s)"
            )

            # Render Grounding Evidence Panel
            render_evidence_panel(st, response)

            # Save assistant message to state
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": response.answer,
                "response": response,
            })


if __name__ == "__main__":
    run()
