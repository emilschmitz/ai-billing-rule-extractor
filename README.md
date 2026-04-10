# RCM Encounter Validation System

An end-to-end Revenue Cycle Management (RCM) Encounter Validation System that autonomously sources medical billing rules from CMS NCCI manuals, extracts them into a config-driven AST, generates synthetic tests, evaluates claims via a FastAPI backend, and visualizes the audit trail via Streamlit.

## Tech Stack
- **Execution:** `uv`
- **Backend:** FastAPI, PostgreSQL
- **Frontend:** Streamlit
- **AI/LLM:** OpenAI (Strict Structured Outputs)

## Prerequisites
- [Docker & Docker Compose](https://docs.docker.com/compose/install/)
- [`uv`](https://docs.astral.sh/uv/) installed
- Valid `OPENAI_API_KEY` Environment Variable

## Usage Instructions

### 1. Start the Environment (Phase 2 - Backend & DB)
Run the PostgreSQL database and FastAPI backend via Docker Compose:
```bash
# Make sure to set your OpenAI key in your terminal first
export OPENAI_API_KEY="sk-..."

# Start the infrastructure
docker-compose up -d --build
```
The FastAPI Rules Engine is fully operational on `http://localhost:8000`.

### 2. Run the Extractor Pipeline (Phase 1 - Data Gen)
This script parses the live CMS NCCI PDF, chunks it, hits the LLM using strict outputs, populates the rule logic into PostgreSQL, and generates synthetic Candid-styled claim JSONs.
```bash
uv run pipeline.py
```

### 3. Run the Integration Tests (Phase 4 - Testing)
Run the script to post all generated synthetic claims against the FastAPI rules engine and validate that expected Denials and Approvals are handled mathematically:
```bash
uv run test_engine.py
```

### 4. Open the Audit Dashboard (Phase 3 - Frontend)
View the extracted logic alongside the highlighted parsed original CMS documentation.
```bash
uv run streamlit run frontend.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.
