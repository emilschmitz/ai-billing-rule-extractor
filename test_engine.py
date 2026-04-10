import os
import sys
import json
import requests
from rich.console import Console
from sqlalchemy import create_engine, text

console = Console()

DB_URL = os.getenv("DATABASE_URL", "postgresql://validator:password@localhost:5432/rules_db")
API_URL = "http://localhost:8000/v1/encounters/validate"

def main():
    console.print("[bold cyan]Starting Integration Tests against Rules Engine...[/bold cyan]")
    
    engine = create_engine(DB_URL)
    
    try:
        with engine.connect() as conn:
            tests = conn.execute(text("SELECT id, target_rule_id, expected_to_pass, encounter_json FROM test_encounters")).mappings().fetchall()
    except Exception as e:
        console.print(f"[bold red]Failed to connect to database: {e}[/bold red]")
        sys.exit(1)
        
    if not tests:
        console.print("[bold yellow]No tests found in the database. Please run `uv run pipeline.py` first.[/bold yellow]")
        sys.exit(0)
        
    console.print(f"Found [bold]{len(tests)}[/bold] tests. Running against FastAPI backend...")
    
    passed_tests = 0
    failed_tests = 0
    
    for t in tests:
        rule_id = str(t['target_rule_id'])
        expected_pass = t['expected_to_pass']
        
        payload = t['encounter_json']
        if isinstance(payload, str):
            payload = json.loads(payload)
            
        try:
            resp = requests.post(API_URL, json=payload, timeout=5)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.ConnectionError:
            console.print(f"[bold red][ERROR][/bold red] Cannot connect to {API_URL}. Is FastAPI running?")
            sys.exit(1)
        except Exception as e:
            console.print(f"[bold red][ERROR][/bold red] Request failed: {e}")
            failed_tests += 1
            continue
            
        denied_by = [r['rule_id'] for r in data.get('denied_by', [])]
        
        if expected_pass:
            if rule_id not in denied_by:
                console.print(f"[bold green][PASS][/bold green] Test {t['id'][:8]}... - Expected PASS - Rule {rule_id[:8]} did not deny.")
                passed_tests += 1
            else:
                console.print(f"[bold red][FAIL][/bold red] Test {t['id'][:8]}... - Expected PASS - MISMATCH: Denied by rule {rule_id[:8]}.")
                failed_tests += 1
        else:
            if rule_id in denied_by:
                console.print(f"[bold green][PASS][/bold green] Test {t['id'][:8]}... - Expected FAIL - SUCCESSFULLY CAUGHT by rule {rule_id[:8]}.")
                passed_tests += 1
            else:
                console.print(f"[bold red][FAIL][/bold red] Test {t['id'][:8]}... - Expected FAIL - MISMATCH: Rule {rule_id[:8]} did NOT deny.")
                failed_tests += 1
                
    console.print("\n[bold cyan]================ Test Summary ================[/bold cyan]")
    console.print(f"Total Tests Run: {len(tests)}")
    console.print(f"Passed: [bold green]{passed_tests}[/bold green]")
    console.print(f"Failed: [bold red]{failed_tests}[/bold red]")
    console.print("[bold cyan]==============================================[/bold cyan]")
    
    if failed_tests > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
