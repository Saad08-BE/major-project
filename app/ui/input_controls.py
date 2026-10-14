"""Gemini-styled input action bar with inline PDF upload (+ icon) and model picker."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import streamlit as st

from app.config.settings import AppSettings
from app.ingestion.pdf_ingestor import PDFIngestor
from app.llm.ollama_client import OllamaClient
from app.retrieval.document_retriever import DocumentRetriever


def get_available_models(settings: AppSettings) -> list[str]:
    """Retrieve locally installed models from Ollama with fallback to default."""
    client = OllamaClient(base_url=settings.ollama_base_url, timeout_seconds=1.5)
    models = []
    if client.is_online():
        try:
            models = client.list_models()
        except Exception:
            pass

    if settings.llm_model not in models:
        models.insert(0, settings.llm_model)
    return models


def render_input_controls(st_module, settings: AppSettings) -> tuple[str, bool]:
    """Render the + PDF uploader, model dropdown, and temporary chat controls styled like Gemini."""
    col_attach, col_model, col_spacer, col_temp = st_module.columns([1, 3, 2, 2])

    with col_attach:
        if st_module.button("➕", help="Add / Index local medical PDF report", use_container_width=True):
            st_module.session_state.show_upload_modal = not st_module.session_state.show_upload_modal
            st_module.rerun()

    with col_model:
        available_models = get_available_models(settings)
        current_idx = 0
        if "selected_model" in st_module.session_state and st_module.session_state.selected_model in available_models:
            current_idx = available_models.index(st_module.session_state.selected_model)

        selected_model = st_module.selectbox(
            "Select Model",
            options=available_models,
            index=current_idx,
            label_visibility="collapsed",
            help="Select local Ollama model (e.g. qwen2.5:3b)",
            key="gemini_model_selector",
        )
        st_module.session_state.selected_model = selected_model

    with col_temp:
        temp_checked = st_module.toggle(
            "Incognito",
            value=st_module.session_state.temp_mode,
            help="Temporary mode: queries are not stored in conversation history.",
            key="temp_chat_toggle",
        )
        if temp_checked != st_module.session_state.temp_mode:
            st_module.session_state.temp_mode = temp_checked
            st_module.rerun()

    # Inline expander for PDF upload if + is toggled
    if st_module.session_state.show_upload_modal:
        with st_module.container():
            st_module.markdown(
                """
                <div style="background: #181b20; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 12px; margin-bottom: 8px;">
                    <div style="font-size: 0.85rem; font-weight: 500; color: #e3e3e3; margin-bottom: 6px;">📄 Add Medical PDF to Local Index</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            uploaded_file = st_module.file_uploader(
                "Upload medical report or clinical guideline PDF",
                type=["pdf"],
                key="inline_pdf_uploader",
                label_visibility="collapsed",
            )
            if uploaded_file is not None:
                if st_module.button("Index Document Now", type="primary"):
                    doc_dir = settings.paths.documents_dir
                    doc_dir.mkdir(parents=True, exist_ok=True)
                    target_path = doc_dir / uploaded_file.name
                    with open(target_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    with st_module.spinner("Processing & indexing PDF locally..."):
                        ingestor = PDFIngestor(
                            chunk_size=settings.chunk_size,
                            chunk_overlap=settings.chunk_overlap,
                        )
                        chunks = ingestor.process_file(target_path)
                        all_chunks = ingestor.process_directory(doc_dir)
                        retriever = DocumentRetriever(embedding_model=None)
                        retriever.index_chunks(all_chunks, settings.paths.vector_store_dir)
                        st_module.success(f"Indexed {len(chunks)} chunk(s) from `{uploaded_file.name}`!")
                        st_module.session_state.show_upload_modal = False
                        st_module.rerun()

    return st_module.session_state.selected_model, st_module.session_state.temp_mode
