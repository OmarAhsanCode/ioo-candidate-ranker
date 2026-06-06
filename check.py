# check.py
import csv
import gzip
import json
import math
import os
import datetime
from dateutil import parser

def load_submission(csv_path):
    ranks = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if row:
                cid = row[0]
                rank = int(row[1])
                score = float(row[2])
                ranks[cid] = (rank, score)
    return ranks

def load_candidates_from_jsonl(jsonl_path, targets):
    is_gzip = jsonl_path.endswith(".gz")
    open_func = gzip.open if is_gzip else open
    mode = "rt" if is_gzip else "r"
    
    profiles = {}
    with open_func(jsonl_path, mode, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            cand = json.loads(line)
            cid = cand.get("candidate_id")
            if cid in targets:
                profiles[cid] = cand
                if len(profiles) == len(targets):
                    break
    return profiles

def get_percentile(sorted_data, p):
    n = len(sorted_data)
    if n == 0:
        return 0.0
    idx = p * (n - 1)
    idx_floor = int(idx)
    idx_ceil = min(idx_floor + 1, n - 1)
    weight = idx - idx_floor
    return sorted_data[idx_floor] * (1.0 - weight) + sorted_data[idx_ceil] * weight

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "submission.csv")
    jsonl_path = os.path.join(script_dir, "candidates.jsonl")
    report_path = os.path.join(script_dir, "check_report.txt")
    
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return
    if not os.path.exists(jsonl_path):
        print(f"Error: {jsonl_path} not found.")
        return

    output_lines = []
    def log(msg):
        output_lines.append(msg)
        print(msg)

    log("Loading submission...")
    sub_data = load_submission(csv_path)
    
    log("Loading candidate details from JSONL...")
    candidate_profiles = load_candidates_from_jsonl(jsonl_path, set(sub_data.keys()))
    
    # Assemble list and sort by rank
    ranked_list = []
    for cid, (rank, score) in sub_data.items():
        profile = candidate_profiles.get(cid, {})
        ranked_list.append({
            "rank": rank,
            "candidate_id": cid,
            "score": score,
            "profile": profile
        })
        
    ranked_list.sort(key=lambda x: x["rank"])
    
    services_keywords = ["tcs", "wipro", "infosys", "accenture", "cognizant", "capgemini", "hcl", "tech mahindra", "mphasis"]
    ref_date = datetime.date(2026, 6, 6)
    
    log("\n" + "="*90)
    log(f"{'Rank':<5} | {'Candidate ID':<12} | {'Score':<8} | {'Title':<30} | {'YoE':<5} | {'Location':<20} | {'Flags'}")
    log("="*90)
    
    for item in ranked_list:
        rank = item["rank"]
        cid = item["candidate_id"]
        score = item["score"]
        cand = item["profile"]
        
        prof = cand.get("profile", {})
        title = prof.get("current_title", "N/A")
        yoe = prof.get("years_of_experience", 0.0)
        loc = prof.get("location", "N/A")
        
        flags = []
        
        # 1. Non-engineering title in top 20
        # Classified as low title score
        non_eng_keywords = ["marketing", "operations", "hr", "finance", "sales", "customer support", "support", "mechanical", "accountant", "recruiter", "admin"]
        is_non_eng = any(w in title.lower() for w in non_eng_keywords)
        if rank <= 20 and is_non_eng:
            flags.append("[FLAG: Non-Eng Title]")
            
        # 2. < 3 years experience in top 20
        if rank <= 20 and yoe < 3.0:
            flags.append("[FLAG: YoE < 3]")
            
        # 3. Pure consulting background in top 10
        career_history = cand.get("career_history", [])
        if rank <= 10 and career_history:
            has_product = False
            for job in career_history:
                company = job.get("company", "").lower()
                is_service = any(svc in company for svc in services_keywords)
                if not is_service:
                    has_product = True
                    break
            if not has_product:
                flags.append("[FLAG: Pure Consulting]")
                
        # 4. last_active_date > 90 days ago in top 10
        signals = cand.get("redrob_signals", {})
        last_active_str = signals.get("last_active_date")
        if rank <= 10 and last_active_str:
            try:
                active_date = parser.parse(last_active_str).date()
                days_since = (ref_date - active_date).days
                if days_since > 90:
                    flags.append(f"[FLAG: Inactive {days_since}d]")
            except:
                pass
                
        flags_str = ", ".join(flags) if flags else "-"
        # Truncate title and location for formatting
        title_disp = title[:28] + ".." if len(title) > 30 else title
        loc_disp = loc[:18] + ".." if len(loc) > 20 else loc
        
        log(f"{rank:<5} | {cid:<12} | {score:<8.4f} | {title_disp:<30} | {yoe:<5.1f} | {loc_disp:<20} | {flags_str}")
        
    log("="*90)
    
    # 5. Score Distribution
    scores = [item["score"] for item in ranked_list]
    sorted_scores = sorted(scores)
    min_val = sorted_scores[0]
    max_val = sorted_scores[-1]
    median = get_percentile(sorted_scores, 0.5)
    p25 = get_percentile(sorted_scores, 0.25)
    p75 = get_percentile(sorted_scores, 0.75)
    
    log("\nScore Distribution:")
    log(f"  Min Score:    {min_val:.4f}")
    log(f"  25th Pctl:    {p25:.4f}")
    log(f"  Median (p50): {median:.4f}")
    log(f"  75th Pctl:    {p75:.4f}")
    log(f"  Max Score:    {max_val:.4f}")
    log("="*90 + "\n")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines) + "\n")

if __name__ == "__main__":
    main()
