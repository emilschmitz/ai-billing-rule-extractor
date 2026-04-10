import os
import io
import uuid
import json
import random
import requests
from bs4 import BeautifulSoup
import pypdf
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field
from openai import OpenAI
from sqlalchemy import create_engine, text

# Database setup
DB_URL = "postgresql+psycopg://validator:password@localhost:5432/rules_db"
engine = create_engine(DB_URL, pool_pre_ping=True)

# OpenAI setup
client = OpenAI()

def read_pdf_pages(file_or_bytes, start_page=1, end_page=None) -> List[dict]:
    print("Reading PDF pages...")
    try:
        reader = pypdf.PdfReader(file_or_bytes)
        pages = []
        
        start_idx = max(0, start_page - 1)
        end_idx = min(len(reader.pages), end_page) if end_page else len(reader.pages)
        
        for i in range(start_idx, end_idx):
            t = reader.pages[i].extract_text()
            if t:
                pages.append({"page_num": i + 1, "text": t})
        print(f"Successfully extracted {len(pages)} pages.")
        return pages
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return []

def chunk_pages_text(pages: List[dict], chunk_size=3, overlap=1) -> List[str]:
    print(f"Intelligent Chunking: Chunking into {chunk_size}-page segments with {overlap} page overlap...")
    chunks = []
    if not pages: return chunks
    
    step = max(1, chunk_size - overlap)
    for i in range(0, len(pages), step):
        chunk_pages = pages[i:i+chunk_size]
        text_content = ""
        for p in chunk_pages:
            text_content += f"[PAGE {p['page_num']}]\n{p['text']}\n\n"
        chunks.append(text_content)
        
        if i + chunk_size >= len(pages):
            break
            
    print(f"Created {len(chunks)} chunks.")
    return chunks

class RuleNode(BaseModel):
    id: str = Field(description="uuid string")
    parent_id: Optional[str] = Field(description="uuid string | null")
    type: Literal['AND', 'OR', 'CONDITION']
    field: str = Field(description="Using dot/bracket notation like 'service_lines[].modifiers'. Empty string for logic nodes.")
    operator: Literal['==', '!=', '>', '<', 'in', 'not in', ''] = Field(description="Empty string for logic nodes")
    value: Union[str, List[str]] = Field(description="String or list of strings. Empty string for logic nodes")
    citation: str = Field(description="Verbatim exact match substring from chunk")

class ExtractionResult(BaseModel):
    rules: List[RuleNode]

class SyntheticEncounter(BaseModel):
    patient: dict = Field(default_factory=dict)
    place_of_service_code: str
    diagnoses: List[dict]
    service_lines: List[dict]

class RuleSyntheticTests(BaseModel):
    passes: List[SyntheticEncounter] = Field(description="5 encounters that pass the rule")
    fails: List[SyntheticEncounter] = Field(description="5 encounters that fail the rule")

SYSTEM_PROMPT = """You are an expert RCM Encounter Validation system builder.
You parse convoluted medical rules into a config-driven flat AST array.
The AST uses nodes. `type` is AND, OR, or CONDITION.
For logic nodes (AND/OR), `field`, `operator`, `value` must be empty strings.
For CONDITION nodes, `field` uses JSONPath-like notation targeting the Candid Health Encounter schema, e.g., 'service_lines[].procedure_code' or 'diagnoses[].code'.
`operator` must be in ['==', '!=', '>', '<', 'in', 'not in'].
The `citation` MUST be a verbatim exact-match substring from the ORIGINAL CHUNK provided. This is absolutely critical for UI highlighting. DO NOT modify the text.

Here are few-shot examples for structured extraction.

Example 1: Single condition rule
Chunk text: "...If procedure code 99214 is billed, the claim requires place of service 11..."
AST:
[
  { "id": "uuid-1", "parent_id": null, "type": "CONDITION", "field": "place_of_service_code", "operator": "==", "value": "11", "citation": "procedure code 99214 is billed, the claim requires place of service 11" }
]

Example 2: Complex AND/OR logic
Chunk text: "...To bill for telehealth, the modifier must be 95 or GQ, and the POS cannot be 02..."
AST:
[
  { "id": "uuid-logic", "parent_id": null, "type": "AND", "field": "", "operator": "", "value": "", "citation": "To bill for telehealth, the modifier must be 95 or GQ, and the POS cannot be 02" },
  { "id": "uuid-cond-1", "parent_id": "uuid-logic", "type": "CONDITION", "field": "service_lines[].modifiers", "operator": "in", "value": ["95", "GQ"], "citation": "modifier must be 95 or GQ" },
  { "id": "uuid-cond-2", "parent_id": "uuid-logic", "type": "CONDITION", "field": "place_of_service_code", "operator": "!=", "value": "02", "citation": "POS cannot be 02" }
]

Example 3: Modifier exclusion
Chunk text: "...Modifiers 25 and 59 should not be reported on the same diagnosis line..."
AST:
[
  { "id": "uuid-cond-3", "parent_id": null, "type": "CONDITION", "field": "service_lines[].modifiers", "operator": "not in", "value": ["25", "59"], "citation": "Modifiers 25 and 59 should not be reported" }
]
"""

def extract_rules(chunk: str) -> List[RuleNode]:
    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Extract rules from this chunk. Remember citation MUST be an exact substring:\n\n{chunk}"}
            ],
            response_format=ExtractionResult,
            temperature=0.0
        )
        return response.choices[0].message.parsed.rules
    except Exception as e:
        print(f"Error extracting rules: {e}")
        return []

def generate_synthetic_data(rule_ast: List[RuleNode]) -> Optional[RuleSyntheticTests]:
    schema_prompt = """Generate 10 Synthetic Encounters (5 that pass, 5 that fail) for the given rule AST.
Mimic the Candid Health Encounter schema:
{
  "patient": {},
  "place_of_service_code": "str",
  "diagnoses": [{"code": "str"}],
  "service_lines": [{"procedure_code": "str", "modifiers": ["str"]}]
}"""
    try:
        ast_json = json.dumps([r.model_dump() for r in rule_ast], indent=2)
        response = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": schema_prompt},
                {"role": "user", "content": f"Generate tests for this AST rule:\n{ast_json}"}
            ],
            response_format=RuleSyntheticTests,
            temperature=0.3
        )
        return response.choices[0].message.parsed
    except Exception as e:
        print(f"Error generating tests: {e}")
        return None

def clear_database():
    with engine.begin() as conn:
        print("Clearing existing data...")
        conn.execute(text("TRUNCATE TABLE test_encounters, rule_nodes CASCADE;"))

def run_pipeline_for_pages(pages: List[dict], chunk_size=3, overlap=1, progress_callback=None):
    chunks = chunk_pages_text(pages, chunk_size=chunk_size, overlap=overlap)

    for i, chunk in enumerate(chunks):
        if not chunk.strip(): continue
        
        chunk_msg = f"Processing chunk {i+1}/{len(chunks)}..."
        print(f"\n{chunk_msg}")
        if progress_callback:
            progress_callback(i, len(chunks), chunk_msg)
            
        rules = extract_rules(chunk)
        if not rules:
            print("No rules extracted for this chunk.")
            continue
        
        # Remap IDs to valid UUIDs to avoid PostgreSQL DataError
        id_map = {}
        for node in rules:
            new_id = str(uuid.uuid4())
            id_map[node.id] = new_id
            node.id = new_id
            
        for node in rules:
            if node.parent_id in id_map:
                node.parent_id = id_map[node.parent_id]
        
        print(f"Extracted {len(rules)} nodes. Generating synthetic data...")
        
        # We group roots. Normally a chunk might have multiple disconnected roots.
        # This simple pipeline links synthetic tests to root nodes of the rules extracted.
        roots = [r for r in rules if r.parent_id is None]
        
        tests = generate_synthetic_data(rules)
        
        print("Saving to database...")
        with engine.begin() as conn:
            # Insert nodes
            for node in rules:
                val = json.dumps(node.value) if isinstance(node.value, list) else json.dumps(node.value)
                query = text("""
                    INSERT INTO rule_nodes (id, parent_id, node_type, field_name, operator, node_value, citation)
                    VALUES (:id, :parent_id, :node_type, :field_name, :operator, :node_value, :citation)
                """)
                conn.execute(query, {
                    "id": node.id,
                    "parent_id": node.parent_id,
                    "node_type": node.type,
                    "field_name": node.field,
                    "operator": node.operator,
                    "node_value": val,
                    "citation": node.citation
                })
            
            # Insert tests targeted at the first root of the chunk
            if tests and roots:
                target_rule_id = roots[0].id
                for t in tests.passes:
                    conn.execute(text("""
                        INSERT INTO test_encounters (encounter_json, target_rule_id, expected_to_pass)
                        VALUES (:json, :rule_id, TRUE)
                    """), {"json": json.dumps(t.model_dump()), "rule_id": target_rule_id})
                for t in tests.fails:
                    conn.execute(text("""
                        INSERT INTO test_encounters (encounter_json, target_rule_id, expected_to_pass)
                        VALUES (:json, :rule_id, FALSE)
                    """), {"json": json.dumps(t.model_dump()), "rule_id": target_rule_id})

def main():
    print("Starting Pipeline...")
    clear_database()
    # Use 2026 manual by default
    pages = read_pdf_pages("data/2026_ncci_medicare_policy_manual_all-chapters.pdf", start_page=1, end_page=10)
    run_pipeline_for_pages(pages, chunk_size=3, overlap=1)
    print("\nPipeline Complete!")

if __name__ == "__main__":
    main()
