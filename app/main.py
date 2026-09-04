"""Local Streamlit entry point for the healthcare intelligence system."""

from __future__ import annotations

from app.config import AppSettings, SettingsError
from app.safety import healthcare_disclaimer, validate_question


def run() -> None:
    """Render the Phase 1 local-only application shell."""
    import streamlit as st

    st.set_page_config(page_title="Local Healthcare Intelligence", page_icon="🩺")
    st.title("Local Privacy-Based Healthcare Intelligence System")
    st.info("Your data is processed locally on this computer.")
    st.caption(healthcare_disclaimer())

    try:
        settings = AppSettings.from_environment()
        settings.paths.create_runtime_directories()
    except SettingsError as exc:
        st.error(f"Local configuration error: {exc}")
        st.stop()

    question = st.text_area("Healthcare question or symptoms", placeholder="Describe a general healthcare question.")
    if st.button("Validate question", type="primary"):
        decision = validate_question(question)
        if not decision.allowed:
            st.warning(decision.user_message)
        elif decision.urgent:
            st.error(healthcare_disclaimer())
        else:
            st.success("Question accepted. Dataset retrieval and local generation will be added in later phases.")

    with st.expander("Local runtime configuration"):
        st.write(f"Local Ollama endpoint: `{settings.ollama_base_url}`")
        st.write(f"Configured local model: `{settings.llm_model}`")


if __name__ == "__main__":
    run()

