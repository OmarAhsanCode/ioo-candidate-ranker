import streamlit as st
import json
import csv
import io
import time
import os
from typing import Iterator
import pandas as pd

# Import our backend components
from scorer import score_candidate
from reasoning import generate_reasoning
from honeypot import is_honeypot

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
            
            # Display Download Button
            st.markdown("### Download Results")
            st.download_button(
                label="Download Top 100 as submission.csv",
                data=csv_buffer.getvalue(),
                file_name="submission.csv",
                mime="text/csv",
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
