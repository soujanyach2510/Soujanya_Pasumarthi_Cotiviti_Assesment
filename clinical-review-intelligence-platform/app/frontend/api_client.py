from __future__ import annotations

from typing import Any

import requests
from requests import Response
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
)
from requests.exceptions import (
    JSONDecodeError,
    RequestException,
    Timeout,
)


# =====================================================
# API Configuration
# =====================================================

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"

CONNECT_TIMEOUT_SECONDS = 3

# Local Ollama + 3 sequential CrewAI agents may take
# several minutes to complete.
READ_TIMEOUT_SECONDS = 600

REQUEST_TIMEOUT = (
    CONNECT_TIMEOUT_SECONDS,
    READ_TIMEOUT_SECONDS,
)


# =====================================================
# API Exceptions
# =====================================================

class CripApiError(Exception):
    """Base exception for CRIP API client errors."""


class CripApiConnectionError(CripApiError):
    """Raised when the frontend cannot connect to FastAPI."""


class CripApiTimeoutError(CripApiError):
    """Raised when an API request exceeds its timeout."""


class CripApiResponseError(CripApiError):
    """Raised when the API returns an unsuccessful status."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code


class CripApiDataError(CripApiError):
    """Raised when the API returns invalid data."""


# =====================================================
# CRIP API Client
# =====================================================

class CripApiClient:
    """
    HTTP client for the CRIP FastAPI backend.

    The Streamlit frontend communicates only through
    the API and does not directly access backend files
    or agent services.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_API_BASE_URL,
    ) -> None:
        normalized_base_url = (
            base_url
            .strip()
            .rstrip("/")
        )

        if not normalized_base_url:
            raise ValueError(
                "The CRIP API base URL cannot be empty."
            )

        self.base_url = normalized_base_url
        self.session = requests.Session()

        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": (
                    "CRIP-Streamlit-Frontend/1.5"
                ),
            }
        )

    # =================================================
    # Session Lifecycle
    # =================================================

    def close(self) -> None:
        """Close the underlying HTTP session."""

        self.session.close()

    def __enter__(self) -> "CripApiClient":
        """Enter the API-client context manager."""

        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        """Close the API session."""

        self.close()

    # =================================================
    # Internal HTTP Helpers
    # =================================================

    def _build_url(
        self,
        endpoint: str,
    ) -> str:
        """Build a complete API URL."""

        normalized_endpoint = endpoint.strip()

        if not normalized_endpoint.startswith("/"):
            normalized_endpoint = (
                f"/{normalized_endpoint}"
            )

        return (
            f"{self.base_url}"
            f"{normalized_endpoint}"
        )

    @staticmethod
    def _extract_error_message(
        response: Response,
    ) -> str:
        """
        Extract a readable error message from a
        FastAPI response.
        """

        try:
            payload = response.json()

        except (ValueError, JSONDecodeError):
            payload = None

        if isinstance(payload, dict):
            detail = payload.get("detail")

            if (
                isinstance(detail, str)
                and detail.strip()
            ):
                return detail.strip()

            if isinstance(detail, list):
                messages: list[str] = []

                for item in detail:
                    if not isinstance(
                        item,
                        dict,
                    ):
                        continue

                    message = item.get("msg")

                    if isinstance(
                        message,
                        str,
                    ):
                        messages.append(
                            message
                        )

                if messages:
                    return "; ".join(
                        messages
                    )

            message = payload.get(
                "message"
            )

            if (
                isinstance(message, str)
                and message.strip()
            ):
                return message.strip()

        response_text = (
            response.text.strip()
        )

        if response_text:
            return response_text

        return (
            "CRIP API returned HTTP status "
            f"{response.status_code}."
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Send an HTTP request and return a validated
        JSON object.
        """

        url = self._build_url(
            endpoint
        )

        try:
            response = (
                self.session.request(
                    method=method,
                    url=url,
                    timeout=REQUEST_TIMEOUT,
                    **kwargs,
                )
            )

        except Timeout as exc:
            raise CripApiTimeoutError(
                "The CRIP API did not respond within "
                "the allowed time. Local multi-agent "
                "reviews may take several minutes."
            ) from exc

        except RequestsConnectionError as exc:
            raise CripApiConnectionError(
                "The Streamlit application could not "
                "connect to the CRIP API. Confirm that "
                "FastAPI is running on port 8000."
            ) from exc

        except RequestException as exc:
            raise CripApiConnectionError(
                "The request to the CRIP API could not "
                "be completed."
            ) from exc

        if not response.ok:
            error_message = (
                self._extract_error_message(
                    response
                )
            )

            raise CripApiResponseError(
                message=error_message,
                status_code=(
                    response.status_code
                ),
            )

        try:
            payload = response.json()

        except (
            ValueError,
            JSONDecodeError,
        ) as exc:
            raise CripApiDataError(
                "The CRIP API returned invalid JSON."
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise CripApiDataError(
                "The CRIP API response must contain "
                "a JSON object."
            )

        return payload

    # =================================================
    # Validation Helpers
    # =================================================

    @staticmethod
    def _require_fields(
        payload: dict[str, Any],
        required_fields: set[str],
        response_name: str,
    ) -> None:
        """
        Verify that required response fields exist.
        """

        missing_fields = (
            required_fields.difference(
                payload.keys()
            )
        )

        if missing_fields:
            formatted_fields = ", ".join(
                sorted(
                    missing_fields
                )
            )

            raise CripApiDataError(
                f"The {response_name} response is "
                f"missing required fields: "
                f"{formatted_fields}."
            )

    @staticmethod
    def _require_list_field(
        payload: dict[str, Any],
        field_name: str,
    ) -> None:
        """
        Ensure a response field contains a list.
        """

        if not isinstance(
            payload.get(field_name),
            list,
        ):
            raise CripApiDataError(
                "The claim review field "
                f"'{field_name}' must be a list."
            )

    # =================================================
    # Health
    # =================================================

    def get_health(
        self,
    ) -> dict[str, Any]:
        """Return FastAPI health information."""

        payload = self._request(
            method="GET",
            endpoint="/health",
        )

        self._require_fields(
            payload=payload,
            required_fields={
                "status",
                "service",
                "version",
            },
            response_name="health",
        )

        return payload

    # =================================================
    # Claim Cases
    # =================================================

    def get_cases(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return summaries for available claim cases.
        """

        payload = self._request(
            method="GET",
            endpoint="/api/v1/cases",
        )

        cases = payload.get(
            "cases"
        )

        if not isinstance(
            cases,
            list,
        ):
            raise CripApiDataError(
                "The cases response does not contain "
                "a valid cases list."
            )

        validated_cases: list[
            dict[str, Any]
        ] = []

        for case in cases:
            if not isinstance(
                case,
                dict,
            ):
                raise CripApiDataError(
                    "The cases response contains "
                    "an invalid case entry."
                )

            if "case_id" not in case:
                raise CripApiDataError(
                    "A case summary is missing "
                    "its case_id."
                )

            validated_cases.append(
                case
            )

        return validated_cases

    def get_case(
        self,
        case_id: str,
    ) -> dict[str, Any]:
        """Return one complete claim case."""

        normalized_case_id = (
            str(case_id).strip()
        )

        if not normalized_case_id:
            raise ValueError(
                "The claim case ID cannot "
                "be empty."
            )

        payload = self._request(
            method="GET",
            endpoint=(
                f"/api/v1/cases/"
                f"{normalized_case_id}"
            ),
        )

        # Current FastAPI response:
        #
        # {
        #     "case_id": "...",
        #     "patient_case": {...}
        # }

        patient_case = payload.get(
            "patient_case"
        )

        if not isinstance(
            patient_case,
            dict,
        ):
            raise CripApiDataError(
                "The API response does not "
                "contain a valid patient_case."
            )

        return patient_case

    # =================================================
    # Multi-Agent Review
    # =================================================

    def start_review(
        self,
        case_id: str,
        review_focus: str | None = None,
    ) -> dict[str, Any]:
        """
        Start the CRIP multi-agent claim review.

        The backend performs:

        Agent 1:
            Claim pattern analysis

        Agent 2:
            Evidence/documentation verification

        Agent 3:
            Structured human-safe synthesis
        """

        normalized_case_id = (
            str(case_id).strip()
        )

        if not normalized_case_id:
            raise ValueError(
                "The claim case ID cannot "
                "be empty."
            )

        request_body: dict[str, Any] = {}

        if review_focus is not None:
            normalized_review_focus = (
                review_focus.strip()
            )

            if normalized_review_focus:
                request_body[
                    "review_focus"
                ] = (
                    normalized_review_focus
                )

        payload = self._request(
            method="POST",
            endpoint=(
                f"/api/v1/cases/"
                f"{normalized_case_id}/review"
            ),
            json=request_body,
        )

        self._validate_review_response(
            payload
        )

        return payload

    # =================================================
    # Structured Review Validation
    # =================================================

    def _validate_review_response(
        self,
        payload: dict[str, Any],
    ) -> None:
        """
        Validate the current structured CRIP review
        response.
        """

        self._require_fields(
            payload=payload,
            required_fields={
                "review_id",
                "case_id",
                "patient_name",
                "review_status",
                "generated_at",
                "review_type",
                "primary_diagnosis",
                "documented_facts",
                "clinical_patterns",
                "documentation_gaps",
                "evidence_references",
                "guidance_references",
                "reviewer_actions",
                "advisory_summary",
                "human_validation_required",
                "source_evidence",
                "validation",
                "safety_notice",
            },
            response_name=(
                "claim review"
            ),
        )

        # ---------------------------------------------
        # Validate list fields
        # ---------------------------------------------

        list_fields = {
            "documented_facts",
            "clinical_patterns",
            "documentation_gaps",
            "evidence_references",
            "guidance_references",
            "reviewer_actions",
            "source_evidence",
        }

        for field_name in list_fields:
            self._require_list_field(
                payload=payload,
                field_name=field_name,
            )

        # ---------------------------------------------
        # Validate text fields
        # ---------------------------------------------

        advisory_summary = (
            payload.get(
                "advisory_summary"
            )
        )

        if not isinstance(
            advisory_summary,
            str,
        ):
            raise CripApiDataError(
                "The claim review "
                "'advisory_summary' must "
                "be a string."
            )

        safety_notice = payload.get(
            "safety_notice"
        )

        if not isinstance(
            safety_notice,
            str,
        ):
            raise CripApiDataError(
                "The claim review "
                "'safety_notice' must "
                "be a string."
            )

        # ---------------------------------------------
        # Validate human-review requirement
        # ---------------------------------------------

        human_validation_required = (
            payload.get(
                "human_validation_required"
            )
        )

        if not isinstance(
            human_validation_required,
            bool,
        ):
            raise CripApiDataError(
                "The claim review "
                "'human_validation_required' "
                "field must be a boolean."
            )

        # ---------------------------------------------
        # Clinical patterns
        # ---------------------------------------------

        clinical_patterns = (
            payload.get(
                "clinical_patterns",
                [],
            )
        )

        for index, pattern in enumerate(
            clinical_patterns
        ):
            if not isinstance(
                pattern,
                dict,
            ):
                raise CripApiDataError(
                    "Clinical pattern at "
                    f"index {index} must be "
                    "a JSON object."
                )

            required_pattern_fields = {
                "title",
                "description",
                "supporting_facts",
                "source_references",
                "confidence",
                "human_validation_required",
            }

            missing_pattern_fields = (
                required_pattern_fields.difference(
                    pattern.keys()
                )
            )

            if missing_pattern_fields:
                formatted_fields = (
                    ", ".join(
                        sorted(
                            missing_pattern_fields
                        )
                    )
                )

                raise CripApiDataError(
                    "A clinical pattern is "
                    "missing fields: "
                    f"{formatted_fields}."
                )

            if not isinstance(
                pattern.get(
                    "supporting_facts"
                ),
                list,
            ):
                raise CripApiDataError(
                    "Clinical pattern "
                    "'supporting_facts' must "
                    "be a list."
                )

            if not isinstance(
                pattern.get(
                    "source_references"
                ),
                list,
            ):
                raise CripApiDataError(
                    "Clinical pattern "
                    "'source_references' must "
                    "be a list."
                )

        # ---------------------------------------------
        # Documentation gaps
        # ---------------------------------------------

        documentation_gaps = (
            payload.get(
                "documentation_gaps",
                [],
            )
        )

        for index, gap in enumerate(
            documentation_gaps
        ):
            if not isinstance(
                gap,
                dict,
            ):
                raise CripApiDataError(
                    "Documentation gap at "
                    f"index {index} must be "
                    "a JSON object."
                )

            required_gap_fields = {
                "item",
                "reason",
                "source_locations_checked",
                "human_verification_step",
                "verification_status",
            }

            missing_gap_fields = (
                required_gap_fields.difference(
                    gap.keys()
                )
            )

            if missing_gap_fields:
                formatted_fields = (
                    ", ".join(
                        sorted(
                            missing_gap_fields
                        )
                    )
                )

                raise CripApiDataError(
                    "A documentation gap is "
                    "missing fields: "
                    f"{formatted_fields}."
                )

        # ---------------------------------------------
        # Evidence references
        # ---------------------------------------------

        evidence_references = (
            payload.get(
                "evidence_references",
                [],
            )
        )

        for index, evidence in enumerate(
            evidence_references
        ):
            if not isinstance(
                evidence,
                dict,
            ):
                raise CripApiDataError(
                    "Evidence reference at "
                    f"index {index} must be "
                    "a JSON object."
                )

            required_evidence_fields = {
                "source",
                "documented_fact",
                "finding_supported",
            }

            missing_evidence_fields = (
                required_evidence_fields.difference(
                    evidence.keys()
                )
            )

            if missing_evidence_fields:
                formatted_fields = (
                    ", ".join(
                        sorted(
                            missing_evidence_fields
                        )
                    )
                )

                raise CripApiDataError(
                    "An evidence reference is "
                    "missing fields: "
                    f"{formatted_fields}."
                )

        # ---------------------------------------------
        # Guidance references
        # ---------------------------------------------

        guidance_references = (
            payload.get(
                "guidance_references",
                [],
            )
        )

        for index, guidance in enumerate(
            guidance_references
        ):
            if not isinstance(
                guidance,
                dict,
            ):
                raise CripApiDataError(
                    "Guidance reference at "
                    f"index {index} must be "
                    "a JSON object."
                )

            required_guidance_fields = {
                "source_file",
                "knowledge_category",
                "score",
            }

            missing_guidance_fields = (
                required_guidance_fields.difference(
                    guidance.keys()
                )
            )

            if missing_guidance_fields:
                formatted_fields = ", ".join(
                    sorted(
                        missing_guidance_fields
                    )
                )

                raise CripApiDataError(
                    "A guidance reference is "
                    "missing fields: "
                    f"{formatted_fields}."
                )

        # ---------------------------------------------
        # Reviewer actions
        # ---------------------------------------------

        reviewer_actions = (
            payload.get(
                "reviewer_actions",
                [],
            )
        )

        for index, action in enumerate(
            reviewer_actions
        ):
            if not isinstance(
                action,
                dict,
            ):
                raise CripApiDataError(
                    "Reviewer action at "
                    f"index {index} must be "
                    "a JSON object."
                )

            if "action" not in action:
                raise CripApiDataError(
                    "Reviewer action at "
                    f"index {index} is missing "
                    "the 'action' field."
                )

        # ---------------------------------------------
        # Source evidence
        # ---------------------------------------------

        source_evidence = payload.get(
            "source_evidence",
            [],
        )

        for index, evidence in enumerate(
            source_evidence
        ):
            if not isinstance(
                evidence,
                dict,
            ):
                raise CripApiDataError(
                    "Source evidence at "
                    f"index {index} must be "
                    "a JSON object."
                )

            required_source_fields = {
                "evidence_id",
                "source_type",
                "source_reference",
                "content",
            }

            missing_source_fields = (
                required_source_fields.difference(
                    evidence.keys()
                )
            )

            if missing_source_fields:
                formatted_fields = (
                    ", ".join(
                        sorted(
                            missing_source_fields
                        )
                    )
                )

                raise CripApiDataError(
                    "A source evidence item is "
                    "missing fields: "
                    f"{formatted_fields}."
                )

        # ---------------------------------------------
        # Deterministic validation result
        # ---------------------------------------------

        validation = payload.get(
            "validation"
        )

        if not isinstance(
            validation,
            dict,
        ):
            raise CripApiDataError(
                "The claim review 'validation' "
                "field must be a JSON object."
            )

        self._require_fields(
            payload=validation,
            required_fields={
                "source_integrity",
                "warnings",
            },
            response_name=(
                "claim review validation"
            ),
        )

        source_integrity = (
            validation.get(
                "source_integrity"
            )
        )

        if not isinstance(
            source_integrity,
            str,
        ):
            raise CripApiDataError(
                "The claim review validation "
                "'source_integrity' field must "
                "be a string."
            )

        warnings = validation.get(
            "warnings"
        )

        if not isinstance(
            warnings,
            list,
        ):
            raise CripApiDataError(
                "The claim review validation "
                "'warnings' field must be a list."
            )

        for index, warning in enumerate(
            warnings
        ):
            if not isinstance(
                warning,
                str,
            ):
                raise CripApiDataError(
                    "Validation warning at "
                    f"index {index} must be "
                    "a string."
                )

