import pypdf

def deeply_search_rules(filename):
    print(f"Reading {filename}")
    try:
        reader = pypdf.PdfReader(filename)
        for i, page in enumerate(reader.pages):
            text = page.extract_text().lower()
            if "modifier" in text and "not be reported" in text:
                print(f"Page {i+1} has rule about modifier not being reported: {text[:50]}")
            if "mutually exclusive" in text and "code" in text:
                print(f"Page {i+1} has MUTUALLY EXCLUSIVE codes rule: {text[:50]}")
            if "if procedure code" in text or ("requires" in text and "place of service" in text):
                print(f"Page {i+1} has PLACE OF SERVICE rule: {text[:50]}")
            if "rule" in text or "ncci" in text:
                pass # Too verbose
    except Exception as e:
        print(f"Error: {e}")

deeply_search_rules("data/2026_ncci_medicare_policy_manual_all-chapters.pdf")
