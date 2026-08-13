from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.backend.review_service import (
    generate_claim_review,
)


# =====================================================
# Application Configuration
# =====================================================

app = FastAPI(
    title="Claim Review Intelligence Platform",
    description=(
        "CRIP is an AI-assisted claim review platform "
        "using a multi-agent workflow with mandatory "
        "human validation."
    ),
    version="1.5.0",
)


# =====================================================
# CORS
# =====================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# Project Paths
# =====================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CLAIM_CASES_DIR = (
    PROJECT_ROOT / "claim_cases"
)


# =====================================================
# API Models
# =====================================================

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class CaseSummary(BaseModel):
    case_id: str
    patient_name: str
    primary_diagnosis: str


class CaseListResponse(BaseModel):
    cases: list[CaseSummary]


class CaseDetailResponse(BaseModel):
    case_id: str
    patient_case: dict[str, Any]


class ReviewRequest(BaseModel):
    """
    Optional review configuration.

    review_focus is reserved for future use.
    The current multi-agent workflow reviews the
    complete claim case.
    """

    review_focus: str | None = None


# =====================================================
# Structured Review Models
# =====================================================

class ClaimReviewPatternResponse(BaseModel):
    title: str
    description: str

    supporting_facts: list[str] = Field(
        default_factory=list,
    )

    source_references: list[str] = Field(
        default_factory=list,
    )

    confidence: str

    human_validation_required: bool


class DocumentationGapResponse(BaseModel):
    item: str
    reason: str

    affected_finding: str | None = None

    source_locations_checked: list[str] = Field(
        default_factory=list,
    )

    human_verification_step: str

    verification_status: str


class EvidenceReferenceResponse(BaseModel):
    source: str
    documented_fact: str
    finding_supported: str


class GuidanceReferenceResponse(BaseModel):
    source_file: str
    knowledge_category: str
    score: float | None = None


class ReviewerActionResponse(BaseModel):
    action: str

    related_finding: str | None = None


class SourceEvidenceResponse(BaseModel):
    evidence_id: str
    source_type: str
    source_reference: str
    content: str



class ValidationResponse(BaseModel):
    source_integrity: str

    warnings: list[str] = Field(
        default_factory=list,
    )


class ClaimReviewResponse(BaseModel):
    """
    Final structured API response returned by CRIP.

    Claim-review analysis is produced by CrewAI agents.

    Deterministic Python only packages the structured
    output and preserves source traceability.
    """

    review_id: str
    case_id: str
    patient_name: str

    review_status: str
    generated_at: str
    review_type: str

    primary_diagnosis: str

    documented_facts: list[str] = Field(
        default_factory=list,
    )

    clinical_patterns: list[
        ClaimReviewPatternResponse
    ] = Field(
        default_factory=list,
    )

    documentation_gaps: list[
        DocumentationGapResponse
    ] = Field(
        default_factory=list,
    )

    evidence_references: list[
        EvidenceReferenceResponse
    ] = Field(
        default_factory=list,
    )

    guidance_references: list[
        GuidanceReferenceResponse
    ] = Field(
        default_factory=list,
    )

    reviewer_actions: list[
        ReviewerActionResponse
    ] = Field(
        default_factory=list,
    )

    advisory_summary: str

    human_validation_required: bool

    source_evidence: list[
        SourceEvidenceResponse
    ] = Field(
        default_factory=list,
    )

    validation: ValidationResponse

    safety_notice: str


# =====================================================
# Utility Functions
# =====================================================

def _safe_text(
    value: Any,
    default: str = "",
) -> str:
    """
    Safely convert a value to text.
    """

    if value is None:
        return default

    text = str(value).strip()

    if not text:
        return default

    return text


def _load_json_file(
    file_path: Path,
) -> dict[str, Any]:
    """
    Load one JSON claim-case file.
    """

    try:
        with file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="Claim case file was not found.",
        ) from exc

    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Claim case file contains invalid JSON."
            ),
        ) from exc

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=500,
            detail=(
                "Claim case file must contain "
                "a JSON object."
            ),
        )

    return data


def _find_case_file(
    case_id: str,
) -> Path:
    """
    Locate the claim_case.json file for a case.

    Expected structure:

    claim_cases/
        case_1001/
            claim_case.json
    """

    normalized_case_id = (
        _safe_text(case_id)
        .replace("case_", "")
        .replace("CASE_", "")
    )

    candidate = (
        CLAIM_CASES_DIR
        / f"case_{normalized_case_id}"
        / "claim_case.json"
    )

    if candidate.exists():
        return candidate

    raise HTTPException(
        status_code=404,
        detail=f"Case '{case_id}' was not found.",
    )


def _extract_case_id(
    claim_case: dict[str, Any],
    fallback: str,
) -> str:
    """
    Extract the case identifier.
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

    return fallback


def _extract_patient_name(
    claim_case: dict[str, Any],
) -> str:
    """
    Extract patient display name without clinical
    interpretation.
    """

    direct_name = _safe_text(
        claim_case.get("patient_name")
    )

    if direct_name:
        return direct_name

    patient = claim_case.get("patient")

    if isinstance(patient, dict):
        nested_name = _safe_text(
            patient.get("name")
        )

        if nested_name:
            return nested_name

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


def _diagnosis_to_text(
    diagnosis: Any,
) -> str:
    """
    Convert a diagnosis field into text without
    interpreting its meaning.
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
    Copy the documented primary diagnosis.

    No diagnosis is inferred here.
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


def _find_submitted_document(
    case_id: str,
    file_name: str,
) -> Path:
    """
    Resolve one submitted source document for a claim case.

    Security / integrity rules:
    - the case must exist
    - the filename must be a plain filename, not a path
    - the file must be listed in claim_case.json submitted_documents
    - the resolved file must remain inside that case directory
    - the file must exist
    """

    clean_file_name = _safe_text(
        file_name
    )

    if (
        not clean_file_name
        or Path(clean_file_name).name
        != clean_file_name
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid source-document filename.",
        )

    case_file = _find_case_file(
        case_id
    )

    claim_case = _load_json_file(
        case_file
    )

    submitted_documents = claim_case.get(
        "submitted_documents",
        [],
    )

    if not isinstance(
        submitted_documents,
        list,
    ):
        submitted_documents = []

    allowed_file_names = {
        _safe_text(
            document.get("file_name")
        )
        for document in submitted_documents
        if isinstance(document, dict)
        and _safe_text(
            document.get("file_name")
        )
    }

    if clean_file_name not in allowed_file_names:
        raise HTTPException(
            status_code=404,
            detail=(
                "The requested document is not listed "
                "for this claim case."
            ),
        )

    case_directory = case_file.parent.resolve()

    document_path = (
        case_directory
        / clean_file_name
    ).resolve()

    try:
        document_path.relative_to(
            case_directory
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid source-document path.",
        ) from exc

    if not document_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=(
                "The requested source document "
                "was not found."
            ),
        )

    return document_path


def _get_all_case_directories() -> list[Path]:
    """
    Return available claim-case directories.
    """

    if not CLAIM_CASES_DIR.exists():
        return []

    return sorted(
        path
        for path in CLAIM_CASES_DIR.iterdir()
        if (
            path.is_dir()
            and path.name.startswith("case_")
        )
    )


# =====================================================
# Root Endpoint
# =====================================================

@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": (
            "Claim Review Intelligence Platform"
        ),
        "status": "running",
        "version": "1.5.0",
    }


# =====================================================
# Health Endpoint
# =====================================================

@app.get(
    "/health",
    response_model=HealthResponse,
)
def health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service=(
            "Claim Review Intelligence Platform"
        ),
        version="1.5.0",
    )


# =====================================================
# Case List Endpoint
# =====================================================

@app.get(
    "/api/v1/cases",
    response_model=CaseListResponse,
)
def list_cases() -> CaseListResponse:
    """
    Return all locally available fictional claim cases.
    """

    cases: list[CaseSummary] = []

    for case_directory in (
        _get_all_case_directories()
    ):
        case_file = (
            case_directory / "claim_case.json"
        )

        if not case_file.exists():
            continue

        try:
            claim_case = _load_json_file(
                case_file
            )

        except HTTPException:
            continue

        folder_case_id = (
            case_directory.name.replace(
                "case_",
                "",
            )
        )

        cases.append(
            CaseSummary(
                case_id=_extract_case_id(
                    claim_case,
                    fallback=folder_case_id,
                ),
                patient_name=(
                    _extract_patient_name(
                        claim_case
                    )
                ),
                primary_diagnosis=(
                    _extract_primary_diagnosis(
                        claim_case
                    )
                ),
            )
        )

    return CaseListResponse(
        cases=cases
    )


# =====================================================
# Case Detail Endpoint
# =====================================================

@app.get(
    "/api/v1/cases/{case_id}",
    response_model=CaseDetailResponse,
)
def get_case(
    case_id: str,
) -> CaseDetailResponse:
    """
    Return the complete claim case.

    This endpoint performs no AI review.
    """

    case_file = _find_case_file(
        case_id
    )

    claim_case = _load_json_file(
        case_file
    )

    normalized_case_id = (
        case_id
        .replace("case_", "")
        .replace("CASE_", "")
    )

    resolved_case_id = _extract_case_id(
        claim_case,
        fallback=normalized_case_id,
    )

    return CaseDetailResponse(
        case_id=resolved_case_id,
        patient_case=claim_case,
    )


# =====================================================
# Submitted Source Document Endpoint
# =====================================================

@app.get(
    "/api/v1/cases/{case_id}/documents/{file_name}",
    response_class=FileResponse,
)
def get_submitted_document(
    case_id: str,
    file_name: str,
) -> FileResponse:
    """
    Return one submitted fictional source document.

    The document is served inline so a reviewer hyperlink can
    open it directly in a separate browser tab.

    Only filenames explicitly listed in the selected case's
    submitted_documents inventory are accessible.
    """

    document_path = _find_submitted_document(
        case_id=case_id,
        file_name=file_name,
    )

    return FileResponse(
        path=document_path,
        media_type="text/plain; charset=utf-8",
        filename=document_path.name,
        content_disposition_type="inline",
    )


# =====================================================
# Multi-Agent Claim Review Endpoint
# =====================================================

@app.post(
    "/api/v1/cases/{case_id}/review",
    response_model=ClaimReviewResponse,
)
def start_review(
    case_id: str,
    request: ReviewRequest | None = None,
) -> ClaimReviewResponse:
    """
    Run the CRIP multi-agent claim-review workflow.

    Agent 1:
        Claim pattern analysis

    Agent 2:
        Documentation, policy, and evidence verification

    Agent 3:
        Human-safe claim-review synthesis

    The API layer does not independently make claim,
    coverage, coding, medical-necessity, or clinical decisions.
    """

    case_file = _find_case_file(
        case_id
    )

    claim_case = _load_json_file(
        case_file
    )

    try:
        review_result = (
            generate_claim_review(
                claim_case=claim_case,
            )
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "The multi-agent claim review "
                "could not be completed."
            ),
        ) from exc

    return ClaimReviewResponse(
        **review_result
    )