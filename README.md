# AI Billing Rule Extraction Pipeline 🏥

Extract medical billing rules in formal, machine-usable form from PDFs, such as the NCCI policy.

Proof of Concept, code is messy.

## Demo

https://github.com/user-attachments/assets/acb183ed-5907-4d53-bbaf-df24d6304520

## Run

Launch the frontend to upload PDFs:

```bash
uv run streamlit run frontend.py
```

## Pipeline Steps

1. Extraction: Parse the PDF into raw text (no AI/OCR needed for NCCI, but could be nice addition for more complex documents).
2. Use LLM with constrained generation to generate a flattened JSON AST. (Flattened representation avoids generation errors common with complex/recursive schemas).
3. Transform the generated flat-AST into a more standard (recursive) format and display it to the user. 

The rules are displayed next to the PDF and extracted text in the frontend for easy human review.

## Production Improvements

Currently, the system sometimes extracts text descriptions (e.g., "endoscopy") instead of standardized billing codes. To be production-ready, it needs integration with external classification databases e.g. to map procedures to CPT codes and diagnoses to ICD codes.

That would be well-suited for an agentic setup with MCP, allowing an extraction agent to decide when to look things up.

## Rules Engine

A rules engine exists as well in this repository, but it's WIP.
