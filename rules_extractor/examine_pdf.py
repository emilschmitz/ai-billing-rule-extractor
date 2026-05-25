import pypdf

def deeply_search_rules(filename):
    print(f"Reading {filename}")
    try:
        reader = pypdf.PdfReader(filename)
        for i, page in enumerate(reader.pages):
            text = page.extract_text().lower()
            page_num = i + 1
            
            # Look for dental rules (age limits, prior approval, frequency limits, etc.)
            checks = []
            if "prior approval" in text or "prior authorization" in text:
                checks.append("prior approval")
            if "under" in text and "years of age" in text:
                checks.append("age limit")
            if "frequency" in text or "limit" in text:
                checks.append("frequency limit")
            if "modifier" in text:
                checks.append("modifier")
            if "reimbursement" in text:
                checks.append("reimbursement policy")
                
            if checks:
                print(f"Page {page_num} checks: {', '.join(checks)}")
                # Print a small excerpt
                lines = [line.strip() for line in page.extract_text().split("\n") if any(k in line.lower() for k in ["prior approval", "age", "frequency", "limit", "modifier"])]
                for line in lines[:3]:
                    print(f"  > {line[:100]}")
    except Exception as e:
        print(f"Error: {e}")

deeply_search_rules("data/dental_policy_and_procedure_manual.pdf")

