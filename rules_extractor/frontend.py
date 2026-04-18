import streamlit as st
import json
import html
import os
import re
from sqlalchemy import create_engine, text
import pipeline

st.set_page_config(layout="wide", page_title="RCM Validation Audit")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: #2D2D2D;
}

/* Minimalist warm background common in AI frontends */
.stApp {
    background-color: #FAF9F6;
}

h1, h2, h3, h4, h5, h6, 
div[data-testid="stMarkdownContainer"] h1, 
div[data-testid="stMarkdownContainer"] h2, 
div[data-testid="stMarkdownContainer"] h3 {
    font-family: 'Source Serif 4', serif !important;
    color: #111111;
    font-weight: 600;
}

/* Cleaner, simpler source document container */
.source-doc {
    font-family: 'Inter', sans-serif !important;
    background-color: #FFFFFF !important;
    padding: 24px !important;
    border: 1px solid #EAE8E2 !important;
    border-radius: 12px !important;
    color: #333333 !important;
    line-height: 1.7;
    font-size: 15px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    white-space: pre-wrap;
}

/* Anthropic-like Buttons */
.stButton>button {
    background-color: #ECEae6;
    color: #2D2D2D;
    border: 1px solid #D8D4CF;
    border-radius: 8px;
    font-weight: 500;
    transition: all 0.2s ease;
}
.stButton>button:hover {
    background-color: #E0DDD8;
    border-color: #C0BCB6;
    color: #111;
}

/* Clean Sidebar */
[data-testid="stSidebar"] {
    background-color: #F5F4F0;
    border-right: 1px solid #EAE8E2;
}

/* Hide Streamlit fullscreen button (zoom icon) */
button[title="View fullscreen"] {
    display: none !important;
}

/* Hide Streamlit cute loading messages (swimming, wheelchair, etc) */
[data-testid="stStatusWidget"] {
    visibility: hidden;
    display: none;
}
</style>
""", unsafe_allow_html=True)

st.title("RCM Encounter Validation")

DB_URL = "postgresql+psycopg://validator:password@localhost:5432/rules_db"

@st.cache_resource
def get_db_engine():
    return create_engine(DB_URL)

@st.cache_data
def get_run_names():
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            runs = conn.execute(text("SELECT DISTINCT run_name FROM rule_nodes WHERE run_name IS NOT NULL ORDER BY run_name DESC")).fetchall()
        return [r[0] for r in runs]
    except Exception as e:
        return []

@st.cache_data
def load_db_data(run_name):
    if not run_name or run_name == "New/Empty": return [], []
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            rules_res = conn.execute(text("SELECT * FROM rule_nodes WHERE run_name = :r"), {"r": run_name}).mappings().fetchall()
            tests_res = conn.execute(text("SELECT * FROM test_encounters WHERE run_name = :r"), {"r": run_name}).mappings().fetchall()
        return [dict(r) for r in rules_res], [dict(t) for t in tests_res]
    except Exception as e:
        st.error(f"Failed to connect to database. Make sure docker-compose is running. Error: {e}")
        return [], []

@st.cache_data
def load_source_document(pdf_source, start_page, end_page):
    pages = pipeline.read_pdf_pages(pdf_source, start_page=start_page, end_page=end_page)
    raw_text = ""
    for p in pages:
        raw_text += f"[PAGE {p['page_num']}]\n{p['text']}\n\n"
    return raw_text, pages

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

st.sidebar.header("Document Configuration")

# Handle uploading new PDFs to data folder
uploaded_file = st.sidebar.file_uploader("Upload PDF Manual", type=["pdf"])
if uploaded_file:
    file_path = os.path.join("data", uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getvalue())
    st.sidebar.success(f"Saved {uploaded_file.name} to data/")

# List available PDFs
available_pdfs = [f for f in os.listdir("data") if f.endswith(".pdf")]
default_index = 0
for i, f in enumerate(available_pdfs):
    if "2026_ncci" in f:
        default_index = i

selected_pdf = st.sidebar.selectbox("Select PDF Document", available_pdfs, index=default_index)

if selected_pdf:
    pdf_source = os.path.join("data", selected_pdf)
else:
    pdf_source = None

start_page = st.sidebar.number_input("Start Page", min_value=1, value=20)
end_page = st.sidebar.number_input("End Page", min_value=1, value=30)
chunk_size = st.sidebar.number_input("Analysis Chunk Size (pages)", min_value=1, value=3)
overlap = st.sidebar.number_input("Overlap Pages", min_value=0, value=1)

st.sidebar.markdown("---")
available_runs = get_run_names()
if 'selected_run_name' not in st.session_state:
    st.session_state.selected_run_name = "New/Empty"

options = ["New/Empty"] + available_runs
idx = options.index(st.session_state.selected_run_name) if st.session_state.selected_run_name in options else 0

selected_run = st.sidebar.selectbox("Past Extractions", options, index=idx)
if selected_run != st.session_state.selected_run_name:
    st.session_state.selected_run_name = selected_run
    st.rerun()

if st.sidebar.button("Run Extraction Analysis"):
    if not pdf_source:
        st.sidebar.error("No PDF selected!")
    else:
        st.sidebar.info("Starting pipeline. Please wait...")
        progress_bar = st.sidebar.progress(0)
        status_text = st.sidebar.empty()
        
        # Read the text for analysis
        pages = pipeline.read_pdf_pages(pdf_source, start_page=start_page, end_page=end_page)
        
        from datetime import datetime
        run_name = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (P{start_page}-{end_page})"
        st.session_state.selected_run_name = run_name
        
        def update_progress(current, total, msg):
            # Calculate progress ratio
            ratio = min(1.0, current / max(1, total))
            progress_bar.progress(ratio)
            status_text.text(msg)
            
        pipeline.run_pipeline_for_pages(
            pages, 
            chunk_size=int(chunk_size), 
            overlap=int(overlap),
            progress_callback=update_progress,
            run_name=run_name
        )
        
        progress_bar.progress(1.0)
        status_text.text("Done!")
        st.sidebar.success("Extraction Complete!")
        # Clear the cache so new rules and documents are reloaded
        get_run_names.clear()
        load_db_data.clear()
        load_source_document.clear()
        st.rerun()

rules_raw, tests_raw = load_db_data(st.session_state.selected_run_name)
if pdf_source:
    raw_text, raw_pages = load_source_document(pdf_source, start_page, end_page)
else:
    raw_text, raw_pages = "", []

if 'selected_citation' not in st.session_state:
    st.session_state.selected_citation = None

# Build AST forest
ast_forest = []
node_cache = {}
for r in rules_raw:
    r['children'] = []
    node_cache[str(r['id'])] = r

for r in rules_raw:
    pid = str(r['parent_id']) if r['parent_id'] else None
    if pid and pid in node_cache:
        node_cache[pid]['children'].append(r)
    elif not pid:
        ast_forest.append(r)

from streamlit_pdf_viewer import pdf_viewer

col1, col2, col3 = st.columns([1, 1, 1])

# Column 1: Rules & Tests
with col1:
    st.header("Extracted Rules")
    
    if not ast_forest:
        st.info("No rules found in database. Please run an extraction analysis.")
        
    def ast_to_logical_expression(node, depth=0):
        indent = "    " * depth
        if node['node_type'] in ('AND', 'OR'):
            children_exprs = [ast_to_logical_expression(c, depth+1) for c in node.get('children', [])]
            if not children_exprs:
                return f"{indent}()"
            
            if len(children_exprs) == 1:
                return children_exprs[0]
                
            joiner = f"\n{indent}{node['node_type']} "
            inner = joiner.join([c.lstrip() for c in children_exprs])
            return f"{indent}(\n{indent}    {inner}\n{indent})"
        else:
            field = node.get('field_name', '')
            op = node.get('operator', '')
            val = node.get('node_value', '')
            return f"{indent}{field} {op} {val}"

    def flatten_ast(node):
        res = [{k: v for k, v in node.items() if k != 'children'}]
        for c in node.get('children', []):
            res.extend(flatten_ast(c))
        return res

    for root in ast_forest:
        desc = root.get('description') or 'Rule Logic'
        title = f"{desc} (ID: {str(root['id'])[:8]})"
        with st.expander(title, expanded=False):
            st.markdown("### Formal Logical Expression")
            expr = ast_to_logical_expression(root)
            st.code(expr, language="sql")
            
            with st.expander("🛠️ View Raw Flat JSON AST"):
                # Clean up the output to resemble the original ExtractionResult flat array
                safe_json = flatten_ast(root)
                st.json(safe_json)
            
            cit = root.get('citation', '')
            pg = root.get('page_number', '?')
            ln = root.get('line_number', '?')
            st.markdown(f"**Citation Location:** Page {pg}, Line ~{ln}  \n**Context:** _{cit}_")
            
            # Button to highlight this rule
            if st.button("Highlight Rule", key=f"btn_{root['id']}"):
                st.session_state.selected_citation = root['citation']
                st.rerun()

# Column 2: Source Text (Extracted by pypdf)
with col2:
    st.header("Raw Extracted Text")
    
    escaped_text = html.escape(raw_text)
    
    # Sort citations by length so we don't accidentally replace a short substring inside a longer one
    citations = list(set([r['citation'] for r in rules_raw if r['citation']]))
    citations.sort(key=len, reverse=True)
    
    for cit in citations:
        if cit and cit.strip():
            words = cit.split()
            if not words: continue
            
            # Escape HTML to match escaped_text, then build a regex pattern 
            # to tolerate newlines and spaces separating the words in the raw PDF text
            escaped_words = [re.escape(html.escape(w)) for w in words]
            pattern_str = r'\s+'.join(escaped_words)
            
            if st.session_state.selected_citation == cit:
                # Highlight strongly if it is the selected citation
                bg = "#FFECA1" # Anthropic-like soft yellow
                border = "border: 1px solid #E6C84C;"
            else:
                # Highlight subtly for other rules
                bg = "#F0F0F0"
                border = "border: 1px solid transparent;"
                
            try:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                repl = f'<mark style="background-color: {bg}; color: inherit; padding: 2px 4px; border-radius: 4px; {border}">\\g<0></mark>'
                escaped_text = pattern.sub(repl, escaped_text)
            except Exception as e:
                pass
            
    st.markdown(f"<div class='source-doc'>{escaped_text}</div>", unsafe_allow_html=True)

# Column 3: The PDF File Viewer
with col3:
    st.header("Source PDF")
    st.caption("Native viewer")
    
    if pdf_source:
        pdf_viewer(pdf_source, width="100%", height=800)
    else:
        st.info("No PDF selected to display.")
