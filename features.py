# features.py
# Feature extraction per candidate
import datetime
from dateutil import parser
import re

MUST_HAVE_KEYWORDS = {
    "embeddings": ["embedding", "sentence-transformer", "sentence transformer", "vector search", "semantic search"],
    "vector_db": ["pinecone", "weaviate", "qdrant", "milvus", "faiss", "opensearch", "elasticsearch", "pgvector"],
    "python": ["python"],
    "ranking_eval": ["ndcg", "mrr", "map", "a-b testing", "ab testing", "a/b testing", "ranking evaluation"],
    "retrieval": [
        "retrieval system", "information retrieval", "hybrid search", "search engine",
        "recommendation system", "recommender", "recsys", "bm25", "dense retrieval",
        "sparse retrieval", "ir system", "llm", "large language model", "generative ai",
        "rag", "retrieval augmented"
    ]
}

NICE_TO_HAVE_KEYWORDS = {
    "llm_finetuning": ["fine-tuning", "fine tuning", "finetuning", "lora", "qlora", "peft"],
    "ltr": ["learning-to-rank", "learning to rank", "xgboost ranking", "lambdarank", "lambda-rank", "lambdamart", "lambda-mart"],
    "nlp": ["nlp", "transformers", "bert", "natural language processing"],
    "distributed": ["distributed system", "large-scale inference", "large scale inference", "kubernetes", "spark", "triton", "ray"]
}

NEGATIVE_KEYWORDS = [
    "computer vision", "speech recognition", "robotics", "image processing", 
    "object detection", "yolo", "opencv", "ocr", "speech to text", 
    "speech-to-text", "text to speech", "text-to-speech", "asr", "tts"
]

def score_core_skills(candidate: dict) -> float:
    """
    Computes a core skills match score from 0.0 to 1.0 based on MUST HAVE and NICE TO HAVE categories.
    Applies a penalty if CV/speech/robotics is the dominant domain.
    """
    summary = candidate.get("profile", {}).get("summary", "")
    summary_lower = summary.lower() if summary else ""
    
    headline = candidate.get("profile", {}).get("headline", "")
    headline_lower = headline.lower() if headline else ""
    
    skills = candidate.get("skills", [])
    processed_skills = []
    for s in skills:
        s_name = s.get("name", "")
        if s_name:
            processed_skills.append({
                "name_lower": s_name.lower(),
                "proficiency_lower": s.get("proficiency", "").lower(),
                "endorsements": s.get("endorsements", 0) or 0
            })
            
    career_history = candidate.get("career_history", [])
    processed_jobs = []
    for job in career_history:
        desc = job.get("description", "")
        processed_jobs.append({
            "desc_lower": desc.lower() if desc else "",
            "title_lower": job.get("title", "").lower() if job.get("title") else ""
        })

    total_must_have_score = 0.0
    # Process Must-Have Categories (Max 10.0 pts per category)
    for cat_name, keywords in MUST_HAVE_KEYWORDS.items():
        cat_score = 0.0
        # Skills check
        for skill in processed_skills:
            if any(kw in skill["name_lower"] for kw in keywords):
                prof = skill["proficiency_lower"]
                endorsements = skill["endorsements"]
                base = 1.0
                if prof == "intermediate":
                    base = 1.5
                elif prof == "advanced":
                    base = 2.0
                elif prof == "expert":
                    base = 3.0
                cat_score += base * (1.0 + min(endorsements, 20) * 0.1)
        
        # Summary check
        if summary_lower and any(kw in summary_lower for kw in keywords):
            cat_score += 1.5
            
        # Headline check
        if headline_lower and any(kw in headline_lower for kw in keywords):
            cat_score += 2.0
            
        # Career History check
        for job in processed_jobs:
            if job["desc_lower"] and any(kw in job["desc_lower"] for kw in keywords):
                cat_score += 1.0
                
        total_must_have_score += min(cat_score, 10.0)

    total_nice_to_have_score = 0.0
    # Process Nice-to-Have Categories (Max 5.0 pts per category)
    for cat_name, keywords in NICE_TO_HAVE_KEYWORDS.items():
        cat_score = 0.0
        # Skills check
        for skill in processed_skills:
            if any(kw in skill["name_lower"] for kw in keywords):
                prof = skill["proficiency_lower"]
                endorsements = skill["endorsements"]
                base = 1.0
                if prof == "intermediate":
                    base = 1.5
                elif prof == "advanced":
                    base = 2.0
                elif prof == "expert":
                    base = 3.0
                cat_score += base * (1.0 + min(endorsements, 20) * 0.1)
        
        # Summary check
        if summary_lower and any(kw in summary_lower for kw in keywords):
            cat_score += 1.5
            
        # Headline check
        if headline_lower and any(kw in headline_lower for kw in keywords):
            cat_score += 2.0
            
        # Career History check
        for job in processed_jobs:
            if job["desc_lower"] and any(kw in job["desc_lower"] for kw in keywords):
                cat_score += 1.0
                
        total_nice_to_have_score += min(cat_score, 5.0)

    # Calculate raw score (5 must_haves @ max 10.0 + 4 nice_to_haves @ max 5.0 = 70.0 max)
    # Check for skill assessments bonus: score >= 70 containing any MUST HAVE keyword
    assessment_bonus = 0.0
    all_must_haves = [kw.lower() for kws in MUST_HAVE_KEYWORDS.values() for kw in kws]
    signals = candidate.get("redrob_signals", {})
    assessments = signals.get("skill_assessment_scores", {})
    for ass_name, ass_score in assessments.items():
        if ass_score is not None and ass_score >= 70:
            if any(kw in ass_name.lower() for kw in all_must_haves):
                assessment_bonus = 0.15
                break

    raw_score = total_must_have_score + total_nice_to_have_score + assessment_bonus
    score = min(raw_score / 70.0, 1.0)

    # Domain dominant penalty: more than 2 career history roles in CV/speech/robotics/image processing
    cv_speech_roles = 0
    for job in processed_jobs:
        if any(kw in job["title_lower"] for kw in NEGATIVE_KEYWORDS) or any(kw in job["desc_lower"] for kw in NEGATIVE_KEYWORDS):
            cv_speech_roles += 1

    if cv_speech_roles > 2:
        score = score * 0.5

    return score

def classify_title(title: str) -> float:
    t = title.lower()
    # Check low/zero first
    if any(w in t for w in ["marketing", "operations", "hr", "finance", "sales", "customer support", "support", "mechanical", "accountant", "recruiter", "admin"]):
        return 0.0
    # Check high
    if any(w in t for w in ["ml engineer", "ai engineer", "nlp engineer", "search engineer", "ranking engineer", "applied scientist", "research engineer"]):
        return 1.0
    if "data scientist" in t:
        return 1.0
    if "machine learning" in t or "artificial intelligence" in t or "deep learning" in t:
        return 1.0
    # Check medium
    if any(w in t for w in ["software engineer", "backend engineer", "data engineer", "analytics engineer", "systems engineer", "developer", "programmer", "full stack", "fullstack"]):
        return 0.5
    # Default
    return 0.3

def score_career_trajectory(candidate: dict) -> float:
    """
    Evaluates career trajectory based on title relevance, company type (product vs service),
    tenure signals, and title/responsibility progression. Returns a score between 0.0 and 1.0.
    """
    career_history = candidate.get("career_history", [])
    
    # 1. Title Relevance (35%)
    t_scores = []
    current_title = candidate.get("profile", {}).get("current_title", "")
    if current_title:
        t_scores.append(classify_title(current_title))
    for job in career_history[:2]:
        t_scores.append(classify_title(job.get("title", "")))
        
    if not t_scores:
        title_score = 0.0
    elif len(t_scores) == 1:
        title_score = t_scores[0]
    elif len(t_scores) == 2:
        title_score = t_scores[0] * 0.6 + t_scores[1] * 0.4
    else:
        title_score = t_scores[0] * 0.5 + t_scores[1] * 0.25 + t_scores[2] * 0.25

    # 2. Product vs Services Company (30%)
    services_keywords = ["tcs", "wipro", "infosys", "accenture", "cognizant", "capgemini", "hcl", "tech mahindra", "mphasis", "tata consultancy services"]
    has_services = False
    has_product = False
    product_before_services = False
    
    # Iterate oldest to newest
    for job in reversed(career_history):
        company = job.get("company", "").lower()
        is_service = any(svc in company for svc in services_keywords)
        if is_service:
            has_services = True
        else:
            has_product = True
            if not has_services:
                product_before_services = True
                
    if not career_history:
        # Check current company
        curr_company = candidate.get("profile", {}).get("current_company", "").lower()
        is_service = any(svc in curr_company for svc in services_keywords)
        if is_service:
            company_score = 0.1
        else:
            company_score = 1.0
    elif has_product and not has_services:
        company_score = 1.0  # Pure product company career
    elif has_services and has_product:
        if product_before_services:
            company_score = 0.6  # Product then services (partial credit)
        else:
            company_score = 0.8  # Services then product (pivot is good!)
    else:
        company_score = 0.1  # Entirely IT services

    # 3. Tenure Signals (20%)
    tenures = [job.get("duration_months", 0) or 0 for job in career_history]
    avg_tenure = sum(tenures) / len(tenures) if tenures else 0.0
    
    tenure_score = 0.5  # Neutral base
    # strong job-hopper check: 2+ roles under 18 months
    under_18_count = sum(1 for t in tenures if t < 18)
    if under_18_count >= 2:
        tenure_score -= 0.4
    elif avg_tenure < 18 and len(tenures) > 1:
        tenure_score -= 0.3  # average tenure penalty
        
    if any(t > 24 for t in tenures):
        tenure_score += 0.5  # stability bonus
    tenure_score = max(0.0, min(tenure_score, 1.0))

    # 4. Progression (15%)
    levels = []
    for job in reversed(career_history):
        title = job.get("title", "").lower()
        level = 2  # default
        if any(w in title for w in ["junior", "jr", "associate", "intern", "trainee"]):
            level = 1
        elif any(w in title for w in ["senior", "sr.", "sr ", "lead", "principal", "staff"]):
            level = 3
        elif any(w in title for w in ["manager", "director", "vp", "head", "chief", "architect"]):
            level = 4
        levels.append(level)
        
    if len(levels) <= 1:
        progression_score = 0.5
    elif levels[-1] > levels[0]:
        progression_score = 1.0
    elif levels[-1] == levels[0]:
        progression_score = 0.5
    else:
        progression_score = 0.2

    # Weighted Sum
    final_trajectory_score = (
        0.35 * title_score +
        0.30 * company_score +
        0.20 * tenure_score +
        0.15 * progression_score
    )
    
    # CV/speech background penalty for Junior titles
    is_junior = any(w in current_title.lower() for w in ["junior", "jr"])
    if is_junior and career_history:
        has_non_current_cv_speech = False
        non_current_jobs = career_history[1:] if career_history[0].get("is_current") else career_history
        for job in non_current_jobs:
            j_title = job.get("title", "").lower()
            j_desc = job.get("description", "").lower()
            if any(kw in j_title for kw in NEGATIVE_KEYWORDS) or any(kw in j_desc for kw in NEGATIVE_KEYWORDS):
                has_non_current_cv_speech = True
                break
        if has_non_current_cv_speech:
            final_trajectory_score = max(0.0, final_trajectory_score - 0.15)
            
    return final_trajectory_score

ML_RE = re.compile(
    r"\b(ml|ai|nlp|llm|lora|qlora|peft|bert|transformers?|deep learning|machine learning|artificial intelligence|embeddings?|vector search|semantic search|natural language processing|fine-tuning|finetuning|fine tuning|learning-to-rank|learning to rank|xgboost ranking|lambdarank)\b",
    re.IGNORECASE
)

def score_experience(candidate: dict) -> float:
    """
    Computes experience score based on years of experience and ML experience.
    """
    years = candidate.get("profile", {}).get("years_of_experience", 0.0)
    
    # Base Score based on years
    if 5.0 <= years <= 9.0:
        base_score = 1.0
    elif (4.0 <= years < 5.0) or (9.0 < years <= 11.0):
        base_score = 0.8
    elif (3.0 <= years < 4.0) or (11.0 < years <= 14.0):
        base_score = 0.5
    else:
        base_score = 0.2

    # ML experience sum
    ml_months = 0
    career_history = candidate.get("career_history", [])
    for job in career_history:
        title = job.get("title", "")
        desc = job.get("description", "")
        if (title and ML_RE.search(title)) or (desc and ML_RE.search(desc)):
            ml_months += job.get("duration_months", 0) or 0
            
    ml_years = ml_months / 12.0
    
    if ml_years >= 4.0:
        return min(base_score * 1.2, 1.0)
    return base_score

def score_location(candidate: dict) -> float:
    """
    Computes location fit score based on country, city, and willing_to_relocate.
    """
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    
    country = (profile.get("country") or "").strip().lower()
    location = (profile.get("location") or "").strip().lower()
    willing_to_relocate = signals.get("willing_to_relocate", False)
    
    if country != "india":
        if not willing_to_relocate:
            return 0.0
        return 0.5
        
    # country is India
    preferred_cities = ["pune", "noida", "hyderabad", "mumbai", "delhi", "gurgaon", "ncr"]
    if any(city in location for city in preferred_cities):
        return 1.0
    if "bangalore" in location or "bengaluru" in location:
        return 0.85
        
    if willing_to_relocate:
        return 0.7
    return 0.4

def score_behavioral(candidate: dict) -> float:
    """
    Computes a behavioral score from 0.3 to 1.0 based on activity, availability,
    responsiveness, reliability, notice period, and profile verifications.
    """
    signals = candidate.get("redrob_signals", {})
    
    # 1. days_since_active
    last_active_str = signals.get("last_active_date")
    ref_date = datetime.date(2026, 6, 6)
    
    try:
        active_date = parser.parse(last_active_str).date()
        days_since_active = (ref_date - active_date).days
    except Exception:
        days_since_active = 365
        
    if days_since_active > 180:
        base_activity = 0.3
    elif 90 <= days_since_active <= 180:
        base_activity = 0.55
    elif 30 <= days_since_active < 90:
        base_activity = 0.75
    else:
        base_activity = 1.0

    score = base_activity

    # 2. Availability bonus
    if signals.get("open_to_work_flag", False) is True:
        score += 0.05
    if (signals.get("applications_submitted_30d", 0) or 0) > 2:
        score += 0.03

    # 3. Responsiveness score
    response_rate = signals.get("recruiter_response_rate", 0.0) or 0.0
    if response_rate > 0.7:
        score += 0.05
    elif response_rate < 0.2:
        score -= 0.1
        
    avg_resp_time = signals.get("avg_response_time_hours", 999.0) or 999.0
    if avg_resp_time < 12.0:
        score += 0.02

    # 4. Reliability
    interview_rate = signals.get("interview_completion_rate", 0.0) or 0.0
    if interview_rate >= 0.8:
        score += 0.04
    elif interview_rate < 0.4:
        score -= 0.08

    # 5. Notice period
    notice_days = signals.get("notice_period_days", 0) or 0
    if notice_days <= 15:
        score += 0.08  # extra bonus for immediate/short notice
    elif 16 <= notice_days <= 30:
        score += 0.04
    elif 31 <= notice_days <= 60:
        pass
    elif 61 <= notice_days <= 90:
        score -= 0.02
    else:
        score -= 0.06

    # 6. Verification
    if signals.get("verified_email", False) is True and signals.get("verified_phone", False) is True:
        score += 0.03

    # Clamp
    return max(0.3, min(score, 1.0))

def extract_features(candidate: dict) -> dict:
    """
    Parses a single candidate dictionary and extracts a fixed feature vector/dict.
    """
    return {
        "core_skills_score": score_core_skills(candidate),
        "career_trajectory_score": score_career_trajectory(candidate),
        "experience_score": score_experience(candidate),
        "location_score": score_location(candidate),
        "behavioral_score": score_behavioral(candidate)
    }

