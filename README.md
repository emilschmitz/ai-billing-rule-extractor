# AI Billing Rule Extraction Pipeline 🏥

Extract medical billing rules in formal, machine-usable form from natural-language PDFs, such as the NCCI policy.

Proof of Concept, code is messy 🔥

## Demo

https://github.com/user-attachments/assets/acb183ed-5907-4d53-bbaf-df24d6304520

## Run

You'll need an OpenAI API key: Copy `.env.sample` to a new file called `.env` and fill it in.

Then, you can start the application (database and rules extractor UI) with Docker Compose:

```bash
docker compose up
```

The rules extractor will be available at `http://localhost:8501`. You can either upload PDFs in the UI, or use the preconfigured NCCI ones. Then click "Run Extraction Analysis" to trigger the pipeline.

## Pipeline Steps

1. Extraction: Parse the PDF into raw text (no AI/OCR needed for NCCI, but could be nice addition for more complex documents).
2. Use LLM with constrained generation to generate a flattened JSON AST. (Flattened representation avoids generation errors common with complex/recursive schemas).
3. Transform the generated flat-AST into a more standard (recursive) format and display it to the user.

The rules are displayed next to the PDF and extracted text in the rules extractor UI for easy human review.

## Improvements

Currently, the system sometimes extracts text descriptions (e.g., "endoscopy") instead of standardized billing codes. To be production-ready, it needs integration with external classification databases e.g. to map procedures to CPT codes and diagnoses to ICD codes.

That task might be well-suited for an agentic setup with a web-search MCP, giving an extraction agent the discretion to look up codes when needed and edit the rules accordingly.

## Rules Engine

A rules engine exists as well in this repository, but it's WIP.
