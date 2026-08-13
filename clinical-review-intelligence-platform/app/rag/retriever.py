from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import chromadb

from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.vector_stores import (
    ExactMatchFilter,
    MetadataFilters,
)
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore


# =====================================================
# Project Paths
# =====================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHROMA_DB_DIR = (
    PROJECT_ROOT / "chroma_db"
)


# =====================================================
# RAG Configuration
# =====================================================

COLLECTION_NAME = "crip_clinical_knowledge"

EMBEDDING_MODEL = os.getenv(
    "CRIP_EMBEDDING_MODEL",
    "nomic-embed-text",
)

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434",
)

DEFAULT_TOP_K = 3

SUPPORTED_KNOWLEDGE_CATEGORIES = {
    "clinical_guidelines",
    "payer_policies",
    "coding_rules",
}


# =====================================================
# Embedding Model
# =====================================================

def create_embedding_model() -> OllamaEmbedding:
    """
    Create the same local embedding model used
    during ingestion.
    """

    return OllamaEmbedding(
        model_name=EMBEDDING_MODEL,
        base_url=OLLAMA_BASE_URL,
    )


# =====================================================
# Vector Index
# =====================================================

def load_knowledge_index() -> VectorStoreIndex:
    """
    Load the existing persistent ChromaDB collection
    as a LlamaIndex VectorStoreIndex.
    """

    if not CHROMA_DB_DIR.exists():
        raise FileNotFoundError(
            "ChromaDB directory was not found. "
            "Run ingestion first:\n\n"
            "python -m app.rag.ingestion"
        )

    Settings.embed_model = (
        create_embedding_model()
    )

    client = chromadb.PersistentClient(
        path=str(
            CHROMA_DB_DIR
        )
    )

    collection = client.get_collection(
        name=COLLECTION_NAME,
    )

    vector_store = ChromaVectorStore(
        chroma_collection=collection,
    )

    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=Settings.embed_model,
    )

    return index


# =====================================================
# Category Validation
# =====================================================

def _validate_knowledge_category(
    knowledge_category: str | None,
) -> str | None:
    """
    Validate an optional knowledge-base category.
    """

    if knowledge_category is None:
        return None

    normalized_category = (
        str(knowledge_category).strip()
    )

    if (
        normalized_category
        not in SUPPORTED_KNOWLEDGE_CATEGORIES
    ):
        supported = ", ".join(
            sorted(
                SUPPORTED_KNOWLEDGE_CATEGORIES
            )
        )

        raise ValueError(
            "Unsupported knowledge category "
            f"'{normalized_category}'. "
            f"Supported categories: {supported}."
        )

    return normalized_category


# =====================================================
# Retrieval
# =====================================================

def retrieve_guidance(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    knowledge_category: str | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve relevant CRIP knowledge-base chunks.

    When knowledge_category is supplied, retrieval is
    restricted to that category before similarity ranking.
    """

    normalized_query = str(query).strip()

    if not normalized_query:
        raise ValueError(
            "Retrieval query cannot be empty."
        )

    if top_k < 1:
        raise ValueError(
            "top_k must be at least 1."
        )

    normalized_category = (
        _validate_knowledge_category(
            knowledge_category
        )
    )

    index = load_knowledge_index()

    retriever_kwargs: dict[str, Any] = {
        "similarity_top_k": top_k,
    }

    if normalized_category is not None:
        retriever_kwargs["filters"] = (
            MetadataFilters(
                filters=[
                    ExactMatchFilter(
                        key="knowledge_category",
                        value=normalized_category,
                    )
                ]
            )
        )

    retriever = index.as_retriever(
        **retriever_kwargs
    )

    nodes = retriever.retrieve(
        normalized_query
    )

    results: list[dict[str, Any]] = []

    for rank, node_with_score in enumerate(
        nodes,
        start=1,
    ):
        node = node_with_score.node

        metadata = (
            dict(node.metadata)
            if isinstance(
                node.metadata,
                dict,
            )
            else {}
        )

        text = (
            node.get_content()
            .strip()
        )

        results.append(
            {
                "rank": rank,
                "score": (
                    float(
                        node_with_score.score
                    )
                    if node_with_score.score
                    is not None
                    else None
                ),
                "text": text,
                "source_file": metadata.get(
                    "source_file",
                    "Unknown",
                ),
                "knowledge_category": (
                    metadata.get(
                        "knowledge_category",
                        "Unknown",
                    )
                ),
                "relative_path": metadata.get(
                    "relative_path",
                    "Unknown",
                ),
            }
        )

    return results


# =====================================================
# Claim-Review Category Retrieval
# =====================================================

def retrieve_claim_review_guidance(
    *,
    clinical_query: str,
    payer_query: str,
    coding_query: str,
    top_k_per_category: int = 1,
) -> list[dict[str, Any]]:
    """
    Retrieve claim-review guidance separately from each
    CRIP knowledge category.

    This prevents one category from consuming all of the
    top similarity results.
    """

    if top_k_per_category < 1:
        raise ValueError(
            "top_k_per_category must be at least 1."
        )

    category_requests = (
        (
            "clinical_guidelines",
            clinical_query,
        ),
        (
            "payer_policies",
            payer_query,
        ),
        (
            "coding_rules",
            coding_query,
        ),
    )

    combined_results: list[
        dict[str, Any]
    ] = []

    for category, query in category_requests:
        category_results = retrieve_guidance(
            query=query,
            top_k=top_k_per_category,
            knowledge_category=category,
        )

        combined_results.extend(
            category_results
        )

    for rank, result in enumerate(
        combined_results,
        start=1,
    ):
        result["rank"] = rank

    return combined_results


# =====================================================
# Display Helper
# =====================================================

def print_retrieval_results(
    results: list[dict[str, Any]],
) -> None:
    """
    Print retrieved chunks for local testing.
    """

    if not results:
        print(
            "No relevant guidance was retrieved."
        )
        return

    for result in results:
        print(
            "\n"
            + "=" * 70
        )

        print(
            f"Rank: {result['rank']}"
        )

        print(
            f"Score: {result['score']}"
        )

        print(
            "Category: "
            f"{result['knowledge_category']}"
        )

        print(
            "Source: "
            f"{result['source_file']}"
        )

        print(
            "Path: "
            f"{result['relative_path']}"
        )

        print(
            "\nRetrieved guidance:\n"
        )

        print(
            result["text"]
        )


# =====================================================
# CLI Test
# =====================================================

def main() -> None:
    """
    Run a category-aware retrieval test.

    Execute from project root:

    python -m app.rag.retriever
    """

    results = retrieve_claim_review_guidance(
        clinical_query=(
            "Chest pain observation ECG serial troponin "
            "clinical documentation review"
        ),
        payer_query=(
            "HealthFirst Demo Plan outpatient observation "
            "services OBS-001 payer documentation requirements"
        ),
        coding_query=(
            "OBS-001 observation services coding review "
            "service date place of service documentation"
        ),
        top_k_per_category=1,
    )

    print(
        "Testing CRIP category-aware "
        "knowledge retrieval..."
    )

    print_retrieval_results(
        results
    )


if __name__ == "__main__":
    main()
