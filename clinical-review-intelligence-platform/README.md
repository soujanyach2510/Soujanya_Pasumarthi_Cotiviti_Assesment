# CRIP – Claim Review Intelligence Platform

## Overview

**CRIP (Claim Review Intelligence Platform)** is an AI-assisted healthcare claim-review proof of concept designed to demonstrate how agentic AI, retrieval-augmented generation (RAG), deterministic validation, and human-in-the-loop review can support payment-integrity workflows.

The platform helps a human claim reviewer evaluate whether a billed healthcare service is supported by the submitted encounter documentation and relevant guidance.

CRIP is designed as a **review-assistance system**, not an autonomous adjudication system. The AI identifies review-relevant findings, retrieves supporting guidance, checks evidence, and produces an advisory summary, while the **human reviewer retains final decision authority**.

---

## Business Problem

Healthcare claim review often requires reviewers to examine multiple sources, including:

* Claim details
* Encounter documentation
* Clinical notes
* Laboratory results
* Payer policies
* Coding guidance
* Clinical guidance

This process can be time-consuming and difficult to trace consistently.

CRIP demonstrates how agentic AI can coordinate these review activities and provide an evidence-centered workflow that helps reviewers:

* Understand the billed service
* Identify supporting or missing documentation
* Retrieve relevant guidance
* Trace findings back to source evidence
* Review deterministic validation warnings
* Make the final human determination

---

## Key Capabilities

### AI-Assisted Claim Review

CRIP analyzes the selected claim case and generates review findings related to the billed service and submitted encounter documentation.

### Multi-Agent Workflow

The proof of concept uses three specialized agents:

#### 1. Claim Pattern Analysis Agent

Identifies important relationships between the billed claim service and the documented encounter.

#### 2. Evidence Verification Agent

Verifies supporting evidence, identifies documentation gaps, and reviews alignment with retrieved guidance.

#### 3. Claim Review Synthesis Agent

Combines verified findings into a concise advisory review and recommends next steps for the human reviewer.

---

## Retrieval-Augmented Generation

CRIP uses a local RAG knowledge base containing three categories of reference material:


knowledge_base/
├── clinical_guidelines/
├── payer_policies/
└── coding_rules/


The system performs category-aware retrieval so the AI workflow receives relevant:

* Clinical guidance
* Payer policy
* Coding guidance

This reduces reliance on the language model's internal knowledge and provides contextual information for the review.

---

## Deterministic Validation

Generative AI output can occasionally introduce incorrect or unsupported statements.

CRIP therefore includes a deterministic Python validation layer that checks objective elements of the generated review against the original claim-case data.

Examples include:

* Unsupported dates
* Incorrect service-date mismatch claims
* Findings that describe missing documentation when no documentation gap was returned
* Certain inconsistencies between source facts and generated findings

The validation layer does **not** make claim decisions or rewrite the AI findings.

Its purpose is to surface objective warnings for the human reviewer.

---

## Human-in-the-Loop Review

Human oversight is a core design principle of CRIP.

The AI does not independently:

* Approve or deny claims
* Determine medical necessity
* Make final coding decisions
* Determine coverage
* Authorize payment
* Provide diagnosis or treatment recommendations

The reviewer evaluates the AI-generated findings, evidence, source documents, guidance, and validation warnings before recording the final determination.

### Core Principle

> **Agents reason. Python validates objective facts. Humans decide.**

---

## Source Evidence and Document Verification

CRIP preserves traceability to the original claim-case information.

The **Evidence & Sources** workspace allows reviewers to:

* Review AI-generated evidence references
* Inspect deterministic source evidence
* View retrieved clinical, payer, and coding guidance
* Open the original submitted source documents

Original source documents are served through the FastAPI backend and open separately for reviewer verification.

This allows the reviewer to validate AI findings without relying only on generated content.

---

## Proof-of-Concept Test Cases

CRIP currently includes two fictional claim-review scenarios.

### Case 1001 – Supported Observation Documentation

The claim includes an observation service and supporting documentation showing:

* Emergency department evaluation
* ECG testing
* Serial troponin testing
* Observation initiation
* Overnight monitoring
* Discharge assessment

This scenario demonstrates a claim where the submitted documentation contains evidence supporting the billed observation service.

### Case 1002 – Documentation Gap

The claim also bills an observation service, but the available documentation shows:

* Emergency department evaluation
* ECG testing
* Initial troponin testing
* Same-day discharge

The submitted record does not establish an observation start, documented observation status, or continued monitoring during an observation period.

This scenario demonstrates how CRIP can surface documentation concerns for human review.

---

## Technology Stack

### Frontend

* Streamlit

### Backend

* FastAPI
* Python

### Agentic AI

* CrewAI

### Local Large Language Model

* Ollama
* Llama 3.1

### Retrieval-Augmented Generation

* LlamaIndex
* ChromaDB
* Nomic embeddings

### Data

* JSON claim-case records
* TXT source documents
* Local healthcare guidance documents

---

## High-Level Architecture


Claim Case + Submitted Documents
              │
              ▼
     RAG Knowledge Retrieval
              │
              ▼
      Multi-Agent Review
              │
      ┌───────┼────────┐
      ▼       ▼        ▼
   Claim   Evidence   Claim
  Pattern Verification Synthesis
   Agent     Agent     Agent
              │
              ▼
   Deterministic Validation
              │
              ▼
 Evidence-Linked Reviewer UI
              │
              ▼
      Human Final Decision


---

## Project Structure


claim-review-intelligence-platform/
├── app/
│   ├── agents/
│   │   ├── claim_pattern_agent.py
│   │   ├── evidence_verification_agent.py
│   │   ├── claim_synthesis_agent.py
│   │   ├── tasks.py
│   │   └── crew.py
│   │
│   ├── backend/
│   │   ├── main.py
│   │   └── review_service.py
│   │
│   ├── frontend/
│   │   ├── app.py
│   │   └── api_client.py
│   │
│   └── rag/
│       ├── ingestion.py
│       └── retriever.py
│
├── claim_cases/
│   ├── case_1001/
│   │   ├── claim_case.json
│   │   ├── emergency_department_note.txt
│   │   ├── laboratory_results.txt
│   │   └── discharge_summary.txt
│   │
│   └── case_1002/
│       ├── claim_case.json
│       ├── emergency_department_note.txt
│       └── laboratory_results.txt
│
├── knowledge_base/
│   ├── clinical_guidelines/
│   ├── payer_policies/
│   └── coding_rules/
│
├── chroma_db/
├── tests/
├── .env
├── requirements.txt
└── README.md


---

## Setup

### 1. Create and Activate a Python Virtual Environment

From the project root, create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

### 2. Install Dependencies

Install all project dependencies:

```bash
pip install -r requirements.txt
```

### 3. Install and Start Ollama

Make sure Ollama is installed and running.

Pull the Llama 3.1 model:

```bash
ollama pull llama3.1
```

Pull the embedding model:

```bash
ollama pull nomic-embed-text
```

Verify the available Ollama models:

```bash
ollama list
```

You should see both `llama3.1` and `nomic-embed-text`.

### 4. Environment Configuration

Create or update the `.env` file in the project root:


CRIP_LLM_MODEL=ollama/llama3.1
OLLAMA_BASE_URL=http://localhost:11434


---

## Build the Local Knowledge Base

Before running the application, ingest the local knowledge-base documents into ChromaDB so the RAG layer can retrieve relevant guidance during claim review.

### Step 1: Verify the Knowledge-Base Structure

Confirm that the following folders exist:


knowledge_base/
├── clinical_guidelines/
├── payer_policies/
└── coding_rules/


The current POC uses documents similar to:


knowledge_base/
├── clinical_guidelines/
│   └── chest_pain_review_guidance.txt
├── payer_policies/
│   └── observation_services_policy.txt
└── coding_rules/
    └── observation_services_coding_rule.txt


These documents have different purposes:

* `clinical_guidelines/` contains clinical context used during review.
* `payer_policies/` contains payer-specific review expectations.
* `coding_rules/` contains coding and billing guidance.

### Step 2: Verify the Embedding Model

Make sure Ollama is running:

```bash
ollama list
```

If `nomic-embed-text` is not listed, pull it:

```bash
ollama pull nomic-embed-text
```

CRIP uses `nomic-embed-text` to generate embeddings for the local knowledge-base documents.

### Step 3: Run the Ingestion Script

From the project root, run:

```bash
python -m app.rag.ingestion
```

The ingestion workflow:

1. Reads the `.txt` files from the knowledge-base folders.
2. Associates each document with its knowledge category.
3. Generates embeddings using `nomic-embed-text`.
4. Stores the vectors and metadata in ChromaDB.

After successful ingestion, the project should contain or update:

chroma_db/

### Step 4: Verify RAG Retrieval

After ingestion is complete, start the backend and frontend and run a claim review.

CRIP should retrieve guidance from all three categories:

* Clinical Guidance
* Payer Policy
* Coding Guidance

The retrieved sources can be viewed in the application under:

AI Review
→ Evidence & Sources
→ Guidance Used

### Rebuilding the Knowledge Base

You do **not** need to rebuild ChromaDB every time the application starts.

Rebuild the vector database when:

* A knowledge-base document is added
* A knowledge-base document is removed
* Document content is significantly changed
* Document metadata or category information is changed

Stop the running application before rebuilding.

Remove the current ChromaDB directory:

```bash
rm -rf chroma_db
```

Then run ingestion again:

```bash
python -m app.rag.ingestion
```

This creates a new vector index using the latest knowledge-base documents.

### Important: Knowledge Base vs. Claim Documents

The `knowledge_base/` and `claim_cases/` folders serve different purposes.

knowledge_base/

contains reusable guidance that may be used across multiple claims.

Examples:

* Clinical guidance
* Payer policies
* Coding rules

claim_cases/

contains evidence belonging to an individual claim.

Examples:

* Claim JSON
* Emergency department note
* Laboratory results
* Discharge summary

Do **not** move claim-specific documents into the `knowledge_base/` folder.

---

## Running the Application

Run the backend and frontend in separate terminal windows.

### Terminal 1 – Start the FastAPI Backend

From the project root:

```bash
python -m uvicorn app.backend.main:app --reload --port 8000
```

The backend will be available at:

http://127.0.0.1:8000

FastAPI Swagger documentation is available at:

http://127.0.0.1:8000/docs

You can use the Swagger page to inspect and test the backend endpoints.

### Terminal 2 – Start the Streamlit Frontend

Open another terminal.

Activate the same virtual environment:

```bash
source .venv/bin/activate
```

Run Streamlit:

```bash
streamlit run app/frontend/app.py
```

Streamlit will display a local URL, typically:

http://localhost:8501

Open that URL in a browser.

---

## Demonstration Workflow

For a complete CRIP demonstration:

1. Start Ollama.
2. Start the FastAPI backend.
3. Start the Streamlit frontend.
4. Select **Case 1001** or **Case 1002** from the sidebar.
5. Review the Claim Overview and encounter information.
6. Click **Start Claim Review**.
7. Wait for the multi-agent workflow to complete.
8. Review the **Advisory Review Summary**.
9. Inspect the generated **Claim Findings**.
10. Review any identified **Documentation Gaps**.
11. Open the **Evidence & Sources** section.
12. Review the retrieved clinical, payer, and coding guidance.
13. Review deterministic validation warnings, if any.
14. Click **Open Document** to inspect the submitted source documents.
15. Compare AI findings with the original source records.
16. Navigate to **Human Decision**.
17. Record the final reviewer determination and rationale.

---

## How the Review Workflow Works

At a high level, the application follows this flow:

1. Claim case selected
        │
        ▼
2. Claim JSON loaded
        │
        ▼
3. RAG retrieves relevant guidance
        │
        ▼
4. CrewAI multi-agent workflow starts
        │
        ├── Claim Pattern Analysis Agent
        ├── Evidence Verification Agent
        └── Claim Review Synthesis Agent
        │
        ▼
5. Structured AI review generated
        │
        ▼
6. Python deterministic validation runs
        │
        ▼
7. Findings, evidence, guidance, and warnings
   are displayed in Streamlit
        │
        ▼
8. Reviewer opens original documents
        │
        ▼
9. Human reviewer records final decision

---

## Submitted Source Documents

Claim-specific source documents are stored inside each case directory.

### Case 1001

claim_cases/case_1001/
├── claim_case.json
├── emergency_department_note.txt
├── laboratory_results.txt
└── discharge_summary.txt

### Case 1002

claim_cases/case_1002/
├── claim_case.json
├── emergency_department_note.txt
└── laboratory_results.txt

The filenames must match the values specified in the case's `submitted_documents` section inside `claim_case.json`.

The Streamlit frontend displays an **Open Document** link for each submitted source document.

The document is securely served through the FastAPI backend rather than being embedded directly inside the Streamlit page.

---

## API Endpoints

The FastAPI backend provides the main application endpoints.

### Health Check

GET /health

### List Available Claim Cases

GET /api/v1/cases

### Retrieve a Claim Case

GET /api/v1/cases/{case_id}

Example:

GET /api/v1/cases/1001

### Run the Multi-Agent Claim Review

POST /api/v1/cases/{case_id}/review

Example:

POST /api/v1/cases/1001/review

### Open a Submitted Source Document

GET /api/v1/cases/{case_id}/documents/{file_name}

Example:

GET /api/v1/cases/1002/documents/laboratory_results.txt

The backend verifies that the requested file belongs to the selected case before serving it.

---

## Human Review and Safety Design

CRIP deliberately separates AI assistance from final decision-making.

### Agent Responsibilities

The agents can:

* Analyze documented claim information
* Identify review-relevant patterns
* Retrieve supporting guidance
* Identify supporting evidence
* Identify possible documentation gaps
* Prepare an advisory summary
* Suggest human review actions

### Deterministic Python Responsibilities

Python performs objective validation such as:

* Checking generated dates against the source case
* Detecting unsupported service-date mismatch statements
* Flagging certain inconsistencies between findings and documentation gaps
* Preserving evidence traceability

Python does **not** generate the claim findings or make a claim decision.

### Human Reviewer Responsibilities

The human reviewer:

* Reviews the generated findings
* Reviews documentation gaps
* Reviews retrieved guidance
* Checks validation warnings
* Opens and verifies source documents
* Records the final determination

---

## POC Scope

CRIP is intentionally designed as a focused hackathon proof of concept.

The current version does not include:

* Production authentication
* Enterprise authorization
* Persistent user database
* Autonomous claims adjudication
* Payment processing
* Production audit infrastructure
* EHR integrations
* Payer core-system integrations
* Enterprise-scale monitoring
* Production-grade security controls
* Docker deployment
* Kubernetes deployment

These capabilities could be considered in a future production implementation but are intentionally outside the scope of this demonstrator.

---

## Future Opportunities

Potential future enhancements include:

* Additional claim categories
* Larger claim-review evaluation datasets
* Advanced evidence-to-document mapping
* Claim-level evidence highlighting
* Reviewer feedback loops
* Controlled model retry after validation failures
* Enterprise payer-policy repositories
* Role-based access control
* Persistent audit history
* Production observability and monitoring
* Integration with payer claim-processing systems
* Risk-based claim prioritization
* Machine-learning claim risk scoring
* Additional deterministic validation rules
* More extensive model evaluation
* Review quality dashboards

---

## Strategic Value

CRIP demonstrates how agentic AI can augment healthcare payment-integrity workflows by coordinating:

* Claim analysis
* Evidence retrieval
* Guidance retrieval
* Pattern recognition
* Documentation-gap identification
* Deterministic validation
* Source traceability
* Human review

The value of the platform is not simply the use of a generative AI model.

The value comes from combining:

> **Agentic reasoning + grounded retrieval + deterministic validation + source traceability + human decision-making**

This creates a more explainable, evidence-centered, and reviewer-focused approach to AI-assisted healthcare claim review.

---

## Disclaimer

CRIP is a fictional educational proof of concept developed for the Cotiviti Intern Assessment.

The claim cases, patient information, payer information, provider information, service codes, policies, clinical guidance, coding guidance, and submitted documents used in the application are fictional and are intended solely for demonstration purposes.

CRIP does not provide medical advice and is not intended for production:

* Claim adjudication
* Coverage determination
* Coding determination
* Medical-necessity determination
* Payment authorization
* Clinical diagnosis
* Treatment recommendations

All AI-generated findings are advisory and require human validation.
