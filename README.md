# AI Billing Rule Extraction Pipeline 🩺

Extracts medical billing rules in formal, machine-usable form from PDFs, such as the NCCI policy.

Proof of Concept, code is messy.

## Demo

https://github.com/user-attachments/assets/acb183ed-5907-4d53-bbaf-df24d6304520

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

Currently, the system sometimes extracts text descriptions (e.g., "endoscopy") instead of standardized billing codes. To be production-ready, it needs integration with external classification databases e.g. to map procedures to CPT codes and diagnoses to ICD codes.

That would be well-suited for an agentic setup with MCP, allowing an extraction agent to decide when to look things up.

## Rules Engine

A rules engine exists as well in this repository, but it's WIP.
