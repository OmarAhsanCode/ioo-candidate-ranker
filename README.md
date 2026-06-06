# AI-Powered Candidate Ranking System

An AI-powered candidate ranking system built for the **India Runs at Active Skills — Data & AI Challenge 2026**.

This system automates the screening process of candidate profiles against a Senior AI Engineer role at Redrob, filtering out unqualified profiles, identifying timeline inconsistencies (honeypots), and ranking candidates using a robust, multi-layer evaluation metric.

---

## 🚀 Live Demo & Repository
* **Live Demo**: [Hugging Face Spaces](https://huggingface.co/spaces/OmarAhsan/ioo-candidate-ranker)
* **GitHub Repository**: [OmarAhsanCode/ioo-candidate-ranker](https://github.com/OmarAhsanCode/ioo-candidate-ranker)

---

## 🛠️ The Approach
The system employs a two-stage evaluation pipeline:

### 1. Stage 1: Feature Extraction & Timeline Integrity (Layer 1)
* **Honeypot Checker**: Disqualifies candidates claiming impossible employment histories (e.g., working before plausible age of birth), contradictory experience lengths, and inflated completeness claims.
* **Hard Filters**: Filters out pure IT consulting/services workers, non-engineering roles, and domain mismatches (such as Computer Vision, Speech, or Robotics specialists) to prioritize core NLP and Search specialists.

### 2. Stage 2: Weighted Composite Scoring & Behavioral Scaling (Layer 2)
Computes a JD compatibility score and multiplies it by a behavioral scale (from 0.3x to 1.0x).
* **Core Skills Compatibility (35% weight)**: Matches experience with vector databases (Pinecone, Weaviate, Qdrant, FAISS), RAG architectures, hybrid retrieval methods, and awards bonuses for technical assessment scores $\ge 70$.
* **Career Trajectory & Stability (30% weight)**: Evaluates role progression and applies penalties for frequent job-hopping (consecutive roles under 18 months).
* **Total Relevant Experience (15% weight)**: Linearly scores candidate tenure up to target Senior level experience.
* **Location Fit (15% weight)**: Prioritizes India-based candidates and candidates willing to relocate.
* **Education Quality (5% weight)**: Tie-breaker scoring for top-tier CS/ML academic qualifications.
* **Behavioral Multiplier**: Dynamically adjusts score based on platform engagement, notice periods (<=30 days favored), response rates, and profile verifications.

---

## 📁 File Structure
* `app.py`: Interactive Streamlit application to upload candidate files and visualize top candidates.
* `rank.py`: Primary CLI pipeline orchestrator to rank bulk candidate files and output `submission.csv`.
* `scorer.py`: Integrates sub-scorers and computes candidate composite rankings.
* `features.py`: Implements metrics for grading skills, career history, experience, location, and behavioral profiles.
* `honeypot.py`: Filters timeline errors and fraud claims.
* `reasoning.py`: Formulates automated, unique 1-2 sentence justification summaries for ranks.
* `check.py` & `debug.py`: Quality assurance tools to analyze score distributions and profile debug properties.

---

## 💻 How to Run Locally

### 1. Setup & Installation
```bash
pip install -r requirements.txt
```

### 2. Run Streamlit UI Dashboard
```bash
streamlit run app.py
```

### 3. Run Pipeline CLI
```bash
python rank.py --candidates candidates.jsonl --out submission.csv
```

---

## 👥 Team IOO
* **Iqra**
* **Omar Ahsan**
* **Ojas**
