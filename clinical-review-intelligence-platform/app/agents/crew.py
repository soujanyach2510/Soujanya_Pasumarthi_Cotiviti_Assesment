from __future__ import annotations

import json
from typing import Any

from crewai import Crew, Process

from app.agents.tasks import (
    GuidanceReference,
    StructuredClaimReview,
    create_review_tasks,
)

from app.rag.retriever import retrieve_claim_review_guidance


# =====================================================
# RAG Query Builders
# =====================================================

def _safe_text(
    value: Any,
) -> str:
    """
    Convert a source value to clean text for retrieval queries.
    """

    if value is None:
        return ""

    return str(value).strip()


def _extract_primary_diagnosis(
    claim_case: dict[str, Any],
) -> str:
    """
    Extract the documented primary diagnosis without
    performing clinical interpretation.
    """

    encounter = claim_case.get("encounter")

    if not isinstance(encounter, dict):
        return ""

    diagnosis = encounter.get("primary_diagnosis")

    if isinstance(diagnosis, str):
        return diagnosis.strip()

    if isinstance(diagnosis, dict):
        for key in (
            "description",
            "name",
            "diagnosis",
        ):
            value = _safe_text(
                diagnosis.get(key)
            )

            if value:
                return value

    return ""


def _extract_timeline_event_names(
    claim_case: dict[str, Any],
) -> list[str]:
    """
    Extract documented timeline-event labels for retrieval.
    """

    encounter = claim_case.get("encounter")

    if not isinstance(encounter, dict):
        return []

    timeline = encounter.get("timeline")

    if not isinstance(timeline, list):
        return []

    event_names: list[str] = []

    for event in timeline:
        if not isinstance(event, dict):
            continue

        event_name = (
            event.get("event")
            or event.get("title")
            or event.get("event_name")
        )

        clean_name = _safe_text(
            event_name
        )

        if clean_name:
            event_names.append(
                clean_name
            )

    return event_names


def _build_clinical_query(
    claim_case: dict[str, Any],
) -> str:
    """
    Build the clinical-guidance retrieval query.

    This query focuses on the documented clinical context of
    the encounter. It is used only to search the
    clinical_guidelines category.
    """

    parts: list[str] = []

    diagnosis = _extract_primary_diagnosis(
        claim_case
    )

    if diagnosis:
        parts.append(
            f"Primary diagnosis: {diagnosis}"
        )

    encounter = claim_case.get("encounter")

    if isinstance(encounter, dict):
        encounter_type = _safe_text(
            encounter.get("encounter_type")
        )

        if encounter_type:
            parts.append(
                f"Encounter type: {encounter_type}"
            )

        clinical_summary = _safe_text(
            encounter.get("clinical_summary")
        )

        if clinical_summary:
            parts.append(
                "Clinical summary: "
                + clinical_summary
            )

    patient = claim_case.get("patient")

    if isinstance(patient, dict):
        comorbidities = patient.get(
            "comorbidities"
        )

        if isinstance(
            comorbidities,
            list,
        ) and comorbidities:
            parts.append(
                "Documented comorbidities: "
                + ", ".join(
                    str(item)
                    for item in comorbidities
                )
            )

    event_names = (
        _extract_timeline_event_names(
            claim_case
        )
    )

    if event_names:
        parts.append(
            "Documented clinical events: "
            + ", ".join(
                event_names
            )
        )

    if not parts:
        return (
            "Relevant clinical guidance for the "
            "submitted healthcare encounter."
        )

    return "\n".join(parts)


def _build_payer_query(
    claim_case: dict[str, Any],
) -> str:
    """
    Build the payer-policy retrieval query.

    This query focuses on the payer and billed-service
    information. It is used only to search the
    payer_policies category.
    """

    parts: list[str] = []

    claim = claim_case.get("claim")

    if isinstance(claim, dict):
        payer_fields = (
            ("Payer", "payer"),
            ("Claim type", "claim_type"),
            ("Service category", "service_category"),
            ("Service code", "service_code"),
            ("Place of service", "place_of_service"),
            ("Service date", "service_date"),
        )

        for label, key in payer_fields:
            value = _safe_text(
                claim.get(key)
            )

            if value:
                parts.append(
                    f"{label}: {value}"
                )

    review = claim_case.get("review")

    if isinstance(review, dict):
        reason = _safe_text(
            review.get("reason")
        )

        if reason:
            parts.append(
                f"Review reason: {reason}"
            )

    if not parts:
        return (
            "Relevant payer policy for the submitted "
            "healthcare claim and billed service."
        )

    return "\n".join(parts)


def _build_coding_query(
    claim_case: dict[str, Any],
) -> str:
    """
    Build the coding-rule retrieval query.

    This query focuses on coding and billing attributes.
    It is used only to search the coding_rules category.
    """

    parts: list[str] = []

    claim = claim_case.get("claim")

    if isinstance(claim, dict):
        coding_fields = (
            ("Claim type", "claim_type"),
            ("Service category", "service_category"),
            ("Service code", "service_code"),
            ("Place of service", "place_of_service"),
            ("Service date", "service_date"),
            ("Billed units", "billed_units"),
        )

        for label, key in coding_fields:
            value = _safe_text(
                claim.get(key)
            )

            if value:
                parts.append(
                    f"{label}: {value}"
                )

    diagnosis = _extract_primary_diagnosis(
        claim_case
    )

    if diagnosis:
        parts.append(
            f"Primary diagnosis: {diagnosis}"
        )

    if not parts:
        return (
            "Relevant coding and billing guidance for "
            "the submitted healthcare claim."
        )

    return "\n".join(parts)


# =====================================================
# Retrieved Guidance Formatter
# =====================================================

def _format_retrieved_guidance(
    retrieval_results: list[dict[str, Any]],
) -> str:
    """
    Convert retrieved Chroma/LlamaIndex results into
    clean context for the CrewAI tasks.
    """

    if not retrieval_results:
        return (
            "No relevant knowledge-base guidance "
            "was retrieved."
        )

    formatted_sections: list[str] = []

    for result in retrieval_results:
        rank = result.get(
            "rank",
            "Unknown",
        )

        source_file = result.get(
            "source_file",
            "Unknown",
        )

        category = result.get(
            "knowledge_category",
            "Unknown",
        )

        text = str(
            result.get(
                "text",
                "",
            )
        ).strip()

        if not text:
            continue

        formatted_sections.append(
            "\n".join(
                [
                    f"Retrieved Guidance #{rank}",
                    f"Category: {category}",
                    f"Source: {source_file}",
                    "Guidance:",
                    text,
                ]
            )
        )

    if not formatted_sections:
        return (
            "No relevant knowledge-base guidance "
            "was retrieved."
        )

    return "\n\n".join(
        formatted_sections
    )


# =====================================================
# Guidance Reference Builder
# =====================================================

def _build_guidance_references(
    retrieval_results: list[dict[str, Any]],
) -> list[GuidanceReference]:
    """
    Build structured RAG references directly from
    retriever results.

    These references come from Chroma/LlamaIndex metadata,
    not from the LLM.
    """

    references: list[GuidanceReference] = []

    seen: set[
        tuple[
            str,
            str,
        ]
    ] = set()

    for result in retrieval_results:
        source_file = str(
            result.get(
                "source_file",
                "Unknown",
            )
        ).strip()

        knowledge_category = str(
            result.get(
                "knowledge_category",
                "Unknown",
            )
        ).strip()

        score_raw = result.get(
            "score"
        )

        score: float | None = None

        if score_raw is not None:
            try:
                score = float(
                    score_raw
                )
            except (
                TypeError,
                ValueError,
            ):
                score = None

        key = (
            source_file,
            knowledge_category,
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        references.append(
            GuidanceReference(
                source_file=source_file,
                knowledge_category=(
                    knowledge_category
                ),
                score=score,
            )
        )

    return references


# =====================================================
# Multi-Agent Claim Review
# =====================================================

def run_review_crew(
    claim_case: dict[str, Any],
) -> StructuredClaimReview:
    """
    Execute the CRIP multi-agent claim review with retrieved
    RAG guidance.

    Flow:

        Claim case
            ↓
        Build clinical / payer / coding queries
            ↓
        Category-aware ChromaDB / LlamaIndex retrieval
            ↓
        Retrieved clinical + payer + coding guidance
            +
        Claim case
            ↓
        Agent 1
            ↓
        Agent 2
            ↓
        Agent 3
            ↓
        StructuredClaimReview

    The knowledge base provides guidance only.

    The submitted claim case remains the source of truth for
    claim data and patient-specific facts.
    """

    claim_case_json = json.dumps(
        claim_case,
        indent=2,
    )

    # -------------------------------------------------
    # Retrieve relevant knowledge-base guidance
    # -------------------------------------------------

    clinical_query = _build_clinical_query(
        claim_case
    )

    payer_query = _build_payer_query(
        claim_case
    )

    coding_query = _build_coding_query(
        claim_case
    )

    retrieval_results = (
        retrieve_claim_review_guidance(
            clinical_query=clinical_query,
            payer_query=payer_query,
            coding_query=coding_query,
            top_k_per_category=1,
        )
    )

    retrieved_guidance = (
        _format_retrieved_guidance(
            retrieval_results
        )
    )

    guidance_references = (
        _build_guidance_references(
            retrieval_results
        )
    )

    # -------------------------------------------------
    # Create RAG-aware tasks
    # -------------------------------------------------

    (
        claim_pattern_task,
        documentation_review_task,
        synthesis_task,
    ) = create_review_tasks(
        patient_case_json=claim_case_json,
        retrieved_guidance=retrieved_guidance,
    )

    # -------------------------------------------------
    # Run sequential multi-agent workflow
    # -------------------------------------------------

    crew = Crew(
        agents=[
            claim_pattern_task.agent,
            documentation_review_task.agent,
            synthesis_task.agent,
        ],
        tasks=[
            claim_pattern_task,
            documentation_review_task,
            synthesis_task,
        ],
        process=Process.sequential,
        verbose=True,
    )

    crew_result = crew.kickoff()

    structured_review: (
        StructuredClaimReview | None
    ) = None

    # -------------------------------------------------
    # Prefer final task's validated Pydantic output
    # -------------------------------------------------

    if (
        synthesis_task.output is not None
        and synthesis_task.output.pydantic
        is not None
    ):
        structured_review = (
            synthesis_task.output.pydantic
        )

    # -------------------------------------------------
    # Fallback to Crew result
    # -------------------------------------------------

    elif (
        hasattr(
            crew_result,
            "pydantic",
        )
        and crew_result.pydantic
        is not None
    ):
        structured_review = (
            crew_result.pydantic
        )

    if structured_review is None:
        raise ValueError(
            "CrewAI completed the review but did not "
            "return a valid StructuredClaimReview object."
        )

    # -------------------------------------------------
    # Add deterministic RAG source references
    # -------------------------------------------------

    structured_review.guidance_references = (
        guidance_references
    )

    return structured_review