# AI Claim Validator

Extracts medical billing rules in formal, machine-usable form from PDFs, such as the NCCI policy.

Proof of Concept, code is messy.

## Run

Launch the frontend to upload PDFs:

```bash
uv run streamlit run frontend.py
```

## Pipeline Steps

1. **Extract**: Parse the PDF into raw text.
2. **Structured Generation**: Use LLM with structured outputs to generate a flattened JSON AST. (Flattened representations avoid generation errors common with complex recursive schemas).
3. **Transform**: Process the flat JSON AST into the application's required format.

In the streamlit frontend, a human can easily review the extracted rules.

## Production Improvements

Currently, the system sometimes extracts text descriptions (e.g., "endoscopy") instead of standardized billing codes. To be production-ready, it needs integration with external classification databases to map:

- Procedures to **CPT codes** (Current Procedural Terminology) or HCPCS.
- Diagnoses to **ICD-10 codes**.

This mapping would be well-suited for an agentic setup using MCP (Model Context Protocol), allowing an extraction agent to decide when to look things up.

## Rules Engine

A rules engine exists in this repository, but it is currently an undeveloped stub.
