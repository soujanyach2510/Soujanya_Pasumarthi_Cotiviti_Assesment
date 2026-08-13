from __future__ import annotations

import os

from crewai import Agent, LLM
from dotenv import load_dotenv


load_dotenv()


def create_evidence_verification_agent() -> Agent:
    """
    Create the local documentation, policy, and evidence
    verification agent.

    The agent uses Ollama locally and does not call a paid
    cloud model.
    """

    model_name = os.getenv(
        "CRIP_LLM_MODEL",
        "ollama/llama3.1",
    )

    ollama_base_url = os.getenv(
        "OLLAMA_BASE_URL",
        "http://localhost:11434",
    )

    llm = LLM(
        model=model_name,
        base_url=ollama_base_url,
        temperature=0.1,
    )

    return Agent(
        role="Claim Evidence Verification Specialist",
        goal=(
            "Verify claim-review findings against the submitted "
            "claim case and supporting encounter documentation. "
            "Use retrieved clinical guidance, payer policy, and "
            "coding rules only as contextual reference material, "
            "and identify documentation gaps only when they "
            "directly affect verification of an existing "
            "claim-review finding."
        ),
        backstory=(
            "You support healthcare claim reviewers by checking "
            "whether claim-review observations are supported by "
            "the submitted claim information and source "
            "documentation. You distinguish claim evidence from "
            "retrieved guidance and clearly identify supported, "
            "partially supported, not documented, or conflicting "
            "information. You do not invent evidence, diagnose "
            "patients, recommend treatment, determine medical "
            "necessity, approve or deny coverage, make payment "
            "decisions, or make final coding determinations. "
            "All findings require human validation."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )