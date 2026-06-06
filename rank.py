# rank.py
import argparse
import csv
import gzip
import json
import logging
import os
import subprocess
import sys
import time
from typing import Iterator
from tqdm import tqdm

from scorer import score_candidate
from reasoning import generate_reasoning
from honeypot import is_honeypot

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

def load_candidates(path: str) -> Iterator[dict]:
    """
    Reads candidates.jsonl line by line (streaming, not all at once).
    Parses each line as JSON.
    Returns an iterator of dicts.
    Handles malformed lines gracefully (skip with a warning).
    Works with both .jsonl and .jsonl.gz (auto-detect by extension).
    """
    is_gzip = path.endswith(".gz")
    open_func = gzip.open if is_gzip else open
    mode = "rt" if is_gzip else "r"
    
    try:
        with open_func(path, mode, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as e:
                    logging.warning(f"Malformed JSON on line {line_num}: {e}")
    except FileNotFoundError:
        logging.error(f"File not found: {path}")
        return
    except Exception as e:
        logging.error(f"Error reading file {path}: {e}")
        return

def main():
    parser = argparse.ArgumentParser(description="Rank candidates for Senior AI Engineer role.")
    parser.add_argument("--candidates", type=str, required=True, help="Path to candidates.jsonl or candidates.jsonl.gz")
    parser.add_argument("--out", type=str, default="submission.csv", help="Path to output CSV (default: submission.csv)")
    args = parser.parse_args()

    print(f"Loading and scoring candidates from {args.candidates}...")
    start_time = time.time()
    
    scored_candidates = []
    
    # Counters for the summary report
    honeypots_count = 0
    it_services_filtered_count = 0
    
    services_keywords = ["tcs", "wipro", "infosys", "accenture", "cognizant", "capgemini", "hcl", "tech mahindra", "mphasis", "tata consultancy services"]
    
    for candidate in tqdm(load_candidates(args.candidates), total=100000, desc="Scoring"):
        cid = candidate.get("candidate_id")
        if not cid:
            continue
            
        # Count honeypots
        is_hp = is_honeypot(candidate)
        if is_hp:
            honeypots_count += 1
            
        # Count IT-services-only candidates (not already flagged as honeypot)
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

    # Sort: score descending, then candidate_id ascending for tie-breaker
    print("Sorting candidates...")
    scored_candidates.sort(key=lambda x: (-x["score"], x["candidate_id"]))

    # Take top 100
    top_100 = scored_candidates[:100]

    # Write to output CSV
    print(f"Writing top 100 candidates to {args.out}...")
    with open(args.out, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for rank_idx, item in enumerate(top_100, 1):
            cid = item["candidate_id"]
            score = item["score"]
            candidate = item["candidate"]
            reason = generate_reasoning(candidate, score, rank_idx)
            writer.writerow([cid, rank_idx, score, reason])

    end_time = time.time()
    runtime = end_time - start_time
    print(f"Done! Pipeline completed in {runtime:.2f} seconds.")

    # Automatically run validate_submission.py
    print("\nRunning validate_submission.py automatically...")
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        val_script = os.path.join(script_dir, "validate_submission.py")
        result = subprocess.run(
            [sys.executable, val_script, args.out],
            capture_output=True,
            text=True
        )
        print("Validation Result:")
        print(result.stdout.strip())
        if result.stderr:
            print("Validation Errors:")
            print(result.stderr.strip())
    except Exception as e:
        print(f"Failed to automatically run validation: {e}")

    # Print Summary Report
    print("\n" + "="*50)
    print("                PIPELINE SUMMARY REPORT")
    print("="*50)
    print(f"Total Honeypots Detected:            {honeypots_count}")
    print(f"Total IT-Services-Only Filtered:     {it_services_filtered_count}")
    print(f"Total Runtime:                       {runtime:.2f} seconds")
    print("-"*50)
    print("TOP 10 CANDIDATES:")
    print(f"{'Rank':<5} | {'Candidate ID':<12} | {'Score':<10} | {'Current Title'}")
    print("-"*50)
    for rank_idx, item in enumerate(top_100[:10], 1):
        cid = item["candidate_id"]
        score = item["score"]
        title = item["candidate"].get("profile", {}).get("current_title", "N/A")
        print(f"{rank_idx:<5} | {cid:<12} | {score:<10.4f} | {title}")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
