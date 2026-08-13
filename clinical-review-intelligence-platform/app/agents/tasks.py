from __future__ import annotations

from crewai import Task
from pydantic import BaseModel, Field, field_validator

from app.agents.claim_pattern_agent import create_claim_pattern_agent
from app.agents.evidence_verification_agent import create_evidence_verification_agent
from app.agents.claim_synthesis_agent import create_claim_synthesis_agent


# =====================================================
# Structured Review Models
# =====================================================

class ClaimReviewFinding(BaseModel):
    title: str
    description: str
    supporting_facts: list[str] = Field(
        default_factory=list
    )
    source_references: list[str] = Field(
        default_factory=list
    )
    confidence: str = "Medium"
    human_validation_required: bool = True


class DocumentationGap(BaseModel):
    item: str
    reason: str
    affected_finding: str | None = None
    source_locations_checked: list[str] = Field(
        default_factory=list
    )
    human_verification_step: str
    verification_status: str = "NOT_DOCUMENTED"


class EvidenceReference(BaseModel):
    source: str
    documented_fact: str
    finding_supported: str


class GuidanceReference(BaseModel):
    source_file: str
    knowledge_category: str
    score: float | None = None


class ReviewerAction(BaseModel):
    action: str
    related_finding: str | None = None


class StructuredClaimReview(BaseModel):
    documented_facts: list[str] = Field(
        default_factory=list
    )

    # Temporary compatibility field name.
    # The content now represents claim-review patterns.
    clinical_patterns: list[ClaimReviewFinding] = Field(
        default_factory=list
    )

    documentation_gaps: list[DocumentationGap] = Field(
        default_factory=list
    )

    evidence_references: list[EvidenceReference] = Field(
        default_factory=list
    )

    guidance_references: list[GuidanceReference] = Field(
        default_factory=list
    )

    reviewer_actions: list[ReviewerAction] = Field(
        default_factory=list
    )

    advisory_summary: str = Field(
        ...,
        min_length=1,
        description=(
            "Required non-empty advisory summary of the "
            "AI-assisted claim review."
        ),
    )

    human_validation_required: bool = True

    @field_validator(
        "advisory_summary",
        mode="before",
    )
    @classmethod
    def validate_advisory_summary(
        cls,
        value: object,
    ) -> str:
        if value is None:
            raise ValueError(
                "advisory_summary is required "
                "and cannot be empty."
            )

        normalized_value = str(value).strip()

        if not normalized_value:
            raise ValueError(
                "advisory_summary is required "
                "and cannot be empty."
            )

        return normalized_value


# Backward-compatible aliases.
# These keep crew.py and review_service.py working while
# the project is migrated one file at a time.
ClinicalFinding = ClaimReviewFinding
StructuredClinicalReview = StructuredClaimReview


# =====================================================
# Task 1: Claim Pattern Analysis
# =====================================================

def create_claim_pattern_task(
    patient_case_json: str,
    retrieved_guidance: str,
) -> Task:
    """
    Identify claim-review patterns using the submitted claim,
    encounter documentation, and retrieved guidance.
    """

    claim_pattern_agent = create_claim_pattern_agent()

    return Task(
        description=f"""
Review the fictional CLAIM CASE below.

CLAIM CASE:
{patient_case_json}


=====================================================
RETRIEVED KNOWLEDGE-BASE GUIDANCE
=====================================================

{retrieved_guidance}


=====================================================
YOUR RESPONSIBILITY
=====================================================

Act as the first-stage CLAIM REVIEW pattern analyst.

Identify patterns relevant to reviewing the submitted claim,
including where supported by the source record:

- billed service and service category
- claim type and place of service
- diagnosis-to-service relationship
- encounter timeline
- observation or other billed-service events
- diagnostic testing associated with the billed service
- documented clinical circumstances supporting the service
- consistency between the claim and encounter documentation
- documentation that may be relevant to payer or coding review

Do NOT perform a general clinical assessment of the patient.

Your purpose is to determine what aspects of the submitted
claim require review and what source evidence supports those
observations.


=====================================================
SOURCE-OF-TRUTH RULE
=====================================================

The CLAIM CASE is the source of truth for:

- submitted claim data
- patient-specific facts
- encounter facts
- submitted-document metadata

Retrieved knowledge-base guidance is reference material only.

It may include:

- clinical guidance
- payer policy
- coding rules

Do not treat retrieved guidance as proof that something happened
in this claim or encounter.

Every claim-specific or patient-specific statement must be
supported by the CLAIM CASE.


=====================================================
CLAIM VS GUIDANCE
=====================================================

Keep these two concepts separate:

CLAIM EVIDENCE
Information actually present in the submitted claim case.

GUIDANCE
External reference material retrieved from the knowledge base.

Guidance may help identify what should be reviewed, but it must
not create a claim fact, patient fact, billed service, diagnosis,
test, documentation gap, or policy conclusion that is absent
from the source record.


=====================================================
PATTERN RULE
=====================================================

Identify only meaningful CLAIM-REVIEW patterns.

Examples:

- the claim bills observation services and the encounter
  documents an observation event
- the claim identifies a hospital-outpatient service and the
  encounter documentation describes the corresponding setting
- the billed service can be traced to documented events
- relevant diagnostic events appear in the encounter timeline
- the submitted claim information and supporting record contain
  information that should be compared with payer or coding
  guidance

Do not simply restate every clinical fact.

Do not make a final determination that a service is:

- medically necessary
- not medically necessary
- covered
- not covered
- correctly coded
- incorrectly coded
- payable
- not payable


=====================================================
GROUNDING AND SAFETY
=====================================================

Do not invent:

- claim fields
- codes
- billed services
- diagnoses
- symptoms
- medications
- tests
- test results
- dates
- policy requirements
- coding requirements
- coverage requirements

Do not diagnose the patient.
Do not recommend treatment or additional testing.
Do not make a final coverage, payment, coding,
utilization-management, or medical-necessity decision.

All findings are advisory and require human validation.


=====================================================
OUTPUT FORMAT
=====================================================

CLAIM_REVIEW_PATTERNS

For each pattern provide:

- Pattern title
- Description
- Supporting documented facts
- Exact claim-case source location or event
- Confidence: High, Medium, or Low
- Human validation required: Yes


DOCUMENTED_FACTS

List the most important claim and encounter facts that are
explicitly documented in the CLAIM CASE.


UNCERTAINTIES

Include only uncertainties that directly affect one of the
identified claim-review patterns.

If none exist:

None identified.
""",
        expected_output="""
A grounded claim-review pattern analysis containing:

1. CLAIM_REVIEW_PATTERNS
2. DOCUMENTED_FACTS
3. UNCERTAINTIES

Use the claim case as the source of truth.

Use retrieved knowledge only as contextual guidance.

Do not make a final coverage, coding, payment,
medical-necessity, utilization-management, diagnosis,
or treatment decision.

Human validation is required.
""",
        agent=claim_pattern_agent,
    )


# =====================================================
# Task 2: Documentation, Policy & Evidence Verification
# =====================================================

def create_documentation_review_task(
    patient_case_json: str,
    retrieved_guidance: str,
    clinical_pattern_task: Task,
) -> Task:
    """
    Verify Agent 1 claim-review patterns against the source
    record and relevant retrieved guidance.
    """

    evidence_verification_agent = create_evidence_verification_agent()

    return Task(
        description=f"""
Verify the claim-review patterns produced by Agent 1.

CLAIM CASE:
{patient_case_json}


=====================================================
RETRIEVED KNOWLEDGE-BASE GUIDANCE
=====================================================

{retrieved_guidance}


=====================================================
YOUR RESPONSIBILITY
=====================================================

Act as the documentation, policy, and evidence-verification
analyst.

For every Agent 1 pattern:

1. Verify the claim-specific statement against the CLAIM CASE.
2. Identify the exact source evidence supporting it.
3. Use retrieved guidance only to contextualize the review.
4. Identify a documentation gap only when it directly affects
   verification of an existing claim-review pattern.

Do not create new claim findings merely because a retrieved
policy, coding rule, or clinical guideline mentions a topic.


=====================================================
SOURCE PRIORITY
=====================================================

Use this hierarchy:

1. Submitted claim data and encounter documentation
2. Agent 1 claim-review analysis
3. Retrieved knowledge-base guidance

The original CLAIM CASE always controls claim-specific and
patient-specific facts.


=====================================================
GUIDANCE CATEGORIES
=====================================================

Retrieved guidance may come from:

- clinical_guidelines
- payer_policies
- coding_rules

Use each category for its intended purpose.

Clinical guidance:
Provides clinical context relevant to the documented encounter.

Payer policy:
Provides payer-review context for the billed service.

Coding rules:
Provide coding or billing context for the submitted service.

Do not convert any retrieved guidance into a final approval,
denial, payment, coding, or medical-necessity decision.


=====================================================
VERIFICATION STATUS
=====================================================

Use only:

SUPPORTED
The source record explicitly supports the finding.

PARTIALLY_SUPPORTED
Part of the finding is supported, but another material part is
not supported.

NOT_DOCUMENTED
The finding was produced by Agent 1, but the source record does
not contain enough evidence to support it.

CONFLICTING_DOCUMENTATION
Different parts of the submitted source record directly
contradict one another.


=====================================================
DOCUMENTATION GAP RULE
=====================================================

A documentation gap may be identified only when all are true:

1. It directly affects an existing Agent 1 claim-review pattern.
2. The missing or unclear information is necessary to verify
   that pattern.
3. The available claim case was checked for the information.
4. The gap can be tied to a specific human verification step.

Do not create a gap solely because retrieved guidance mentions
something that is absent.

If no review-relevant gap exists:

DOCUMENTATION_GAPS:
None identified.


=====================================================
EVIDENCE REQUIREMENT
=====================================================

Evidence must trace back to the CLAIM CASE.

Useful source locations may include:

- claim.claim_id
- claim.payer
- claim.claim_type
- claim.service_category
- claim.service_code
- claim.place_of_service
- claim.service_date
- claim.billed_units
- claim.billed_amount
- encounter.primary_diagnosis
- encounter.clinical_summary
- encounter.timeline
- patient.comorbidities
- submitted_documents

Do not list knowledge-base guidance as claim-specific evidence.


=====================================================
SAFETY RULES
=====================================================

Do not:

- invent claim evidence
- invent patient evidence
- invent documentation gaps
- diagnose the patient
- recommend treatment
- determine medical necessity
- approve or deny coverage
- make a payment decision
- make a final coding determination
- make the final claim-review decision

Human validation is mandatory.


=====================================================
OUTPUT FORMAT
=====================================================

SUPPORTED_FINDINGS

For each verified finding:

- Finding
- Verification status
- Exact claim-case source
- Supporting documented fact
- Human validation required


DOCUMENTATION_GAPS

For each valid gap:

- Missing or unclear item
- Verification status
- Specific finding affected
- Why it matters
- Source locations checked
- Human verification step

If none:

None identified.


EVIDENCE_REFERENCES

Create at least one evidence reference for EVERY finding that
you mark SUPPORTED or PARTIALLY_SUPPORTED.

For each evidence reference provide:

- Source
- Documented fact
- Finding supported

The "Finding supported" value must use the actual Agent 1
finding title. Do not use generic values such as "Yes".

If one source supports more than one finding, create separate
evidence-reference entries so each finding remains traceable.
""",
        expected_output="""
A grounded claim-review evidence-verification report containing:

1. SUPPORTED_FINDINGS
2. DOCUMENTATION_GAPS
3. EVIDENCE_REFERENCES

Every supported or partially supported finding must have at
least one evidence-reference entry mapped to that finding.

Verify only findings produced by Agent 1.

Use the claim case as the source of truth.

Use retrieved clinical, payer, and coding guidance only as
contextual reference material.

Do not make the final claim-review determination.

Human validation is required.
""",
        agent=evidence_verification_agent,
        context=[
            clinical_pattern_task,
        ],
    )


# =====================================================
# Task 3: Human-Safe Claim Review Synthesis
# =====================================================

def create_synthesis_task(
    patient_case_json: str,
    retrieved_guidance: str,
    clinical_pattern_task: Task,
    documentation_review_task: Task,
) -> Task:
    """
    Produce the final structured claim-review advisory from
    verified evidence and retrieved guidance.
    """

    claim_synthesis_agent = create_claim_synthesis_agent()

    return Task(
        description=f"""
Prepare the final human-safe CLAIM REVIEW advisory.

Use:

1. Original claim case
2. Agent 1 claim-review pattern analysis
3. Agent 2 documentation/policy/evidence verification
4. Retrieved knowledge-base guidance

CLAIM CASE:
{patient_case_json}


=====================================================
RETRIEVED KNOWLEDGE-BASE GUIDANCE
=====================================================

{retrieved_guidance}


=====================================================
YOUR RESPONSIBILITY
=====================================================

Synthesize the verified review into a concise structured result
for a HUMAN CLAIM REVIEWER.

Do not perform a new independent clinical analysis.

Do not create new claim findings.

Do not make a final claim determination.


=====================================================
SOURCE PRIORITY
=====================================================

Use this hierarchy:

1. Original claim case
2. Agent 2 verification
3. Agent 1 pattern analysis
4. Retrieved knowledge-base guidance

The original claim case is the source of truth for all submitted
claim and patient-specific facts.


=====================================================
STRUCTURED OUTPUT
=====================================================

Return one StructuredClaimReview object.

The existing field name clinical_patterns is temporarily
retained for application compatibility, but the items placed
there must be CLAIM-REVIEW patterns, not general clinical
patterns.

Populate:

- documented_facts
- clinical_patterns
- documentation_gaps
- evidence_references
- reviewer_actions
- advisory_summary
- human_validation_required

guidance_references are attached deterministically by Python
after CrewAI completes.


=====================================================
DOCUMENTED FACTS
=====================================================

Include important facts directly supported by the claim case,
such as:

- submitted claim/service information
- relevant encounter information
- relevant documented clinical events

Do not place generic policy or coding guidance in
documented_facts.


=====================================================
CLAIM-REVIEW PATTERNS
=====================================================

clinical_patterns may contain only claim-review patterns that:

1. originated in Agent 1
AND
2. were verified or appropriately qualified by Agent 2

Do not create a pattern merely because retrieved guidance
discusses that subject.

Every pattern must include:

- title
- description
- supporting_facts
- source_references
- confidence
- human_validation_required


=====================================================
DOCUMENTATION GAPS
=====================================================

Include only gaps validated by Agent 2.

Do not create new gaps during synthesis.

If Agent 2 reports no valid gaps:

documentation_gaps = []


=====================================================
EVIDENCE REFERENCES
=====================================================

Map each verified claim-review finding back to source data in
the claim case.

Each evidence reference must contain:

- source
- documented_fact
- finding_supported

Do not use retrieved guidance as claim-specific or
patient-specific evidence.

TRACEABILITY REQUIREMENT:

Every final claim-review pattern must have at least one
evidence_references entry whose finding_supported value matches
that pattern title.

Do not return a final pattern without mapped source evidence.


=====================================================
REVIEWER ACTIONS
=====================================================

reviewer_actions are concrete workflow steps for the HUMAN CLAIM
REVIEWER.

Return 1 to 3 useful reviewer actions even when
documentation_gaps is empty.

Actions must be specific to this claim. Avoid vague actions such
as only:

- "Verify"
- "Review"
- "Confirm"

Each action should explain WHAT should be checked and, when
relevant, WHICH evidence or guidance category should be used.

Appropriate actions include:

- compare the billed observation service with the documented
  observation event and service date
- compare relevant claim information with the retrieved payer
  policy
- compare the submitted service code and place of service with
  the retrieved coding guidance
- validate a specific finding against cited claim-case evidence
- resolve a validated documentation gap
- resolve conflicting submitted documentation

If documentation_gaps is empty:

- do not ask for missing documentation
- do not imply documentation is absent
- still provide useful validation steps based on existing
  evidence and retrieved guidance

Do not tell the reviewer to approve, deny, pay, or reject the
claim.


=====================================================
ADVISORY SUMMARY
=====================================================

advisory_summary must be 2 to 4 concise sentences.

It must summarize the ACTUAL review result, not merely state
that human validation is required.

Include:

1. the billed service being reviewed
2. the key encounter evidence that was verified
3. whether documentation gaps were identified
4. the main payer-policy or coding comparison the human reviewer
   should complete next

A valid summary should sound like a concise handoff to a human
claim reviewer.

Do NOT return a summary that only says:

- human validation is required
- the analysis is advisory
- findings require verification

Those statements may appear only after the actual review
findings have been summarized.

The summary must remain advisory.

Do not state:

- approve
- deny
- covered
- not covered
- medically necessary
- not medically necessary
- correctly coded
- incorrectly coded

as a final determination.


=====================================================
FINAL SAFETY RULES
=====================================================

Never:

1. Invent claim or patient information.
2. Invent evidence.
3. Invent documentation gaps.
4. Treat knowledge-base guidance as source evidence.
5. Diagnose the patient.
6. Recommend treatment or additional testing.
7. Make a medical-necessity determination.
8. Make a coverage or payment decision.
9. Make a final coding determination.
10. Make the final claim-review decision.
11. Carry an unsupported Agent 1 finding into the final output.
12. Create a finding solely because retrieved guidance mentions
    that topic.

13. Return a final claim-review pattern without at least one
    mapped evidence reference.

14. Return reviewer actions that consist only of vague words such
    as "Verify", "Review", or "Confirm".

15. Return an advisory summary that contains only a generic
    human-validation or safety statement.

human_validation_required must always be true.
""",
        expected_output="""
Return one valid StructuredClaimReview object containing:

- documented_facts
- clinical_patterns
- documentation_gaps
- evidence_references
- reviewer_actions
- advisory_summary
- human_validation_required

The claim case is the source of truth.

The clinical_patterns field currently stores verified
claim-review patterns for backward compatibility.

Retrieved knowledge-base guidance is contextual reference
material only.

Each final claim-review pattern must have at least one mapped
evidence reference.

Return 1 to 3 concrete reviewer actions.

advisory_summary must be 2 to 4 concise sentences describing the
actual review findings, documentation-gap status, and the main
human-review comparison that remains.

Do not make final medical-necessity, coverage, payment, coding,
utilization-management, diagnosis, or treatment decisions.

human_validation_required must be true.
""",
        agent=claim_synthesis_agent,
        context=[
            clinical_pattern_task,
            documentation_review_task,
        ],
        output_pydantic=StructuredClaimReview,
    )


# =====================================================
# CRIP Task Factory
# =====================================================

def create_review_tasks(
    patient_case_json: str,
    retrieved_guidance: str,
) -> tuple[Task, Task, Task]:
    """
    Create the complete RAG-aware claim-review workflow.

    The patient_case_json parameter name is retained
    temporarily for compatibility with crew.py.
    """

    claim_pattern_task = create_claim_pattern_task(
        patient_case_json=patient_case_json,
        retrieved_guidance=retrieved_guidance,
    )

    documentation_review_task = (
        create_documentation_review_task(
            patient_case_json=patient_case_json,
            retrieved_guidance=retrieved_guidance,
            clinical_pattern_task=claim_pattern_task,
        )
    )

    synthesis_task = create_synthesis_task(
        patient_case_json=patient_case_json,
        retrieved_guidance=retrieved_guidance,
        clinical_pattern_task=claim_pattern_task,
        documentation_review_task=documentation_review_task,
    )

    return (
        claim_pattern_task,
        documentation_review_task,
        synthesis_task,
    )
