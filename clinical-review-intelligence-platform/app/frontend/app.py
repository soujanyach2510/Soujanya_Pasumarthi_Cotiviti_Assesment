from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from api_client import (
    CripApiClient,
    CripApiConnectionError,
    CripApiDataError,
    CripApiError,
    CripApiResponseError,
    CripApiTimeoutError,
)


# =====================================================
# Streamlit Configuration
# =====================================================

st.set_page_config(
    page_title="CRIP | Claim Review Intelligence Platform",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =====================================================
# API Configuration
# =====================================================

API_BASE_URL = os.getenv(
    "CRIP_API_BASE_URL",
    "http://127.0.0.1:8000",
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLAIM_CASES_DIR = PROJECT_ROOT / "claim_cases"


# =====================================================
# Application Constants
# =====================================================

REVIEW_STATUSES = {
    "pending": "Pending Review",
    "in_progress": "Review in Progress",
    "awaiting_human_review": "Awaiting Human Review",
    "completed": "Review Completed",
    "requires_attention": "Requires Attention",
}

NAVIGATION_OPTIONS = [
    "Case Overview",
    "AI Review",
    "Human Decision",
]


# =====================================================
# Styling
# =====================================================

def apply_enterprise_styles() -> None:
    """Apply enterprise healthcare application styling."""

    st.markdown(
        """
        <style>
        .stApp {
            background-color: #f4f7fb;
        }

        .block-container {
            max-width: 1320px;
            padding-top: 0.35rem;
            padding-bottom: 2.25rem;
            padding-left: 1.35rem;
            padding-right: 1.35rem;
        }

        header[data-testid="stHeader"] {
            background: transparent;
            height: 0rem;
        }

        div[data-testid="stAppViewBlockContainer"] {
            padding-top: 0.35rem;
        }

        div[data-testid="stVerticalBlock"] {
            gap: 0.75rem;
        }

        html,
        body,
        [class*="css"] {
            font-family:
                Inter,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                sans-serif;
        }

        section[data-testid="stSidebar"] {
            background-color: #102f4a;
            border-right: 1px solid #244b66;
        }

        section[data-testid="stSidebar"] * {
            color: #f4f7fb;
        }

        .sidebar-brand {
            margin-bottom: 1.5rem;
        }

        .sidebar-brand-title {
            color: #ffffff;
            font-size: 1.65rem;
            font-weight: 800;
            letter-spacing: 0.01em;
        }

        .sidebar-brand-subtitle {
            color: #d3dfeb;
            font-size: 0.82rem;
            line-height: 1.4;
            margin-top: 0.25rem;
        }

        .sidebar-section-title {
            color: #c7d5e2;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            margin-bottom: 0.45rem;
            margin-top: 1.25rem;
            text-transform: uppercase;
        }

        .sidebar-case-card {
            background: linear-gradient(
                145deg,
                rgba(255, 255, 255, 0.12),
                rgba(255, 255, 255, 0.06)
            );
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 12px;
            margin-top: 0.45rem;
            padding: 0.9rem;
        }

        .sidebar-case-kicker {
            color: #a9c3d7;
            font-size: 0.68rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .sidebar-case-id {
            color: #ffffff;
            font-size: 1rem;
            font-weight: 800;
            margin-top: 0.25rem;
        }

        .sidebar-case-name {
            color: #d9e7f2;
            font-size: 0.82rem;
            margin-top: 0.12rem;
        }

        .sidebar-case-status {
            background-color: rgba(255, 255, 255, 0.12);
            border-radius: 999px;
            color: #ffffff;
            display: inline-block;
            font-size: 0.67rem;
            font-weight: 750;
            margin-top: 0.65rem;
            padding: 0.3rem 0.55rem;
        }

        .sidebar-note {
            color: #b8cad8;
            font-size: 0.72rem;
            line-height: 1.5;
            margin-top: 1.25rem;
        }

        .page-title {
            color: #102a43;
            font-size: 1.85rem;
            font-weight: 800;
            line-height: 1.2;
        }

        .page-subtitle {
            color: #5f7d99;
            font-size: 0.92rem;
            margin-top: 0.2rem;
        }

        .status-pill {
            border-radius: 999px;
            display: inline-block;
            font-size: 0.8rem;
            font-weight: 800;
            padding: 0.55rem 0.9rem;
        }

        .status-pending {
            background-color: #fff7df;
            border: 1px solid #e9ba43;
            color: #865b00;
        }

        .status-progress {
            background-color: #eaf3fb;
            border: 1px solid #76a8cb;
            color: #24577a;
        }

        .status-completed {
            background-color: #e7f7ed;
            border: 1px solid #62b981;
            color: #176d3b;
        }

        .status-attention {
            background-color: #fdeeee;
            border: 1px solid #d88181;
            color: #8f2d2d;
        }

        .status-awaiting {
            background-color: #fff7df;
            border: 1px solid #e1b54a;
            color: #7a5600;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #ffffff;
            border-color: #d7e1ea;
            border-radius: 14px;
        }

        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #d7e1ea;
            border-radius: 12px;
            min-height: 115px;
            padding: 1rem;
        }

        div[data-testid="stMetricLabel"] {
            color: #68839c;
            font-size: 0.75rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        div[data-testid="stMetricValue"] {
            color: #102a43;
            font-size: 1.15rem;
            font-weight: 800;
        }

        div.stButton > button {
            border-radius: 8px;
            font-weight: 750;
            min-height: 2.75rem;
        }

        div.stButton > button[kind="primary"] {
            background-color: #17628f;
            border-color: #17628f;
        }

        div.stButton > button[kind="primary"]:hover {
            background-color: #104e74;
            border-color: #104e74;
        }

        section[data-testid="stSidebar"] div.stButton > button {
            background-color: #ffffff !important;
            border: 1px solid #d7e1ea !important;
            color: #17324d !important;
        }

        section[data-testid="stSidebar"] div.stButton > button * {
            color: #17324d !important;
            opacity: 1 !important;
        }

        section[data-testid="stSidebar"] div.stButton > button:hover {
            background-color: #eef4f8 !important;
            border-color: #9fb6c8 !important;
            color: #102f4a !important;
        }

        div[data-testid="stAlert"] {
            border-radius: 10px;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            box-shadow: 0 1px 2px rgba(16, 42, 67, 0.04);
        }

        div[data-testid="stMetric"] {
            box-shadow: 0 1px 2px rgba(16, 42, 67, 0.035);
        }

        button[data-baseweb="tab"] {
            font-weight: 700;
        }

        .workspace-kicker {
            color: #17628f;
            font-size: 0.7rem;
            font-weight: 800;
            letter-spacing: 0.09em;
            text-transform: uppercase;
        }

        .progress-panel {
            background: linear-gradient(135deg, #eef7fc, #f7fbfd);
            border: 1px solid #b8d8eb;
            border-radius: 12px;
            padding: 1rem 1.1rem;
        }

        .progress-title {
            color: #123e5b;
            font-size: 1rem;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }

        .progress-text {
            color: #46677f;
            font-size: 0.82rem;
            line-height: 1.5;
        }

        #MainMenu {
            visibility: hidden;
        }

        footer {
            visibility: hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =====================================================
# API Access
# =====================================================

@st.cache_data(
    ttl=5,
    show_spinner=False,
)
def get_api_health() -> dict[str, Any]:
    """Retrieve the current backend health status."""

    with CripApiClient(
        base_url=API_BASE_URL,
    ) as client:
        return client.get_health()


@st.cache_data(
    ttl=10,
    show_spinner=False,
)
def get_case_summaries() -> list[dict[str, Any]]:
    """Retrieve claim-case summaries."""

    with CripApiClient(
        base_url=API_BASE_URL,
    ) as client:
        return client.get_cases()


@st.cache_data(
    ttl=10,
    show_spinner=False,
)
def get_claim_case(
    case_id: str,
) -> dict[str, Any]:
    """Retrieve one complete claim case."""

    with CripApiClient(
        base_url=API_BASE_URL,
    ) as client:
        return client.get_case(case_id)


def request_claim_review(
    case_id: str,
) -> dict[str, Any]:
    """Request a claim review from the FastAPI backend."""

    review_focus = (
        "Evaluate the submitted claim, billed observation service, "
        "supporting encounter evidence, payer-policy context, coding "
        "guidance, and relevant clinical documentation."
    )

    with CripApiClient(
        base_url=API_BASE_URL,
    ) as client:
        return client.start_review(
            case_id=case_id,
            review_focus=review_focus,
        )


def clear_case_cache() -> None:
    """Clear cached backend data."""

    get_api_health.clear()
    get_case_summaries.clear()
    get_claim_case.clear()


# =====================================================
# Session State
# =====================================================

def initialize_session_state() -> None:
    """Initialize required Streamlit session values."""

    defaults = {
        "active_page": "Case Overview",
        "selected_case_id": None,
        "review_started": False,
        "review_status": "pending",
        "review_result": None,
        "review_error": None,
        "review_requested": False,
        "final_decision": None,
        "final_rationale": "",
        "decision_submitted": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_review_state() -> None:
    """Reset the review workflow when the case changes."""

    st.session_state.active_page = "Case Overview"
    st.session_state.review_started = False
    st.session_state.review_status = "pending"
    st.session_state.review_result = None
    st.session_state.review_error = None
    st.session_state.review_requested = False
    st.session_state.final_decision = None
    st.session_state.final_rationale = ""
    st.session_state.decision_submitted = False


def complete_review_request(
    review_result: dict[str, Any],
) -> None:
    """Store a completed AI review in session state."""

    st.session_state.review_started = True
    st.session_state.review_status = "awaiting_human_review"
    st.session_state.review_result = review_result
    st.session_state.review_error = None
    st.session_state.review_requested = False
    st.session_state.active_page = "AI Review"
    st.session_state.final_decision = None
    st.session_state.final_rationale = ""
    st.session_state.decision_submitted = False


# =====================================================
# Formatting and Normalization
# =====================================================

def safe_value(
    value: Any,
    default: str = "Not documented",
) -> str:
    """Return a clean value for display."""

    if value is None:
        return default

    text = str(value).strip()

    return text if text else default


def format_date(
    value: str | None,
    include_time: bool = False,
) -> str:
    """Format supported ISO date values."""

    if not value:
        return "Not documented"

    supported_formats = (
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
    )

    normalized_value = value.replace(
        "Z",
        "+00:00",
    )

    for date_format in supported_formats:
        try:
            parsed_date = datetime.strptime(
                normalized_value,
                date_format,
            )

            if include_time:
                return parsed_date.strftime(
                    "%b %d, %Y at %I:%M %p"
                )

            return parsed_date.strftime(
                "%b %d, %Y"
            )

        except ValueError:
            continue

    return value


def format_confidence(
    confidence: Any,
) -> str:
    """Format either text or numeric confidence values."""

    if confidence is None:
        return "Not available"

    if isinstance(confidence, str):
        normalized = confidence.strip()

        if not normalized:
            return "Not available"

        if normalized.lower() in {
            "high",
            "medium",
            "low",
        }:
            return normalized.title()

        try:
            confidence_value = float(normalized)
        except ValueError:
            return normalized
    else:
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            return "Not available"

    if 0 <= confidence_value <= 1:
        return f"{confidence_value * 100:.0f}%"

    return f"{confidence_value:.0f}%"


def diagnosis_to_text(
    diagnosis: Any,
) -> str:
    """Convert a diagnosis field into readable display text."""

    if isinstance(diagnosis, str):
        return safe_value(diagnosis)

    if isinstance(diagnosis, dict):
        for key in (
            "description",
            "name",
            "diagnosis",
            "label",
            "display",
            "text",
        ):
            value = diagnosis.get(key)

            if value:
                return safe_value(value)

    return "Not documented"


def normalize_case_data(
    raw_case: dict[str, Any],
) -> dict[str, Any]:
    """Normalize backend patient-case data for the UI."""

    patient = raw_case.get(
        "patient",
        {},
    )

    encounter = raw_case.get(
        "encounter",
        {},
    )

    review = raw_case.get(
        "review",
        {},
    )

    claim = raw_case.get(
        "claim",
        {},
    )

    if not isinstance(claim, dict):
        claim = {}

    return {
        "case_id": raw_case.get(
            "case_id",
            raw_case.get("id", "Unknown"),
        ),
        "claim_id": claim.get(
            "claim_id",
            "Not documented",
        ),
        "payer": claim.get(
            "payer",
            "Not documented",
        ),
        "provider": claim.get(
            "provider",
            "Not documented",
        ),
        "claim_type": claim.get(
            "claim_type",
            "Not documented",
        ),
        "service_category": claim.get(
            "service_category",
            "Not documented",
        ),
        "service_code": claim.get(
            "service_code",
            "Not documented",
        ),
        "place_of_service": claim.get(
            "place_of_service",
            "Not documented",
        ),
        "service_date": claim.get(
            "service_date",
        ),
        "billed_units": claim.get(
            "billed_units",
        ),
        "billed_amount": claim.get(
            "billed_amount",
        ),
        "claim_status": claim.get(
            "claim_status",
            "Pending Review",
        ),
        "patient_id": patient.get(
            "patient_id",
            raw_case.get(
                "patient_id",
                "Not documented",
            ),
        ),
        "patient_name": patient.get(
            "name",
            raw_case.get(
                "patient_name",
                "Not documented",
            ),
        ),
        "age": patient.get(
            "age",
            raw_case.get("age"),
        ),
        "sex": patient.get(
            "sex",
            raw_case.get("sex"),
        ),
        "primary_diagnosis": diagnosis_to_text(
            encounter.get(
                "primary_diagnosis",
                raw_case.get(
                    "primary_diagnosis",
                    "Not documented",
                ),
            )
        ),
        "encounter_type": encounter.get(
            "encounter_type",
            raw_case.get(
                "encounter_type",
                "Not documented",
            ),
        ),
        "admission_date": encounter.get(
            "admission_date",
            raw_case.get("admission_date"),
        ),
        "discharge_date": encounter.get(
            "discharge_date",
            raw_case.get("discharge_date"),
        ),
        "review_reason": review.get(
            "reason",
            raw_case.get(
                "review_reason",
                "Claim documentation review",
            ),
        ),
        "priority": review.get(
            "priority",
            raw_case.get(
                "priority",
                "Standard",
            ),
        ),
        "status": review.get(
            "status",
            raw_case.get(
                "status",
                "pending",
            ),
        ),
        "clinical_summary": raw_case.get(
            "clinical_summary",
            encounter.get(
                "clinical_summary",
                "",
            ),
        ),
        "comorbidities": raw_case.get(
            "comorbidities",
            patient.get(
                "comorbidities",
                [],
            ),
        ),
        "timeline": raw_case.get(
            "timeline",
            encounter.get(
                "timeline",
                [],
            ),
        ),
        "clinical_documents": raw_case.get(
            "clinical_documents",
            [],
        ),
        "submitted_documents": raw_case.get(
            "submitted_documents",
            [],
        ),
    }


# =====================================================
# API Error Handling
# =====================================================

def display_api_error(
    error: Exception,
) -> None:
    """Display a clear backend error."""

    if isinstance(
        error,
        CripApiConnectionError,
    ):
        st.error(
            "CRIP could not connect to the FastAPI backend."
        )

        st.info(
            "Run the backend from the project root:\n\n"
            "`python -m uvicorn app.backend.main:app "
            "--reload --port 8000`"
        )

    elif isinstance(
        error,
        CripApiTimeoutError,
    ):
        st.error(
            "The backend took too long to complete the request."
        )

    elif isinstance(
        error,
        CripApiResponseError,
    ):
        st.error(
            f"The backend returned an error: {error}"
        )

    elif isinstance(
        error,
        CripApiDataError,
    ):
        st.error(
            f"The backend returned unexpected data: {error}"
        )

    elif isinstance(
        error,
        CripApiError,
    ):
        st.error(
            f"An API error occurred: {error}"
        )

    else:
        st.error(
            f"An unexpected application error occurred: {error}"
        )


# =====================================================
# Claim Review Request
# =====================================================

def queue_claim_review() -> None:
    """Move the UI into a visible in-progress state."""

    st.session_state.review_started = True
    st.session_state.review_status = "in_progress"
    st.session_state.review_result = None
    st.session_state.review_error = None
    st.session_state.review_requested = True
    st.session_state.active_page = "AI Review"
    st.session_state.final_decision = None
    st.session_state.final_rationale = ""
    st.session_state.decision_submitted = False


def run_claim_review(
    case_id: str,
) -> bool:
    """Run the backend claim review and store its result."""

    try:
        with st.spinner(
            "Analyzing the claim, supporting documentation, "
            "and retrieved guidance..."
        ):
            review_result = request_claim_review(
                case_id=case_id,
            )

        complete_review_request(
            review_result=review_result,
        )

        return True

    except Exception as exc:
        st.session_state.review_error = str(exc)
        st.session_state.review_requested = False
        st.session_state.review_status = "requires_attention"
        display_api_error(exc)
        return False


# =====================================================
# Sidebar
# =====================================================

def case_option_label(
    case_summary: dict[str, Any],
) -> str:
    """Create a readable case-selector label."""

    case_id = safe_value(
        case_summary.get("case_id")
    )

    patient_name = safe_value(
        case_summary.get("patient_name")
    )

    return f"Case #{case_id} — {patient_name}"


def render_sidebar(
    case_summaries: list[dict[str, Any]],
) -> None:
    """Render compact case context and workspace navigation."""

    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="sidebar-brand-title">CRIP</div>
                <div class="sidebar-brand-subtitle">
                    Claim Review Intelligence Platform
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="sidebar-section-title">Claim Case</div>',
            unsafe_allow_html=True,
        )

        if not case_summaries:
            st.warning(
                "No claim cases are available."
            )

        else:
            case_lookup = {
                case_option_label(case): case
                for case in case_summaries
            }

            case_labels = list(
                case_lookup.keys()
            )

            current_case_id = (
                st.session_state.selected_case_id
            )

            default_index = 0

            for index, case_label in enumerate(
                case_labels
            ):
                case_id = str(
                    case_lookup[
                        case_label
                    ].get("case_id")
                )

                if case_id == str(
                    current_case_id
                ):
                    default_index = index
                    break

            if len(case_labels) > 1:
                selected_label = st.radio(
                    "Choose claim case",
                    options=case_labels,
                    index=default_index,
                    key="claim_case_selector",
                )
            else:
                selected_label = case_labels[0]

            selected_summary = (
                case_lookup[
                    selected_label
                ]
            )

            selected_case_id = str(
                selected_summary.get(
                    "case_id"
                )
            )

            if (
                selected_case_id
                != st.session_state.selected_case_id
            ):
                st.session_state.selected_case_id = (
                    selected_case_id
                )

                reset_review_state()
                st.rerun()

            patient_name = safe_value(
                selected_summary.get(
                    "patient_name"
                )
            )

            primary_diagnosis = safe_value(
                selected_summary.get(
                    "primary_diagnosis"
                )
            )

            review_status = REVIEW_STATUSES.get(
                st.session_state.review_status,
                "Pending Review",
            )

            st.markdown(
                f"""
                <div class="sidebar-case-card">
                    <div class="sidebar-case-kicker">
                        Selected case
                    </div>
                    <div class="sidebar-case-id">
                        Case #{selected_case_id}
                    </div>
                    <div class="sidebar-case-name">
                        {patient_name}
                    </div>
                    <div class="sidebar-case-name">
                        {primary_diagnosis}
                    </div>
                    <div class="sidebar-case-status">
                        {review_status}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div class="sidebar-section-title">Review Workspace</div>',
            unsafe_allow_html=True,
        )

        selected_page = st.radio(
            "Review navigation",
            options=NAVIGATION_OPTIONS,
            index=NAVIGATION_OPTIONS.index(
                st.session_state.active_page
            ),
            label_visibility="collapsed",
        )

        st.session_state.active_page = selected_page

        if st.button(
            "Refresh Case",
            use_container_width=True,
        ):
            clear_case_cache()
            st.rerun()

        st.markdown(
            """
            <div class="sidebar-note">
                AI-generated findings are advisory and require
                confirmation by a qualified human reviewer.
            </div>
            """,
            unsafe_allow_html=True,
        )


# =====================================================
# Header
# =====================================================

def get_status_css_class(
    review_status: str,
) -> str:
    """Return the CSS class for the review status."""

    status_classes = {
        "pending": "status-pending",
        "in_progress": "status-progress",
        "awaiting_human_review": "status-awaiting",
        "completed": "status-completed",
        "requires_attention": "status-attention",
    }

    return status_classes.get(
        review_status,
        "status-pending",
    )


def render_application_header(
    case: dict[str, Any],
) -> None:
    """Render the application header."""

    review_status = (
        st.session_state.review_status
    )

    status_label = REVIEW_STATUSES.get(
        review_status,
        safe_value(review_status).replace(
            "_",
            " ",
        ).title(),
    )

    status_css_class = get_status_css_class(
        review_status
    )

    with st.container(border=True):
        title_column, status_column = st.columns(
            [4, 1]
        )

        with title_column:
            st.markdown(
                '<div class="workspace-kicker">'
                "AI-ASSISTED CLAIM OPERATIONS"
                "</div>",
                unsafe_allow_html=True,
            )

            st.markdown(
                '<div class="page-title">'
                "Claim Review Workspace"
                "</div>",
                unsafe_allow_html=True,
            )


        with status_column:
            st.markdown(
                '<div style="text-align:right; padding-top:0.35rem;">'
                f'<span class="status-pill {status_css_class}">'
                f"{status_label}"
                "</span>"
                "</div>",
                unsafe_allow_html=True,
            )


# =====================================================
# Case Overview
# =====================================================

def render_claim_overview(
    case: dict[str, Any],
) -> None:
    """Render the submitted claim information first."""

    with st.container(border=True):
        st.subheader("Claim Overview")

        top_columns = st.columns(4)

        with top_columns[0]:
            st.metric(
                label="Claim ID",
                value=safe_value(
                    case.get("claim_id")
                ),
            )

        with top_columns[1]:
            st.metric(
                label="Payer",
                value=safe_value(
                    case.get("payer")
                ),
            )

        with top_columns[2]:
            st.metric(
                label="Service",
                value=safe_value(
                    case.get("service_category")
                ),
            )

        with top_columns[3]:
            billed_amount = case.get(
                "billed_amount"
            )

            if isinstance(
                billed_amount,
                (int, float),
            ):
                billed_value = (
                    f"${billed_amount:,.2f}"
                )
            else:
                billed_value = safe_value(
                    billed_amount
                )

            st.metric(
                label="Billed Amount",
                value=billed_value,
            )

        st.divider()

        detail_columns = st.columns(3)

        with detail_columns[0]:
            st.caption("CLAIM TYPE")
            st.markdown(
                f"**{safe_value(case.get('claim_type'))}**"
            )

            st.caption("SERVICE CODE")
            st.markdown(
                f"**{safe_value(case.get('service_code'))}**"
            )

        with detail_columns[1]:
            st.caption("PLACE OF SERVICE")
            st.markdown(
                f"**{safe_value(case.get('place_of_service'))}**"
            )

            st.caption("SERVICE DATE")
            st.markdown(
                f"**{format_date(case.get('service_date'))}**"
            )

        with detail_columns[2]:
            st.caption("PROVIDER")
            st.markdown(
                f"**{safe_value(case.get('provider'))}**"
            )

            st.caption("CLAIM STATUS")
            st.markdown(
                f"**{safe_value(case.get('claim_status'))}**"
            )


def render_patient_summary(
    case: dict[str, Any],
) -> None:
    """Render patient identity and summary metrics."""

    with st.container(border=True):
        st.subheader(
            safe_value(
                case["patient_name"]
            )
        )

        st.caption(
            f"Patient ID: "
            f"{safe_value(case['patient_id'])} "
            f"• Case #{safe_value(case['case_id'])}"
        )

    metric_columns = st.columns(4)

    with metric_columns[0]:
        st.metric(
            label="Age",
            value=safe_value(
                case["age"]
            ),
        )
        st.caption("Years")

    with metric_columns[1]:
        st.metric(
            label="Sex",
            value=safe_value(
                case["sex"]
            ),
        )
        st.caption("Documented demographic")

    with metric_columns[2]:
        st.metric(
            label="Encounter",
            value=safe_value(
                case["encounter_type"]
            ),
        )
        st.caption("Current care setting")

    with metric_columns[3]:
        st.metric(
            label="Priority",
            value=safe_value(
                case["priority"]
            ),
        )
        st.caption("Review priority")


def render_case_information(
    case: dict[str, Any],
) -> None:
    """Render diagnosis, dates, and review information."""

    st.subheader("Case Information")

    left_column, right_column = st.columns(2)

    with left_column:
        with st.container(border=True):
            st.caption("PRIMARY DIAGNOSIS")

            st.markdown(
                f"**{safe_value(case['primary_diagnosis'])}**"
            )

            st.divider()

            st.caption("ADMISSION DATE")

            st.markdown(
                f"**{format_date(case['admission_date'])}**"
            )

            if case.get("discharge_date"):
                st.divider()

                st.caption("DISCHARGE DATE")

                st.markdown(
                    f"**{format_date(case['discharge_date'])}**"
                )

    with right_column:
        with st.container(border=True):
            st.caption("REVIEW REASON")

            st.markdown(
                f"**{safe_value(case['review_reason'])}**"
            )

            st.divider()

            st.caption("CURRENT STATUS")

            current_status = REVIEW_STATUSES.get(
                st.session_state.review_status,
                "Pending Review",
            )

            st.markdown(
                f"**{current_status}**"
            )


def render_clinical_summary(
    case: dict[str, Any],
) -> None:
    """Render the clinical summary."""

    with st.container(border=True):
        st.subheader("Clinical Summary")

        summary = safe_value(
            case.get("clinical_summary"),
            "Clinical documentation is available for review.",
        )

        st.info(summary)


def render_clinical_timeline(
    case: dict[str, Any],
) -> None:
    """Render the clinical timeline."""

    with st.container(border=True):
        st.subheader("Clinical Timeline")

        timeline = case.get(
            "timeline",
            [],
        )

        if not timeline:
            st.info(
                "No clinical timeline events were documented."
            )
            return

        valid_events = [
            event
            for event in timeline
            if isinstance(event, dict)
        ]

        for index, event in enumerate(
            valid_events
        ):
            event_date = format_date(
                event.get("date")
                or event.get("timestamp"),
                include_time=True,
            )

            event_title = safe_value(
                event.get("title")
                or event.get("event"),
                "Clinical event",
            )

            event_description = safe_value(
                event.get("description")
                or event.get("details"),
                "No additional details were documented.",
            )

            st.caption(event_date)
            st.markdown(
                f"**{event_title}**"
            )
            st.write(event_description)

            if index < len(valid_events) - 1:
                st.divider()


def render_documented_conditions(
    case: dict[str, Any],
) -> None:
    """Render documented conditions."""

    with st.container(border=True):
        st.subheader(
            "Documented Conditions"
        )

        conditions = case.get(
            "comorbidities",
            [],
        )

        if not conditions:
            st.info(
                "No additional documented conditions were found."
            )
            return

        for condition in conditions:
            st.markdown(
                f"- {safe_value(condition)}"
            )


def render_review_action(
    case: dict[str, Any],
) -> None:
    """Render the claim-review action."""

    with st.container(border=True):
        st.subheader("Claim Review")

        st.write(
            "Initiate an AI-assisted claim review using submitted claim data, "
            "encounter evidence, payer policy, coding guidance, and relevant "
            "clinical guidance. All generated findings require human validation."
        )

        if st.session_state.decision_submitted:
            st.success(
                "The review has been completed and a human "
                "reviewer determination has been recorded."
            )
            return

        if st.session_state.review_result:
            st.success(
                "The claim analysis is complete and ready "
                "for human review."
            )

            if st.button(
                "Open AI Review",
                type="primary",
                use_container_width=True,
            ):
                st.session_state.active_page = "AI Review"
                st.rerun()

            return

        if st.button(
            "Start Claim Review",
            type="primary",
            use_container_width=True,
        ):
            queue_claim_review()
            st.rerun()


def render_case_overview(
    case: dict[str, Any],
) -> None:
    """Render the complete claim-case overview."""

    render_claim_overview(case)

    st.write("")

    render_patient_summary(case)

    st.write("")

    render_case_information(case)
    render_clinical_summary(case)

    left_column, right_column = st.columns(
        [1.15, 0.85],
        gap="large",
    )

    with left_column:
        render_clinical_timeline(case)

    with right_column:
        render_documented_conditions(case)
        render_review_action(case)


# =====================================================
# AI Review Components
# =====================================================

def render_review_summary(
    review_result: dict[str, Any],
) -> None:
    """Render the final claim-review advisory and reviewer actions."""

    with st.container(border=True):
        st.subheader("Advisory Review Summary")

        st.write(
            safe_value(
                review_result.get("advisory_summary"),
                "No advisory summary was returned.",
            )
        )

        documented_facts = review_result.get(
            "documented_facts",
            [],
        )

        if documented_facts:
            st.divider()
            st.markdown("**Documented facts**")

            for fact in documented_facts:
                st.markdown(
                    f"- {safe_value(fact)}"
                )

        reviewer_actions = review_result.get(
            "reviewer_actions",
            [],
        )

        if reviewer_actions:
            st.divider()
            st.markdown("**Human reviewer actions**")

            for item in reviewer_actions:
                if not isinstance(item, dict):
                    continue

                action = safe_value(
                    item.get("action")
                )
                related_finding = item.get(
                    "related_finding"
                )

                if related_finding:
                    st.markdown(
                        f"- **{action}** — "
                        f"{safe_value(related_finding)}"
                    )
                else:
                    st.markdown(
                        f"- **{action}**"
                    )

        if review_result.get(
            "human_validation_required"
        ):
            st.warning(
                "Human claim-review validation is required before "
                "a final reviewer determination is recorded."
            )


def render_review_metadata(
    review_result: dict[str, Any],
) -> None:
    """Render review metadata."""

    metadata_columns = st.columns(4)

    with metadata_columns[0]:
        st.metric(
            label="Review ID",
            value=safe_value(
                review_result.get("review_id")
            ),
        )

    with metadata_columns[1]:
        st.metric(
            label="Claim Findings",
            value=len(
                review_result.get(
                    "clinical_patterns",
                    [],
                )
            ),
        )

    with metadata_columns[2]:
        st.metric(
            label="Documentation Gaps",
            value=len(
                review_result.get(
                    "documentation_gaps",
                    [],
                )
            ),
        )

    with metadata_columns[3]:
        generated_at = format_date(
            safe_value(
                review_result.get("generated_at")
            ),
            include_time=True,
        )

        st.metric(
            label="Generated",
            value=generated_at,
        )


def render_clinical_patterns(
    patterns: list[dict[str, Any]],
) -> None:
    """Render verified claim-review patterns as compact expanders."""

    if not patterns:
        st.info(
            "No claim findings were generated."
        )
        return

    for index, pattern in enumerate(patterns, start=1):
        if not isinstance(pattern, dict):
            continue

        title = safe_value(
            pattern.get("title")
        )

        confidence = format_confidence(
            pattern.get("confidence")
        )

        with st.expander(
            f"{index}. {title} — Confidence: {confidence}",
            expanded=(index == 1),
        ):
            st.write(
                safe_value(
                    pattern.get("description")
                )
            )

            supporting_facts = pattern.get(
                "supporting_facts",
                [],
            )

            if supporting_facts:
                st.markdown(
                    "**Supporting documented facts**"
                )

                for fact in supporting_facts:
                    st.markdown(
                        f"- {safe_value(fact)}"
                    )

            source_references = pattern.get(
                "source_references",
                [],
            )

            if source_references:
                st.markdown(
                    "**Source references**"
                )

                for reference in source_references:
                    st.markdown(
                        f"- {safe_value(reference)}"
                    )

            if pattern.get(
                "human_validation_required"
            ):
                st.caption(
                    "Human validation required"
                )


def render_documentation_gaps(
    gaps: list[dict[str, Any]],
) -> None:
    """Render validated documentation gaps."""

    if not gaps:
        st.success(
            "No review-relevant documentation gaps were identified."
        )
        return

    for gap in gaps:
        if not isinstance(gap, dict):
            continue

        with st.container(border=True):
            title_column, status_column = st.columns(
                [4, 1]
            )

            with title_column:
                st.subheader(
                    safe_value(
                        gap.get("item")
                    )
                )

            with status_column:
                st.metric(
                    label="Status",
                    value=safe_value(
                        gap.get("verification_status")
                    ).replace("_", " ").title(),
                )

            st.write(
                safe_value(
                    gap.get("reason")
                )
            )

            affected_finding = gap.get(
                "affected_finding"
            )

            if affected_finding:
                st.markdown(
                    "**Affected finding:** "
                    f"{safe_value(affected_finding)}"
                )

            locations_checked = gap.get(
                "source_locations_checked",
                [],
            )

            if locations_checked:
                st.markdown(
                    "**Source locations checked**"
                )

                for location in locations_checked:
                    st.markdown(
                        f"- {safe_value(location)}"
                    )

            st.info(
                "Human verification step: "
                f"{safe_value(gap.get('human_verification_step'))}"
            )


def render_evidence_references(
    evidence_items: list[dict[str, Any]],
) -> None:
    """Render agent-generated evidence-to-finding mappings."""

    st.markdown("### Evidence References")

    if not evidence_items:
        st.info(
            "No evidence references were returned."
        )
        return

    for index, evidence in enumerate(
        evidence_items,
        start=1,
    ):
        if not isinstance(evidence, dict):
            continue

        source = safe_value(
            evidence.get("source"),
            f"Evidence reference {index}",
        )

        with st.expander(
            f"{index}. {source}"
        ):
            st.caption("DOCUMENTED FACT")
            st.write(
                safe_value(
                    evidence.get("documented_fact")
                )
            )

            st.caption("FINDING SUPPORTED")
            st.write(
                safe_value(
                    evidence.get("finding_supported")
                )
            )


def render_guidance_references(
    guidance_items: list[dict[str, Any]],
) -> None:
    """Render retrieved RAG guidance used by the review."""

    st.markdown("### Guidance Used")

    st.caption(
        "These references were retrieved from the local CRIP "
        "knowledge base and provided to the CrewAI workflow."
    )

    if not guidance_items:
        st.info(
            "No knowledge-base guidance references were returned."
        )
        return

    category_labels = {
        "clinical_guidelines": "Clinical Guidance",
        "payer_policies": "Payer Policy",
        "coding_rules": "Coding Guidance",
    }

    for item in guidance_items:
        if not isinstance(item, dict):
            continue

        category = safe_value(
            item.get("knowledge_category")
        )

        label = category_labels.get(
            category,
            category.replace("_", " ").title(),
        )

        source_file = safe_value(
            item.get("source_file")
        )

        score = item.get("score")

        if isinstance(score, (int, float)):
            score_text = f"{score:.3f}"
        else:
            score_text = "Not available"

        with st.container(border=True):
            left_column, right_column = st.columns(
                [4, 1]
            )

            with left_column:
                st.markdown(
                    f"**{label}**"
                )
                st.write(source_file)

            with right_column:
                st.metric(
                    label="Similarity",
                    value=score_text,
                )


def render_validation_result(
    validation: dict[str, Any] | None,
) -> None:
    """Render deterministic validation warnings."""

    st.markdown("### Validation")

    if not isinstance(validation, dict):
        st.info(
            "No deterministic validation result was returned."
        )
        return

    status = safe_value(
        validation.get("source_integrity"),
        "unknown",
    )

    warnings = validation.get(
        "warnings",
        [],
    )

    if (
        status.casefold() == "passed"
        and not warnings
    ):
        st.success(
            "Deterministic source-integrity validation passed."
        )
        return

    st.warning(
        "The AI review requires attention before a final "
        "human determination."
    )

    if isinstance(warnings, list):
        for warning in warnings:
            st.markdown(
                f"- {safe_value(warning)}"
            )


def render_submitted_source_documents(
    case: dict[str, Any],
) -> None:
    """
    Render hyperlinks to submitted case documents served by FastAPI.

    Each source document opens in a separate browser tab through the
    backend document endpoint.
    """

    st.markdown(
        "### Submitted Source Documents"
    )

    st.caption(
        "Open the original submitted records in a separate browser tab "
        "to verify AI findings against the source documentation."
    )

    submitted_documents = case.get(
        "submitted_documents",
        [],
    )

    if not isinstance(
        submitted_documents,
        list,
    ) or not submitted_documents:
        st.info(
            "No submitted source-document inventory is available "
            "for this case."
        )
        return

    valid_documents = [
        document
        for document in submitted_documents
        if isinstance(document, dict)
    ]

    if not valid_documents:
        st.info(
            "No readable submitted source documents were found."
        )
        return

    case_id = safe_value(
        case.get("case_id"),
        "",
    )

    for index, document in enumerate(
        valid_documents,
        start=1,
    ):
        document_type = safe_value(
            document.get("document_type"),
            f"Source Document {index}",
        )

        document_date = format_date(
            document.get("date")
        )

        file_name = safe_value(
            document.get("file_name"),
            "",
        )

        document_id = safe_value(
            document.get("document_id")
        )

        with st.container(border=True):
            detail_column, action_column = st.columns(
                [4, 1]
            )

            with detail_column:
                st.markdown(
                    f"**{index}. {document_type}**"
                )

                metadata_parts = []

                if document_date != "Not documented":
                    metadata_parts.append(
                        document_date
                    )

                if document_id != "Not documented":
                    metadata_parts.append(
                        document_id
                    )

                if file_name:
                    metadata_parts.append(
                        file_name
                    )

                if metadata_parts:
                    st.caption(
                        " • ".join(
                            metadata_parts
                        )
                    )

            if not case_id or not file_name:
                with action_column:
                    st.caption(
                        "Source file unavailable"
                    )
                continue

            document_url = (
                f"{API_BASE_URL.rstrip('/')}"
                f"/api/v1/cases/{case_id}"
                f"/documents/{file_name}"
            )

            with action_column:
                st.link_button(
                    "Open Document ↗",
                    document_url,
                    use_container_width=True,
                )



def render_source_evidence(
    evidence_items: list[dict[str, Any]],
) -> None:
    """Render grouped deterministic source traceability."""

    st.markdown("### Original Source Evidence")

    st.caption(
        "Source-record content is grouped for compact traceability "
        "while preserving every evidence item."
    )

    if not evidence_items:
        st.info(
            "No source evidence was returned."
        )
        return

    grouped_evidence: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for evidence in evidence_items:
        if not isinstance(evidence, dict):
            continue

        source_type = safe_value(
            evidence.get("source_type"),
            "Other Evidence",
        )

        grouped_evidence.setdefault(
            source_type,
            [],
        ).append(evidence)

    preferred_order = [
        "Claim",
        "Clinical Documentation",
        "Clinical Timeline",
        "Submitted Document",
    ]

    ordered_types = [
        source_type
        for source_type in preferred_order
        if source_type in grouped_evidence
    ]

    ordered_types.extend(
        source_type
        for source_type in grouped_evidence
        if source_type not in ordered_types
    )

    for source_type in ordered_types:
        items = grouped_evidence[
            source_type
        ]

        with st.expander(
            f"{source_type} — {len(items)} item"
            f"{'s' if len(items) != 1 else ''}"
        ):
            for index, evidence in enumerate(
                items
            ):
                evidence_id = safe_value(
                    evidence.get("evidence_id")
                )

                source_reference = safe_value(
                    evidence.get(
                        "source_reference"
                    )
                )

                st.markdown(
                    f"**{evidence_id} — "
                    f"{source_reference}**"
                )

                st.write(
                    safe_value(
                        evidence.get("content")
                    )
                )

                if index < len(items) - 1:
                    st.divider()


# =====================================================
# AI Review Page
# =====================================================

def render_ai_review(
    case: dict[str, Any],
) -> None:
    """Render the AI-assisted claim review."""

    with st.container(border=True):
        st.subheader(
            "AI-Assisted Claim Review"
        )

        st.write(
            "Review the overall AI summary, claim findings, missing or unclear "
            "documentation, retrieved guidance, validation checks, and source "
            "evidence before recording a human determination."
        )

    review_result = (
        st.session_state.review_result
    )

    if not review_result:
        if (
            st.session_state.review_status
            == "in_progress"
        ):
            st.markdown(
                """
                <div class="progress-panel">
                    <div class="progress-title">
                        Review in Progress
                    </div>
                    <div class="progress-text">
                        CRIP is retrieving claim-review guidance and running
                        the three-agent analysis. This local Ollama workflow
                        can take several minutes.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.write("")

            with st.status(
                "Running multi-agent claim review...",
                expanded=True,
                state="running",
            ) as status:
                st.write(
                    "1. Retrieving clinical, payer, and coding guidance"
                )
                st.write(
                    "2. Comparing billed services with supporting visit documentation"
                )
                st.write(
                    "3. Synthesizing a human-review advisory"
                )

                if st.session_state.review_requested:
                    review_succeeded = run_claim_review(
                        case_id=str(
                            case["case_id"]
                        ),
                    )

                    if review_succeeded:
                        status.update(
                            label=(
                                "AI review completed — "
                                "awaiting human review"
                            ),
                            state="complete",
                            expanded=False,
                        )
                        st.rerun()

            return

        if (
            st.session_state.review_status
            == "requires_attention"
        ):
            st.error(
                "The previous claim review could not be completed."
            )

            if st.session_state.review_error:
                st.caption(
                    st.session_state.review_error
                )

        else:
            st.info(
                "No AI-assisted claim review has been generated yet."
            )

        if st.button(
            "Start Claim Review",
            type="primary",
        ):
            queue_claim_review()
            st.rerun()

        return

    render_review_metadata(
        review_result
    )

    st.write("")

    (
        summary_tab,
        patterns_tab,
        gaps_tab,
        guidance_tab,
        evidence_tab,
    ) = st.tabs(
        [
            "Review Summary",
            "Claim Findings",
            "Documentation Gaps",
            "Guidance & Validation",
            "Evidence & Sources",
        ]
    )

    with summary_tab:
        st.caption(
            "Overall AI-assisted result of the claim review, including "
            "the main documented facts and recommended human-review actions."
        )

        render_review_summary(
            review_result
        )

        safety_notice = safe_value(
            review_result.get(
                "safety_notice"
            )
        )

        st.info(safety_notice)

    with patterns_tab:
        st.caption(
            "Findings showing where the billed claim information is supported "
            "by documentation from the patient's visit."
        )

        render_clinical_patterns(
            review_result.get(
                "clinical_patterns",
                [],
            )
        )

    with gaps_tab:
        st.caption(
            "Important information that the AI expected to find but could not "
            "confirm, or documentation that may be missing or unclear."
        )

        render_documentation_gaps(
            review_result.get(
                "documentation_gaps",
                [],
            )
        )

    with guidance_tab:
        st.caption(
            "Shows the clinical, payer, and coding guidance retrieved for the "
            "review, plus deterministic checks performed after the AI response."
        )

        render_guidance_references(
            review_result.get(
                "guidance_references",
                [],
            )
        )

        st.divider()

        render_validation_result(
            review_result.get(
                "validation"
            )
        )

    with evidence_tab:
        st.caption(
            "Maps each AI finding to supporting facts, lets the reviewer open "
            "the submitted source documents, and preserves source-record "
            "traceability for human verification."
        )

        render_evidence_references(
            review_result.get(
                "evidence_references",
                [],
            )
        )

        st.divider()

        render_submitted_source_documents(
            case
        )

        st.divider()

        render_source_evidence(
            review_result.get(
                "source_evidence",
                [],
            )
        )

    st.write("")

    if st.button(
        "Continue to Human Decision",
        type="primary",
    ):
        st.session_state.active_page = (
            "Human Decision"
        )
        st.rerun()


# =====================================================
# Human Decision Page
# =====================================================

def render_recorded_decision() -> None:
    """Render the submitted human reviewer decision."""

    st.success(
        "The human reviewer decision has been recorded successfully."
    )

    with st.container(border=True):
        st.subheader("Recorded Decision")

        st.caption("FINAL DETERMINATION")

        st.markdown(
            f"**{safe_value(st.session_state.final_decision)}**"
        )

        st.divider()

        st.caption("REVIEWER RATIONALE")

        st.write(
            safe_value(
                st.session_state.final_rationale
            )
        )


def render_human_decision(
    case: dict[str, Any],
) -> None:
    """Render the human reviewer decision page."""

    with st.container(border=True):
        st.subheader(
            "Human Review Decision"
        )

        st.write(
            "Record the final reviewer determination after evaluating "
            "the submitted claim, AI-generated claim-review patterns, "
            "retrieved guidance, validation warnings, supporting evidence, "
            "and advisory summary."
        )

    if st.session_state.decision_submitted:
        render_recorded_decision()
        return

    review_result = (
        st.session_state.review_result
    )

    if not review_result:
        st.warning(
            "Complete the AI-assisted claim review before "
            "recording a human decision."
        )
        return

    with st.container(border=True):
        st.caption("AI-ASSISTED ADVISORY SUMMARY")

        st.write(
            safe_value(
                review_result.get(
                    "advisory_summary"
                )
            )
        )

        pattern_count = len(
            review_result.get(
                "clinical_patterns",
                [],
            )
        )

        gap_count = len(
            review_result.get(
                "documentation_gaps",
                [],
            )
        )

        summary_columns = st.columns(2)

        with summary_columns[0]:
            st.metric(
                label="Verified Claim Patterns",
                value=pattern_count,
            )

        with summary_columns[1]:
            st.metric(
                label="Documentation Gaps",
                value=gap_count,
            )

        st.caption(
            "This AI-generated review is advisory. The qualified "
            "human reviewer remains responsible for the final "
            "determination."
        )

    with st.form(
        key="human_decision_form",
        clear_on_submit=False,
    ):
        decision = st.radio(
            "Reviewer determination",
            options=[
                "Accept review findings",
                "Accept with modifications",
                "Request additional review",
                "Unable to determine from available documentation",
            ],
            index=None,
        )

        rationale = st.text_area(
            "Reviewer rationale",
            placeholder=(
                "Document the evidence and reasoning supporting "
                "the final reviewer determination."
            ),
            height=170,
        )

        confirmation = st.checkbox(
            "I confirm that I reviewed the patient record, "
            "AI-generated claim-review patterns, supporting evidence, "
            "and documentation gaps, and accept responsibility "
            "for the final determination."
        )

        submitted = st.form_submit_button(
            "Submit Final Decision",
            type="primary",
        )

    if submitted:
        if not decision:
            st.error(
                "Select a reviewer determination."
            )
            return

        if len(rationale.strip()) < 20:
            st.error(
                "Enter a meaningful reviewer rationale "
                "of at least 20 characters."
            )
            return

        if not confirmation:
            st.error(
                "Confirm reviewer responsibility before submitting."
            )
            return

        st.session_state.review_status = "completed"
        st.session_state.final_decision = decision
        st.session_state.final_rationale = (
            rationale.strip()
        )
        st.session_state.decision_submitted = True

        st.rerun()


# =====================================================
# Main Application
# =====================================================

def main() -> None:
    """Run the CRIP Streamlit application."""

    apply_enterprise_styles()
    initialize_session_state()

    case_summaries: list[dict[str, Any]] = []

    try:
        get_api_health()
        case_summaries = get_case_summaries()

    except Exception as exc:
        render_sidebar(
            case_summaries=[],
        )

        display_api_error(exc)
        st.stop()

    if (
        st.session_state.selected_case_id is None
        and case_summaries
    ):
        st.session_state.selected_case_id = str(
            case_summaries[0]["case_id"]
        )

    render_sidebar(
        case_summaries=case_summaries,
    )

    if not case_summaries:
        st.warning(
            "The backend did not return any claim cases."
        )
        st.stop()

    try:
        raw_case = get_claim_case(
            st.session_state.selected_case_id
        )

        claim_case = normalize_case_data(
            raw_case
        )

    except Exception as exc:
        display_api_error(exc)
        st.stop()

    render_application_header(
        claim_case
    )

    active_page = (
        st.session_state.active_page
    )

    if active_page == "Case Overview":
        render_case_overview(
            claim_case
        )

    elif active_page == "AI Review":
        render_ai_review(
            claim_case
        )

    elif active_page == "Human Decision":
        render_human_decision(
            claim_case
        )


if __name__ == "__main__":
    main()