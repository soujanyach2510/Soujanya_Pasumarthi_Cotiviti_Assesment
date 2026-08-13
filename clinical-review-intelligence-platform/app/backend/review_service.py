from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.agents.crew import run_review_crew
from app.agents.tasks import StructuredClaimReview


# =====================================================
# General Helpers
# =====================================================

def _safe_text(
    value: Any,
    default: str = "",
) -> str:
    """
    Safely convert a value to trimmed text.
    """

    if value is None:
        return default

    text = str(value).strip()

    if not text:
        return default

    return text


def _generate_review_id() -> str:
    """
    Generate a unique CRIP review ID.
    """

    return f"REV-{uuid4().hex[:12].upper()}"



def _get_claim(
    claim_case: dict[str, Any],
) -> dict[str, Any]:
    """
    Return the claim section from the claim-case payload.
    """

    claim = claim_case.get("claim")

    if isinstance(claim, dict):
        return claim

    return {}


def _extract_claim_id(
    claim_case: dict[str, Any],
) -> str:
    """
    Extract the submitted claim identifier.
    """

    return _safe_text(
        _get_claim(claim_case).get("claim_id"),
        default="Not documented",
    )


def _extract_payer(
    claim_case: dict[str, Any],
) -> str:
    """
    Extract the submitted payer name.
    """

    return _safe_text(
        _get_claim(claim_case).get("payer"),
        default="Not documented",
    )


def _extract_service_category(
    claim_case: dict[str, Any],
) -> str:
    """
    Extract the billed service category.
    """

    return _safe_text(
        _get_claim(claim_case).get("service_category"),
        default="Not documented",
    )


def _extract_service_code(
    claim_case: dict[str, Any],
) -> str:
    """
    Extract the submitted service code.
    """

    return _safe_text(
        _get_claim(claim_case).get("service_code"),
        default="Not documented",
    )


# =====================================================
# Claim Case Metadata
# =====================================================

def _extract_case_id(
    claim_case: dict[str, Any],
) -> str:
    """
    Extract the case identifier.

    No clinical reasoning occurs here.
    """

    value = _safe_text(
        claim_case.get("case_id")
    )

    if value:
        return value

    encounter = claim_case.get("encounter")

    if isinstance(encounter, dict):
        value = _safe_text(
            encounter.get("case_id")
        )

        if value:
            return value

    return "UNKNOWN"


def _extract_patient_name(
    claim_case: dict[str, Any],
) -> str:
    """
    Extract the patient name from the submitted claim case.
    """

    direct_name = _safe_text(
        claim_case.get("patient_name")
    )

    if direct_name:
        return direct_name

    patient = claim_case.get("patient")

    if isinstance(patient, dict):
        direct_nested_name = _safe_text(
            patient.get("name")
        )

        if direct_nested_name:
            return direct_nested_name

        first_name = _safe_text(
            patient.get("first_name")
        )

        last_name = _safe_text(
            patient.get("last_name")
        )

        full_name = " ".join(
            part
            for part in [
                first_name,
                last_name,
            ]
            if part
        )

        if full_name:
            return full_name

    return "Unknown Patient"


# =====================================================
# Primary Diagnosis
# =====================================================

def _diagnosis_to_text(
    diagnosis: Any,
) -> str:
    """
    Convert a diagnosis field into text without
    interpreting its clinical meaning.
    """

    if isinstance(diagnosis, str):
        return _safe_text(diagnosis)

    if isinstance(diagnosis, dict):
        for key in (
            "description",
            "name",
            "diagnosis",
            "label",
            "display",
            "text",
        ):
            value = _safe_text(
                diagnosis.get(key)
            )

            if value:
                return value

    return ""


def _extract_primary_diagnosis(
    claim_case: dict[str, Any],
) -> str:
    """
    Extract the documented primary diagnosis from
    supported CRIP claim-case locations.

    This copies source data only.
    """

    diagnosis = _diagnosis_to_text(
        claim_case.get(
            "primary_diagnosis"
        )
    )

    if diagnosis:
        return diagnosis

    encounter = claim_case.get("encounter")

    if isinstance(encounter, dict):
        diagnosis = _diagnosis_to_text(
            encounter.get(
                "primary_diagnosis"
            )
        )

        if diagnosis:
            return diagnosis

        diagnosis = _diagnosis_to_text(
            encounter.get("diagnosis")
        )

        if diagnosis:
            return diagnosis

    return "Not documented"


# =====================================================
# Source Evidence Helpers
# =====================================================

def _create_evidence_item(
    evidence: list[dict[str, str]],
    *,
    source_type: str,
    source_reference: str,
    content: str,
) -> None:
    """
    Append one source-traceability item.

    No clinical interpretation occurs here.
    """

    clean_content = _safe_text(content)

    if not clean_content:
        return

    evidence.append(
        {
            "evidence_id": (
                f"EVID-{len(evidence) + 1:03d}"
            ),
            "source_type": source_type,
            "source_reference": (
                source_reference
            ),
            "content": clean_content,
        }
    )


def _extract_event_content(
    event: dict[str, Any],
) -> str:
    """
    Extract text from a timeline event.
    """

    for key in (
        "details",
        "description",
        "content",
        "note",
        "text",
        "result",
        "summary",
    ):
        value = _safe_text(
            event.get(key)
        )

        if value:
            return value

    return ""


def _extract_event_name(
    event: dict[str, Any],
) -> str:
    """
    Extract the timeline-event label.
    """

    for key in (
        "event",
        "event_name",
        "title",
        "type",
        "name",
    ):
        value = _safe_text(
            event.get(key)
        )

        if value:
            return value

    return "Clinical event"


def _extract_event_time(
    event: dict[str, Any],
) -> str:
    """
    Extract the event timestamp/date.
    """

    for key in (
        "timestamp",
        "datetime",
        "date_time",
        "date",
        "time",
    ):
        value = _safe_text(
            event.get(key)
        )

        if value:
            return value

    return ""


def _find_timeline(
    claim_case: dict[str, Any],
) -> list[Any]:
    """
    Locate clinical timeline events from the claim case.
    """

    possible_keys = (
        "timeline",
        "clinical_timeline",
        "events",
        "clinical_events",
    )

    for key in possible_keys:
        value = claim_case.get(key)

        if isinstance(value, list):
            return value

    encounter = claim_case.get("encounter")

    if isinstance(encounter, dict):
        for key in possible_keys:
            value = encounter.get(key)

            if isinstance(value, list):
                return value

    return []


# =====================================================
# Source Evidence
# =====================================================

def _build_source_evidence(
    claim_case: dict[str, Any],
) -> list[dict[str, str]]:
    """
    Build an auditable traceability view of the submitted
    claim and its supporting clinical documentation.

    IMPORTANT:

    This code does NOT:

    - determine medical necessity
    - make a coverage decision
    - make a coding determination
    - diagnose the patient
    - recommend treatment

    It only preserves source data for human review.
    """

    evidence: list[dict[str, str]] = []

    # -------------------------------------------------
    # Claim information
    # -------------------------------------------------

    claim = _get_claim(claim_case)

    claim_fields = (
        ("Claim ID", "claim_id"),
        ("Payer", "payer"),
        ("Provider", "provider"),
        ("Claim type", "claim_type"),
        ("Service category", "service_category"),
        ("Service code", "service_code"),
        ("Place of service", "place_of_service"),
        ("Service date", "service_date"),
        ("Billed units", "billed_units"),
        ("Billed amount", "billed_amount"),
        ("Claim status", "claim_status"),
    )

    for label, key in claim_fields:
        value = claim.get(key)

        if value is None:
            continue

        clean_value = _safe_text(value)

        if clean_value:
            _create_evidence_item(
                evidence,
                source_type="Claim",
                source_reference=label,
                content=clean_value,
            )

    # -------------------------------------------------
    # Primary diagnosis
    # -------------------------------------------------

    primary_diagnosis = (
        _extract_primary_diagnosis(
            claim_case
        )
    )

    if (
        primary_diagnosis
        and primary_diagnosis
        != "Not documented"
    ):
        _create_evidence_item(
            evidence,
            source_type="Clinical Documentation",
            source_reference="Primary diagnosis",
            content=primary_diagnosis,
        )

    # -------------------------------------------------
    # Clinical summary
    # -------------------------------------------------

    encounter = claim_case.get("encounter")

    clinical_summary = ""

    if isinstance(encounter, dict):
        clinical_summary = _safe_text(
            encounter.get("clinical_summary")
        )

    if not clinical_summary:
        clinical_summary = _safe_text(
            claim_case.get("clinical_summary")
        )

    if clinical_summary:
        _create_evidence_item(
            evidence,
            source_type="Clinical Documentation",
            source_reference="Encounter clinical summary",
            content=clinical_summary,
        )

    # -------------------------------------------------
    # Patient comorbidities
    # -------------------------------------------------

    patient = claim_case.get("patient")

    if isinstance(patient, dict):
        comorbidities = patient.get(
            "comorbidities"
        )

        if isinstance(
            comorbidities,
            list,
        ):
            clean_conditions = [
                _safe_text(item)
                for item in comorbidities
                if _safe_text(item)
            ]

            if clean_conditions:
                _create_evidence_item(
                    evidence,
                    source_type="Clinical Documentation",
                    source_reference="Patient comorbidities",
                    content=", ".join(
                        clean_conditions
                    ),
                )

    # -------------------------------------------------
    # Clinical timeline
    # -------------------------------------------------

    timeline = _find_timeline(
        claim_case
    )

    for event in timeline:
        if not isinstance(event, dict):
            continue

        event_name = _extract_event_name(
            event
        )

        event_time = _extract_event_time(
            event
        )

        event_content = (
            _extract_event_content(
                event
            )
        )

        if not event_content:
            continue

        if event_time:
            source_reference = (
                f"{event_name} — "
                f"{event_time}"
            )
        else:
            source_reference = event_name

        _create_evidence_item(
            evidence,
            source_type="Clinical Timeline",
            source_reference=source_reference,
            content=event_content,
        )

    # -------------------------------------------------
    # Submitted-document inventory
    # -------------------------------------------------

    submitted_documents = claim_case.get(
        "submitted_documents"
    )

    if isinstance(submitted_documents, list):
        for document in submitted_documents:
            if not isinstance(document, dict):
                continue

            document_type = _safe_text(
                document.get("document_type"),
                default="Submitted document",
            )

            file_name = _safe_text(
                document.get("file_name")
            )

            document_date = _safe_text(
                document.get("date")
            )

            details = " | ".join(
                value
                for value in (
                    file_name,
                    document_date,
                )
                if value
            )

            if details:
                _create_evidence_item(
                    evidence,
                    source_type="Submitted Document",
                    source_reference=document_type,
                    content=details,
                )

    return evidence


# =====================================================
# Structured Agent Review
# =====================================================

def _serialize_agent_review(
    review: StructuredClaimReview,
) -> dict[str, Any]:
    """
    Serialize validated Pydantic output.

    No clinical reasoning occurs here.
    """

    return review.model_dump()


# =====================================================
# Deterministic Source-Integrity Validation
# =====================================================

def _collect_source_strings(
    value: Any,
) -> list[str]:
    """
    Flatten submitted claim-case values into normalized strings.

    This helper is used only for objective source-integrity checks.
    It does not perform claim-review reasoning.
    """

    collected: list[str] = []

    if value is None:
        return collected

    if isinstance(value, dict):
        for nested_value in value.values():
            collected.extend(
                _collect_source_strings(
                    nested_value
                )
            )

        return collected

    if isinstance(value, list):
        for item in value:
            collected.extend(
                _collect_source_strings(
                    item
                )
            )

        return collected

    text_value = _safe_text(
        value
    )

    if text_value:
        collected.append(
            text_value
        )

    return collected


def _contains_source_value(
    candidate: str,
    source_values: list[str],
) -> bool:
    """
    Check whether a candidate value appears exactly in
    the original submitted claim case.
    """

    normalized_candidate = (
        candidate.strip().casefold()
    )

    if not normalized_candidate:
        return False

    return any(
        source_value.strip().casefold()
        == normalized_candidate
        for source_value in source_values
    )


def _extract_quoted_values(
    text: str,
) -> list[str]:
    """
    Extract simple quoted values from agent-generated
    evidence/source-reference strings.
    """

    quoted_values: list[str] = []

    current_quote: str | None = None
    buffer: list[str] = []

    for character in text:
        if current_quote is None:
            if character in {'"', "'"}:
                current_quote = character
                buffer = []

            continue

        if character == current_quote:
            value = "".join(
                buffer
            ).strip()

            if value:
                quoted_values.append(
                    value
                )

            current_quote = None
            buffer = []
            continue

        buffer.append(
            character
        )

    return quoted_values


def _collect_text_corpus(
    value: Any,
) -> str:
    """
    Flatten nested values into one lowercase text corpus.

    This is used only for deterministic presence checks.
    It does not infer medical necessity, coding correctness,
    or claim validity.
    """

    return " ".join(
        item
        for item in _collect_source_strings(
            value
        )
        if item
    ).casefold()


def _extract_calendar_dates(
    value: Any,
) -> set[str]:
    """
    Extract YYYY-MM-DD calendar dates from nested values.

    Datetimes are reduced to their calendar date so that
    2026-07-22 and 2026-07-22T10:05:00 compare correctly.
    """

    dates: set[str] = set()

    for text_value in _collect_source_strings(
        value
    ):
        for date_match in re.findall(
            r"\b\d{4}-\d{2}-\d{2}\b",
            text_value,
        ):
            dates.add(date_match)

    return dates


def _collect_agent_review_text(
    agent_review: dict[str, Any],
) -> str:
    """
    Collect human-readable agent output into one text corpus.

    Guidance metadata is intentionally excluded because this
    validator is checking agent claims against the submitted case.
    """

    review_subset = {
        "documented_facts": agent_review.get(
            "documented_facts",
            [],
        ),
        "clinical_patterns": agent_review.get(
            "clinical_patterns",
            [],
        ),
        "documentation_gaps": agent_review.get(
            "documentation_gaps",
            [],
        ),
        "evidence_references": agent_review.get(
            "evidence_references",
            [],
        ),
        "reviewer_actions": agent_review.get(
            "reviewer_actions",
            [],
        ),
        "advisory_summary": agent_review.get(
            "advisory_summary",
            "",
        ),
    }

    return _collect_text_corpus(
        review_subset
    )


def _finding_contains_missing_support_language(
    finding: dict[str, Any],
) -> bool:
    """
    Detect whether a claim finding itself describes missing
    or undocumented support.

    This does not create a documentation gap. It only helps
    detect inconsistent structured output when the gap list is empty.
    """

    finding_text = _collect_text_corpus(
        {
            "title": finding.get("title"),
            "description": finding.get(
                "description"
            ),
            "supporting_facts": finding.get(
                "supporting_facts",
                [],
            ),
        }
    )

    missing_phrases = (
        "not documented",
        "no documentation",
        "no documented",
        "missing documentation",
        "documentation missing",
        "could not confirm",
        "unable to confirm",
        "not found in the documentation",
    )

    return any(
        phrase in finding_text
        for phrase in missing_phrases
    )


def _validate_agent_dates_against_source(
    *,
    claim_case: dict[str, Any],
    agent_review: dict[str, Any],
) -> list[str]:
    """
    Flag calendar dates introduced by the agents that are not
    present anywhere in the submitted claim case.

    This is intentionally conservative and objective.
    """

    warnings: list[str] = []

    source_dates = _extract_calendar_dates(
        claim_case
    )

    agent_dates = _extract_calendar_dates(
        {
            "documented_facts": agent_review.get(
                "documented_facts",
                [],
            ),
            "clinical_patterns": agent_review.get(
                "clinical_patterns",
                [],
            ),
            "documentation_gaps": agent_review.get(
                "documentation_gaps",
                [],
            ),
            "evidence_references": agent_review.get(
                "evidence_references",
                [],
            ),
            "reviewer_actions": agent_review.get(
                "reviewer_actions",
                [],
            ),
            "advisory_summary": agent_review.get(
                "advisory_summary",
                "",
            ),
        }
    )

    unsupported_dates = sorted(
        agent_dates - source_dates
    )

    for date_value in unsupported_dates:
        warnings.append(
            "Agent output references calendar date "
            f"{date_value}, but that date does not appear "
            "anywhere in the submitted claim case."
        )

    return warnings


def _validate_service_date_mismatch_claims(
    *,
    claim_case: dict[str, Any],
    agent_review: dict[str, Any],
) -> list[str]:
    """
    Catch an obvious false service-date mismatch when the claim
    service date and every documented timeline event share the
    same calendar date.
    """

    warnings: list[str] = []

    claim = _get_claim(
        claim_case
    )

    service_date = _safe_text(
        claim.get("service_date")
    )[:10]

    if not service_date:
        return warnings

    timeline_dates: set[str] = set()

    for event in _find_timeline(
        claim_case
    ):
        if not isinstance(event, dict):
            continue

        event_time = _extract_event_time(
            event
        )

        if len(event_time) >= 10:
            timeline_dates.add(
                event_time[:10]
            )

    if (
        not timeline_dates
        or timeline_dates != {service_date}
    ):
        return warnings

    patterns = agent_review.get(
        "clinical_patterns",
        [],
    )

    if not isinstance(patterns, list):
        return warnings

    mismatch_phrases = (
        "service date does not match",
        "service-date does not match",
        "service date mismatch",
        "date mismatch",
        "dates do not match",
        "conflicting service date",
    )

    for index, finding in enumerate(
        patterns,
        start=1,
    ):
        if not isinstance(finding, dict):
            continue

        finding_text = _collect_text_corpus(
            finding
        )

        if any(
            phrase in finding_text
            for phrase in mismatch_phrases
        ):
            warnings.append(
                "Claim finding "
                f"{index} reports a service-date mismatch, "
                f"but the claim service date ({service_date}) "
                "and all documented timeline events use the "
                "same calendar date."
            )

    return warnings


def _validate_documentation_gap_consistency(
    *,
    claim_case: dict[str, Any],
    agent_review: dict[str, Any],
) -> list[str]:
    """
    Perform conservative cross-output checks for common Ollama
    inconsistencies.

    Python does not create or remove gaps. It only flags cases
    where agent output contradicts readily observable source data
    or contradicts another structured section.
    """

    warnings: list[str] = []

    patterns = agent_review.get(
        "clinical_patterns",
        [],
    )

    gaps = agent_review.get(
        "documentation_gaps",
        [],
    )

    if not isinstance(patterns, list):
        patterns = []

    if not isinstance(gaps, list):
        gaps = []

    if not gaps:
        for finding in patterns:
            if not isinstance(finding, dict):
                continue

            if _finding_contains_missing_support_language(
                finding
            ):
                warnings.append(
                    "Agent findings describe missing or "
                    "undocumented supporting information, "
                    "but documentation_gaps is empty."
                )
                break

    source_text = _collect_text_corpus(
        claim_case
    )

    for index, gap in enumerate(
        gaps,
        start=1,
    ):
        if not isinstance(gap, dict):
            continue

        gap_text = _collect_text_corpus(
            gap
        )

        missing_language = any(
            phrase in gap_text
            for phrase in (
                "not documented",
                "missing",
                "unclear",
                "could not confirm",
                "unable to confirm",
            )
        )

        if not missing_language:
            continue

        # Conservative check for diagnostic results that are
        # plainly present in the submitted case.
        if (
            "diagnostic" in gap_text
            and (
                "electrocardiogram" in source_text
                or "ecg" in source_text
                or "troponin" in source_text
            )
            and any(
                result_term in source_text
                for result_term in (
                    "result",
                    "showed",
                    "normal sinus rhythm",
                    "normal reference range",
                    "within the normal reference range",
                )
            )
        ):
            warnings.append(
                "Documentation gap "
                f"{index} describes diagnostic testing/results "
                "as missing or unclear, but the submitted case "
                "contains documented diagnostic test information "
                "and results. Human verification is required."
            )

        # Conservative check for an observation-start gap when
        # the source explicitly says observation was initiated.
        if (
            "observation" in gap_text
            and (
                "start" in gap_text
                or "initiated" in gap_text
            )
            and "observation initiated" in source_text
        ):
            warnings.append(
                "Documentation gap "
                f"{index} describes an observation start as "
                "missing, but the submitted case explicitly "
                "contains an 'Observation initiated' event. "
                "Human verification is required."
            )

    return warnings


def _validate_agent_output_source_integrity(
    *,
    claim_case: dict[str, Any],
    agent_review: dict[str, Any],
) -> dict[str, Any]:
    """
    Perform deterministic source-integrity checks on the
    agent-generated review.

    The validator does NOT:
    - create claim-review patterns
    - create reviewer actions
    - create an advisory summary
    - decide coverage, coding, payment, or medical necessity

    It only flags objective integrity problems, including
    common inconsistencies that can occur with a lightweight
    local Ollama model.
    """

    warnings: list[str] = []

    source_values = (
        _collect_source_strings(
            claim_case
        )
    )

    evidence_references = (
        agent_review.get(
            "evidence_references",
            [],
        )
    )

    if isinstance(
        evidence_references,
        list,
    ):
        for index, reference in enumerate(
            evidence_references,
            start=1,
        ):
            if not isinstance(
                reference,
                dict,
            ):
                continue

            source_text = _safe_text(
                reference.get("source")
            )

            documented_fact = _safe_text(
                reference.get(
                    "documented_fact"
                )
            )

            combined_text = " ".join(
                part
                for part in (
                    source_text,
                    documented_fact,
                )
                if part
            )

            if not combined_text:
                continue

            if "=" not in combined_text:
                continue

            for quoted_value in (
                _extract_quoted_values(
                    combined_text
                )
            ):
                if _contains_source_value(
                    quoted_value,
                    source_values,
                ):
                    continue

                warnings.append(
                    "Evidence reference "
                    f"{index} contains quoted value "
                    f"'{quoted_value}' that was not found "
                    "as an exact value in the submitted "
                    "claim case."
                )

    reviewer_actions = (
        agent_review.get(
            "reviewer_actions",
            [],
        )
    )

    if not reviewer_actions:
        warnings.append(
            "Agent synthesis returned no reviewer actions."
        )

    else:
        generic_action_terms = {
            "verify",
            "review",
            "confirm",
            "validate",
        }

        generic_actions_found = False

        for action_item in reviewer_actions:
            if isinstance(
                action_item,
                dict,
            ):
                action_text = _safe_text(
                    action_item.get(
                        "action"
                    )
                )

            else:
                action_text = _safe_text(
                    action_item
                )

            if (
                action_text
                and action_text.casefold()
                in generic_action_terms
            ):
                generic_actions_found = True
                break

        if generic_actions_found:
            warnings.append(
                "Agent reviewer actions are too generic "
                "and do not specify what the human "
                "reviewer should validate."
            )

    advisory_summary = _safe_text(
        agent_review.get(
            "advisory_summary"
        )
    )

    generic_summary_phrases = (
        "this analysis is advisory",
        "requires human validation",
        "human validation is required",
    )

    if (
        advisory_summary
        and len(
            advisory_summary.split()
        ) <= 20
        and any(
            phrase
            in advisory_summary.casefold()
            for phrase
            in generic_summary_phrases
        )
    ):
        warnings.append(
            "Agent advisory summary appears generic and "
            "does not contain enough claim-specific review "
            "detail."
        )

    # -------------------------------------------------
    # Ollama-oriented objective consistency checks
    # -------------------------------------------------

    warnings.extend(
        _validate_agent_dates_against_source(
            claim_case=claim_case,
            agent_review=agent_review,
        )
    )

    warnings.extend(
        _validate_service_date_mismatch_claims(
            claim_case=claim_case,
            agent_review=agent_review,
        )
    )

    warnings.extend(
        _validate_documentation_gap_consistency(
            claim_case=claim_case,
            agent_review=agent_review,
        )
    )

    # Preserve order while removing duplicate warnings.
    warnings = list(
        dict.fromkeys(
            warnings
        )
    )

    status = (
        "warning"
        if warnings
        else "passed"
    )

    return {
        "source_integrity": status,
        "warnings": warnings,
    }


# =====================================================
# Main Review Service
# =====================================================

def generate_claim_review(
    claim_case: dict[str, Any],
) -> dict[str, Any]:
    """
    Execute the CRIP multi-agent claim-review workflow.

    AI responsibility:
        Agent 1:
            Claim-relevant pattern recognition

        Agent 2:
            Evidence/documentation verification

        Agent 3:
            Human-safe claim-review synthesis

    Python responsibility:
        - preserve claim and patient metadata
        - generate review ID
        - generate timestamp
        - preserve original source evidence
        - preserve deterministic RAG guidance references
        - serialize structured AI output
        - validate objective source integrity
        - construct API response

    Python does NOT independently make claim, coverage, coding, or clinical decisions.
    """

    if not isinstance(
        claim_case,
        dict,
    ):
        raise ValueError(
            "claim_case must be a dictionary."
        )

    # -------------------------------------------------
    # Multi-agent reasoning
    # -------------------------------------------------

    structured_review = run_review_crew(
        claim_case=claim_case,
    )

    if not isinstance(
        structured_review,
        StructuredClaimReview,
    ):
        raise ValueError(
            "CrewAI did not return a valid "
            "StructuredClaimReview."
        )

    # -------------------------------------------------
    # Serialize AI result
    # -------------------------------------------------

    agent_review = (
        _serialize_agent_review(
            structured_review
        )
    )

    # -------------------------------------------------
    # Preserve original source traceability
    # -------------------------------------------------

    source_evidence = (
        _build_source_evidence(
            claim_case
        )
    )

    # -------------------------------------------------
    # Deterministic source-integrity validation
    # -------------------------------------------------

    validation = (
        _validate_agent_output_source_integrity(
            claim_case=claim_case,
            agent_review=agent_review,
        )
    )

    # -------------------------------------------------
    # Construct API payload
    # -------------------------------------------------

    return {
        "review_id": (
            _generate_review_id()
        ),

        "case_id": (
            _extract_case_id(
                claim_case
            )
        ),

        "patient_name": (
            _extract_patient_name(
                claim_case
            )
        ),

        "review_status": "completed",

        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "review_type": (
            "multi_agent_claim_review"
        ),

        "primary_diagnosis": (
            _extract_primary_diagnosis(
                claim_case
            )
        ),

        # =============================================
        # Agent-generated review
        # =============================================

        "documented_facts": (
            agent_review[
                "documented_facts"
            ]
        ),

        "clinical_patterns": (
            agent_review[
                "clinical_patterns"
            ]
        ),

        "documentation_gaps": (
            agent_review[
                "documentation_gaps"
            ]
        ),

        "evidence_references": (
            agent_review[
                "evidence_references"
            ]
        ),

        # =============================================
        # Retrieved RAG guidance traceability
        # =============================================

        "guidance_references": (
            agent_review.get(
                "guidance_references",
                [],
            )
        ),

        "reviewer_actions": (
            agent_review[
                "reviewer_actions"
            ]
        ),

        "advisory_summary": (
            agent_review[
                "advisory_summary"
            ]
        ),

        "human_validation_required": (
            agent_review[
                "human_validation_required"
            ]
        ),

        # =============================================
        # Original source traceability
        # =============================================

        "source_evidence": (
            source_evidence
        ),

        # =============================================
        # Deterministic validation
        # =============================================

        "validation": validation,

        # =============================================
        # Safety
        # =============================================

        "safety_notice": (
            "This output is an AI-assisted claim-review advisory. "
            "It does not make a final coverage, coding, medical-"
            "necessity, utilization-management, diagnosis, or "
            "treatment decision. A qualified human reviewer "
            "must validate the evidence and make the final "
            "determination."
        ),
    }