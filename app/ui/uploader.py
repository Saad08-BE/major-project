"""UI components for local medical document uploading and live re-indexing."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import streamlit as st

from app.config.settings import AppSettings
from app.ingestion.pdf_ingestor import PDFIngestor
from app.retrieval.document_retriever import DocumentRetriever


def render_document_uploader(st_module, settings: AppSettings) -> bool:
    """Render the document uploader panel. Returns True if a new file was indexed."""
    st_module.sidebar.subheader("📄 Upload Medical PDF")
    st_module.sidebar.caption("Reports, lab results, or clinical practice guidelines")

    uploaded_file = st_module.sidebar.file_uploader(
        "Select a local PDF to index",
        type=["pdf"],
        help="The document is saved locally into data/documents/ and indexed immediately.",
        key="pdf_uploader",
    )

    if uploaded_file is not None:
        save_btn = st_module.sidebar.button("Index Document Locally", type="primary")
        if save_btn:
            doc_dir = settings.paths.documents_dir
            doc_dir.mkdir(parents=True, exist_ok=True)
            target_path = doc_dir / uploaded_file.name

            with open(target_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            with st_module.sidebar.status("Processing PDF locally..."):
                ingestor = PDFIngestor(
                    chunk_size=settings.chunk_size,
                    chunk_overlap=settings.chunk_overlap,
                )
                try:
                    chunks = ingestor.process_file(target_path)
                    retriever = DocumentRetriever(embedding_model=None)
                    # Reindex all documents in the directory
                    all_chunks = ingestor.process_directory(doc_dir)
                    retriever.index_chunks(all_chunks, settings.paths.vector_store_dir)
                    st_module.sidebar.success(f"Indexed {len(chunks)} chunk(s) from `{uploaded_file.name}`!")
                    return True
                except Exception as exc:
                    st_module.sidebar.error(f"Failed to index: {exc}")
                    return False

    return False
