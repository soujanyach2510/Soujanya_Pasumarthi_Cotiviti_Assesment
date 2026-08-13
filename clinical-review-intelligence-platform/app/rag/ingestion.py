from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import chromadb

from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore


# =====================================================
# Project Paths
# =====================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

KNOWLEDGE_BASE_DIR = (
    PROJECT_ROOT / "knowledge_base"
)

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

CHUNK_SIZE = 700
CHUNK_OVERLAP = 100


# =====================================================
# Embedding Configuration
# =====================================================

def create_embedding_model() -> OllamaEmbedding:
    """
    Create the local Ollama embedding model.

    This does not use OpenAI or any paid API.
    """

    return OllamaEmbedding(
        model_name=EMBEDDING_MODEL,
        base_url=OLLAMA_BASE_URL,
    )


def configure_llama_index() -> None:
    """
    Configure LlamaIndex to use the local Ollama
    embedding model.
    """

    Settings.embed_model = (
        create_embedding_model()
    )

    Settings.text_splitter = (
        SentenceSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
    )


# =====================================================
# Knowledge Base Validation
# =====================================================

def validate_knowledge_base() -> None:
    """
    Confirm that the knowledge-base directory exists
    and contains at least one supported document.
    """

    if not KNOWLEDGE_BASE_DIR.exists():
        raise FileNotFoundError(
            "Knowledge base directory was not found: "
            f"{KNOWLEDGE_BASE_DIR}"
        )

    supported_extensions = {
        ".txt",
        ".md",
        ".pdf",
        ".docx",
    }

    documents_found = [
        path
        for path in KNOWLEDGE_BASE_DIR.rglob("*")
        if (
            path.is_file()
            and path.suffix.lower()
            in supported_extensions
        )
    ]

    if not documents_found:
        raise ValueError(
            "No knowledge-base documents were found. "
            "Add at least one .txt, .md, .pdf, or "
            ".docx file under knowledge_base/."
        )


# =====================================================
# Document Metadata
# =====================================================

def extract_document_metadata(
    file_path: str,
) -> dict[str, Any]:
    """
    Add simple metadata based on where the document
    lives in the knowledge base.

    Example:

    knowledge_base/
        clinical_guidelines/
        payer_policies/
        coding_rules/
    """

    path = Path(file_path)

    try:
        relative_path = path.relative_to(
            KNOWLEDGE_BASE_DIR
        )

    except ValueError:
        relative_path = path

    category = (
        relative_path.parts[0]
        if len(relative_path.parts) > 1
        else "general"
    )

    return {
        "source_file": path.name,
        "knowledge_category": category,
        "relative_path": str(relative_path),
    }


# =====================================================
# Document Loading
# =====================================================

def load_knowledge_documents():
    """
    Load all supported documents from the CRIP
    knowledge base.

    LlamaIndex handles document parsing.
    """

    validate_knowledge_base()

    reader = SimpleDirectoryReader(
        input_dir=str(
            KNOWLEDGE_BASE_DIR
        ),
        recursive=True,
        required_exts=[
            ".txt",
            ".md",
            ".pdf",
            ".docx",
        ],
        file_metadata=(
            extract_document_metadata
        ),
    )

    documents = reader.load_data()

    if not documents:
        raise ValueError(
            "LlamaIndex did not load any "
            "knowledge-base documents."
        )

    return documents


# =====================================================
# ChromaDB
# =====================================================

def create_chroma_collection():
    """
    Create or retrieve the persistent local
    ChromaDB collection.
    """

    CHROMA_DB_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    client = chromadb.PersistentClient(
        path=str(
            CHROMA_DB_DIR
        )
    )

    collection = (
        client.get_or_create_collection(
            name=COLLECTION_NAME,
        )
    )

    return collection


# =====================================================
# Index Creation
# =====================================================

def build_knowledge_index() -> VectorStoreIndex:
    """
    Build the CRIP local RAG index.

    Flow:

        knowledge_base/
            ↓
        LlamaIndex document loading
            ↓
        SentenceSplitter
            ↓
        Ollama embeddings
            ↓
        ChromaDB
    """

    configure_llama_index()

    documents = (
        load_knowledge_documents()
    )

    collection = (
        create_chroma_collection()
    )

    vector_store = ChromaVectorStore(
        chroma_collection=collection
    )

    storage_context = (
        StorageContext.from_defaults(
            vector_store=vector_store
        )
    )

    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        show_progress=True,
    )

    return index


# =====================================================
# CLI Entry Point
# =====================================================

def main() -> None:
    """
    Build the local knowledge index manually.

    Run from the project root:

    python -m app.rag.ingestion
    """

    print(
        "Starting CRIP knowledge-base ingestion..."
    )

    print(
        f"Knowledge base: "
        f"{KNOWLEDGE_BASE_DIR}"
    )

    print(
        f"ChromaDB path: "
        f"{CHROMA_DB_DIR}"
    )

    print(
        f"Embedding model: "
        f"{EMBEDDING_MODEL}"
    )

    index = build_knowledge_index()

    print(
        "CRIP knowledge-base index "
        "created successfully."
    )

    print(
        f"Index type: "
        f"{type(index).__name__}"
    )


if __name__ == "__main__":
    main()