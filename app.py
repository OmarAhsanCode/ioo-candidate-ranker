import streamlit as st
import json
import csv
import io
import time
import os
from typing import Iterator
import pandas as pd
from fpdf import FPDF

# Import our backend components
from scorer import score_candidate
from reasoning import generate_reasoning
from honeypot import is_honeypot

class CandidateReportPDF(FPDF):
    def header(self):
        # Draw a beautiful dark slate banner at the top
        self.set_fill_color(30, 41, 59) # Slate 800
        self.rect(0, 0, 210, 35, "F")
        
        self.set_text_color(255, 255, 255)
        self.set_font("helvetica", "B", 16)
        # Shift Y down slightly inside the banner
        self.set_y(8)
        self.cell(0, 8, "IOO CANDIDATE RANKING SYSTEM", new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("helvetica", "I", 10)
        self.cell(0, 6, "AI-Powered Evaluation & Shortlist Report", new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_y(35) # reset Y below banner
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(100, 116, 139) # Slate 500
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}} | Team IOO - Confidential", align="C")

def clean_txt(text: str) -> str:
    if not text:
        return ""
    # Replace common unicode punctuation with ASCII equivalents
    replacements = {
        "\u201c": '"', "\u201d": '"', # smart quotes
        "\u2018": "'", "\u2019": "'", # smart apostrophes
        "\u2013": "-", "\u2014": "-", # dashes
        "\u2022": "*", # bullet points
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", errors="replace").decode("latin-1")

def generate_pdf_report(top_100) -> bytes:
    pdf = CandidateReportPDF()
    pdf.set_margin(10)
    pdf.add_page()
    
    # Metadata/Summary Block
    pdf.set_text_color(15, 23, 42) # Slate 900
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Evaluation Summary", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 6, f"Date: {time.strftime('%Y-%m-%d')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Total Candidates Ranked: {len(top_100)}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    pdf.set_font("helvetica", size=8)
    
    with pdf.table(
        col_widths=(12, 28, 15, 38, 27, 70),
        align="CENTER",
        cell_fill_color=(248, 250, 252), # Slate 50
        cell_fill_mode="ROWS",
        line_height=5
    ) as table:
        # Header Row
        pdf.set_fill_color(30, 41, 59)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("helvetica", "B", 8)
        
        row = table.row()
        row.cell("Rank")
        row.cell("Candidate ID")
        row.cell("Score")
        row.cell("Current Title")
        row.cell("Location")
        row.cell("Reasoning")
        
        # Reset fonts/colors for body
        pdf.set_text_color(15, 23, 42)
        pdf.set_font("helvetica", "", 8)
        
        for item in top_100:
            row = table.row()
            row.cell(clean_txt(str(item.get("rank", ""))))
            row.cell(clean_txt(str(item.get("candidate_id", ""))))
            row.cell(clean_txt(f"{item.get('score', 0.0):.2f}"))
            row.cell(clean_txt(str(item.get("title", "N/A"))))
            row.cell(clean_txt(str(item.get("location", "N/A"))))
            row.cell(clean_txt(str(item.get("reasoning", "N/A"))))
            
    return bytes(pdf.output())


st.set_page_config(
    page_title="Accurate Candidate Ranking System",
    layout="wide"
)

st.title("Accurate Candidate Ranking System")
st.markdown("---")

# Layout columns for inputs
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Job Description")
    jd_text = st.text_area(
        "Paste the Job Description here",
        placeholder="e.g. Seeking a Senior AI Engineer with experience in vector search, RAG, Information Retrieval, and Python...",
        height=250
    )

# Load sample candidate file helper
sample_file_path = "sample_candidates.json"
sample_data_content = ""
if os.path.exists(sample_file_path):
    try:
        with open(sample_file_path, "r", encoding="utf-8") as sf:
            sample_data_content = sf.read()
    except Exception:
        pass

with col2:
    st.subheader("Candidate Database Uploader")
    
    # Load Sample button
    load_sample_clicked = st.button("Load Sample Candidates", use_container_width=True)
    
    uploaded_file = st.file_uploader(
        "Or upload your candidates.jsonl file",
        type=["jsonl", "json"]
    )
    
    st.info("Your file must follow the Redrob candidate schema. Download a sample file to see the expected format.")
    
    if sample_data_content:
        st.download_button(
            label="Download sample_candidates.json template",
            data=sample_data_content,
            file_name="sample_candidates.json",
            mime="application/json",
            use_container_width=True
        )
    
    run_clicked = st.button("Run Ranking", use_container_width=True)

# Determine file data sources
file_source = None
if load_sample_clicked:
    if sample_data_content:
        file_source = sample_data_content
        st.toast("Loaded sample candidates database!")
    else:
        st.error("Sample candidate file template not found in workspace root.")
elif uploaded_file:
    try:
        file_source = uploaded_file.getvalue().decode("utf-8").strip()
    except Exception as e:
        st.error(f"Failed to decode uploaded file: {e}")

if run_clicked or load_sample_clicked:
    if not file_source:
        st.error("Please upload a candidates file or click 'Load Sample Candidates' first.")
    else:
        st.info("Processing candidates database... Please wait.")
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        
        # Load and parse candidates
        scored_candidates = []
        honeypots_count = 0
        it_services_filtered_count = 0
        services_keywords = ["tcs", "wipro", "infosys", "accenture", "cognizant", "capgemini", "hcl", "tech mahindra", "mphasis", "tata consultancy services"]
        
        start_time = time.time()
        
        try:
            raw_candidates = []
            if file_source.startswith("["):
                try:
                    raw_candidates = json.loads(file_source)
                except Exception as je:
                    st.error(f"Failed to parse JSON array: {je}")
            else:
                # Parse as JSONL line by line
                for line in file_source.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw_candidates.append(json.loads(line))
                    except Exception:
                        continue
            
            total_candidates_loaded = len(raw_candidates)
            st.info(f"Loaded {total_candidates_loaded} candidates from the database. Starting scoring...")
            
            for idx, candidate in enumerate(raw_candidates):
                cid = candidate.get("candidate_id")
                if not cid:
                    continue
                
                is_hp = is_honeypot(candidate)
                if is_hp:
                    honeypots_count += 1
                
                if not is_hp:
                    career_history = candidate.get("career_history", [])
                    if career_history:
                        has_product = False
                        for job in career_history:
                            company = job.get("company", "").lower()
                            is_service = any(svc in company for svc in services_keywords)
                            if not is_service:
                                has_product = True
                                break
                        if not has_product:
                            it_services_filtered_count += 1
                
                score = score_candidate(candidate)
                scored_candidates.append({
                    "candidate_id": cid,
                    "score": score,
                    "candidate": candidate
                })
                
                # Update progress occasionally
                if (idx + 1) % max(1, total_candidates_loaded // 10) == 0 or idx == total_candidates_loaded - 1:
                    progress_bar.progress(min(1.0, (idx + 1) / total_candidates_loaded))
                    status_text.text(f"Scored {idx + 1} of {total_candidates_loaded} profiles...")
            
            # Sort: score descending, then candidate_id ascending for tie-breaker
            scored_candidates.sort(key=lambda x: (-x["score"], x["candidate_id"]))
            
            runtime = time.time() - start_time
            st.success(f"Successfully processed {len(scored_candidates)} candidates in {runtime:.2f} seconds!")
            
            # Show summary metrics
            m_col1, m_col2, m_col3 = st.columns(3)
            with m_col1:
                st.metric("Total Candidates Scored", len(scored_candidates))
            with m_col2:
                st.metric("Honeypots Detected & Removed", honeypots_count)
            with m_col3:
                st.metric("IT-Services-Only Filtered", it_services_filtered_count)
            
            # Generate top 100 for output
            top_100 = []
            for rank_idx, item in enumerate(scored_candidates[:100], 1):
                cid = item.get("candidate_id", "N/A")
                score = item.get("score", 0.0)
                cand = item.get("candidate", {})
                reason = generate_reasoning(cand, score, rank_idx) if cand else "N/A"
                top_100.append({
                    "candidate_id": cid,
                    "rank": rank_idx,
                    "score": score,
                    "reasoning": reason,
                    "title": cand.get("profile", {}).get("current_title", "N/A") if cand else "N/A",
                    "location": cand.get("profile", {}).get("location", "N/A") if cand else "N/A"
                })
            
            # Export CSV to memory
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(["candidate_id", "rank", "score", "reasoning"])
            for item in top_100:
                writer.writerow([item["candidate_id"], item["rank"], item["score"], item["reasoning"]])
            
            # Display Download Buttons
            st.markdown("### Download Results")
            dl_col1, dl_col2 = st.columns(2)
            with dl_col1:
                st.download_button(
                    label="Download Top 100 as submission.csv",
                    data=csv_buffer.getvalue(),
                    file_name="submission.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with dl_col2:
                pdf_data = generate_pdf_report(top_100)
                st.download_button(
                    label="Download Top 100 as report.pdf",
                    data=pdf_data,
                    file_name="ioo_candidate_ranking_report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            # Display Top 20 Table
            st.markdown("### Top 20 Candidates Shortlist")
            top_20_list = []
            for item in top_100[:20]:
                top_20_list.append({
                    "Rank": item.get("rank", "N/A"),
                    "Candidate ID": item.get("candidate_id", "N/A"),
                    "Score": item.get("score", "N/A"),
                    "Title": item.get("title", "N/A"),
                    "Location": item.get("location", "N/A"),
                    "Reasoning": item.get("reasoning", "N/A")
                })
            top_20_df = pd.DataFrame(top_20_list)
            st.dataframe(top_20_df, use_container_width=True, hide_index=True)
            
        except Exception as e:
            st.error(f"Failed to process files: {e}")
