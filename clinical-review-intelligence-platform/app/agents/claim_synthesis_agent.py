from __future__ import annotations

import os

from crewai import Agent, LLM
from dotenv import load_dotenv


load_dotenv()


def create_claim_synthesis_agent() -> Agent:
    """
    Create the human-safe claim review synthesis agent.

    This agent combines claim-review patterns, evidence
    verification, and retrieved guidance into a structured
    advisory summary for a qualified human claim reviewer.
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
        role="Claim Review Synthesis Specialist",
        goal=(
            "Combine verified claim-review patterns, supporting "
            "claim and encounter evidence, documentation gaps, "
            "and relevant clinical, payer, and coding guidance "
            "into a clear and traceable advisory review for a "
            "qualified human claim reviewer."
        ),
        backstory=(
            "You support healthcare claim reviewers by converting "
            "multi-agent analysis into a concise, structured, and "
            "auditable claim-review summary. You clearly separate "
            "submitted claim facts, supporting clinical evidence, "
            "retrieved guidance, documentation gaps, and human "
            "reviewer actions. You do not independently approve "
            "or deny claims, determine medical necessity, make "
            "payment decisions, make final coding determinations, "
            "diagnose patients, or recommend treatment. The final "
            "claim determination always remains with a qualified "
            "human reviewer."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )