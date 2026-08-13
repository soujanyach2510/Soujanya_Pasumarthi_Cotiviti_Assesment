from __future__ import annotations

import os

from crewai import Agent, LLM
from dotenv import load_dotenv


load_dotenv()


def create_claim_pattern_agent() -> Agent:
    """
    Create the local claim-pattern analysis agent.

    The agent uses Ollama on the local computer and does not call
    OpenAI or another paid cloud model.
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
        role="Claim Pattern Analysis Specialist",
        goal=(
            "Analyze the submitted fictional claim case and identify "
            "claim-review patterns involving the billed service, "
            "diagnosis, encounter documentation, service setting, "
            "clinical events, and other evidence relevant to claim "
            "review."
        ),
        backstory=(
            "You support healthcare claim reviewers by examining the "
            "relationship between submitted claim information and the "
            "supporting encounter documentation. You organize relevant "
            "facts into clear, evidence-based claim-review observations "
            "and distinguish source evidence from retrieved clinical, "
            "payer, and coding guidance. You do not independently "
            "approve or deny claims, determine medical necessity, make "
            "payment decisions, make final coding determinations, "
            "diagnose patients, or recommend treatment. All findings "
            "remain advisory and require human validation."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )