import streamlit as st
import json
import csv
import io
import time
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

with col2:
    st.subheader("Candidate Database Uploader")
    uploaded_file = st.file_uploader(
        "Upload candidates.jsonl file",
        type=["jsonl", "json"]
    )
    
    run_clicked = st.button("Run Ranking", use_container_width=True)

if run_clicked:
    if not uploaded_file:
        st.error("Please upload a candidates file first.")
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
            # Read and parse input file format
            file_content = uploaded_file.getvalue().decode("utf-8").strip()
            
            raw_candidates = []
            if file_content.startswith("["):
                try:
                    raw_candidates = json.loads(file_content)
                except Exception as je:
                    st.error(f"Failed to parse JSON array: {je}")
            else:
                # Parse as JSONL line by line
                for line in file_content.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw_candidates.append(json.loads(line))
                    except Exception:
                        continue
            
            total_candidates_loaded = len(raw_candidates)
            st.info(f"Loaded {total_candidates_loaded} candidates from the file. Starting scoring...")
            
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
