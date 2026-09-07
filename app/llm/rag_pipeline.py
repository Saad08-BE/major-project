"""End-to-end local Healthcare RAG pipeline orchestrating safety, retrieval, and LLM generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any

from app.config.settings import AppSettings
from app.llm.ollama_client import LLMGenerationResult, LocalServiceUnavailable, ModelUnavailableError, OllamaClient
from app.llm.prompts import HEALTHCARE_SYSTEM_PROMPT, build_grounded_prompt
from app.retrieval.dataset_retriever import DatasetRetriever, RetrievalContext
from app.retrieval.vector_store import VectorSearchResult
from app.safety import SafetyDecision, healthcare_disclaimer, validate_question


@dataclass(frozen=True)
class RAGResponse:
    """Complete response object returned to the user or UI."""

    question: str
    answer: str
    retrieved_cases: list[VectorSearchResult]
    cohort_statistics: dict[str, Any]
    disclaimer: str
    llm_model: str | None
    is_offline_fallback: bool
    urgent_warning: bool
    total_latency_seconds: float
    safety_decision: SafetyDecision


class HealthcareRAGPipeline:
    """Orchestrates safety checks, hybrid retrieval, and local LLM generation."""

    def __init__(
        self,
        retriever: DatasetRetriever,
        ollama_client: OllamaClient,
        settings: AppSettings,
    ) -> None:
        self.retriever = retriever
        self.ollama = ollama_client
        self.settings = settings

    @classmethod
    def initialize(cls, settings: AppSettings | None = None) -> "HealthcareRAGPipeline":
        """Factory initializing pipeline components from project settings and local disk."""
        app_settings = settings or AppSettings.from_environment()
        app_settings.paths.create_runtime_directories()

        retriever = DatasetRetriever.from_local_files(
            vector_store_dir=app_settings.paths.vector_store_dir,
            processed_data_dir=app_settings.paths.processed_data_dir,
        )
        ollama = OllamaClient(
            base_url=app_settings.ollama_base_url,
            timeout_seconds=60.0,
        )
        return cls(retriever=retriever, ollama_client=ollama, settings=app_settings)

    def answer_question(self, question: str) -> RAGResponse:
        """Run full RAG pipeline for a user question."""
        start_time = time.time()

        # 1. Safety Triage
        safety = validate_question(question)
        if not safety.allowed:
            return RAGResponse(
                question=question,
                answer=safety.user_message,
                retrieved_cases=[],
                cohort_statistics={},
                disclaimer=healthcare_disclaimer(),
                llm_model=None,
                is_offline_fallback=False,
                urgent_warning=False,
                total_latency_seconds=round(time.time() - start_time, 3),
                safety_decision=safety,
            )

        # 2. Hybrid Retrieval
        context: RetrievalContext = self.retriever.retrieve_context(
            query=question,
            top_k=self.settings.top_k,
            min_similarity=self.settings.similarity_threshold,
        )

        # 3. Prompt Construction
        grounded_prompt = build_grounded_prompt(
            question=question,
            evidence_context_block=context.formatted_context_block,
        )

        # 4. Local LLM Generation (with graceful offline fallback)
        answer_text = ""
        used_model = None
        is_fallback = False

        try:
            llm_result: LLMGenerationResult = self.ollama.generate(
                prompt=grounded_prompt,
                model=self.settings.llm_model,
                system=HEALTHCARE_SYSTEM_PROMPT,
                temperature=0.2,
            )
            answer_text = llm_result.response_text
            used_model = llm_result.model
        except (LocalServiceUnavailable, ModelUnavailableError) as exc:
            # Graceful degradation: synthesize retrieved evidence directly
            is_fallback = True
            used_model = None
            answer_text = self._build_offline_evidence_summary(question, context, str(exc))

        # 5. Attach Disclaimers & Urgent Warning
        disclaimer = healthcare_disclaimer()
        if safety.urgent:
            answer_text = (
                "⚠️ **URGENT MEDICAL NOTICE**: Your question mentions acute or potentially serious symptoms. "
                "Please seek immediate medical evaluation or emergency care.\n\n"
                + answer_text
            )

        total_time = round(time.time() - start_time, 3)

        return RAGResponse(
            question=question,
            answer=answer_text,
            retrieved_cases=context.evidence_records,
            cohort_statistics=context.cohort_statistics,
            disclaimer=disclaimer,
            llm_model=used_model,
            is_offline_fallback=is_fallback,
            urgent_warning=safety.urgent,
            total_latency_seconds=total_time,
            safety_decision=safety,
        )

    def _build_offline_evidence_summary(
        self,
        question: str,
        context: RetrievalContext,
        offline_reason: str,
    ) -> str:
        """Construct a structured evidence summary when the local LLM is offline."""
        lines = [
            f"ℹ️ *Local LLM is offline ({offline_reason}). Displaying retrieved evidence directly:*\n",
            "### Retrieved Local Healthcare Evidence\n",
        ]

        if context.cohort_statistics.get("symptom_evidence"):
            lines.append("**Cohort Statistical Associations**:")
            for symp, diags in context.cohort_statistics["symptom_evidence"].items():
                diag_list = ", ".join(f"**{d['diagnosis']}** ({d['percentage']}%)" for d in diags)
                lines.append(f"- Symptoms *'{symp}'* correlate with: {diag_list}")
            lines.append("")

        if context.cohort_statistics.get("diagnosis_evidence"):
            lines.append("**Treatment & Outcome Trends**:")
            for diag, info in context.cohort_statistics["diagnosis_evidence"].items():
                treats = ", ".join(f"{t['treatment']} ({t['percentage']}%)" for t in info["common_treatments"])
                outcomes = ", ".join(f"{o['outcome']} ({o['percentage']}%)" for o in info["outcomes"])
                lines.append(f"- **{diag}**: Common Treatments: [{treats}]; Outcomes: [{outcomes}]")
            lines.append("")

        if context.evidence_records:
            lines.append("**Matching De-Identified Cases**:")
            for idx, case in enumerate(context.evidence_records[:3], 1):
                lines.append(f"{idx}. {case.text}")
        else:
            lines.append("No direct case matches met the similarity threshold.")

        return "\n".join(lines)
