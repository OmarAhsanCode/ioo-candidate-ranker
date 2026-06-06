# scorer.py
import re
from honeypot import is_honeypot
from features import (
    score_core_skills,
    score_career_trajectory,
    score_experience,
    score_location,
    score_behavioral,
    classify_title,
    NEGATIVE_KEYWORDS
)

CS_RE = re.compile(
    r"\b(computer science|machine learning|artificial intelligence|data science|software engineering|information technology|computer engineering|cs|ml|ai|it)\b",
    re.IGNORECASE
)

def score_education(candidate: dict) -> float:
    """
    Computes education score based on tier and field of study.
    """
    education = candidate.get("education", [])
    if not education:
        return 0.3
        
    best_score = 0.0
    for edu in education:
        field = (edu.get("field_of_study") or "").strip().lower()
        degree = (edu.get("degree") or "").strip().lower()
        tier = (edu.get("tier") or "unknown").strip().lower()
        
        is_cs = False
        if CS_RE.search(field) or CS_RE.search(degree):
            is_cs = True
            
        if is_cs:
            if tier == "tier_1":
                score = 1.0
            elif tier == "tier_2":
                score = 0.8
            elif tier == "tier_3":
                score = 0.6
            else:
                score = 0.4
        else:
            # Non-CS field: 0.5 if otherwise strong, 0.3 otherwise
            yoe = candidate.get("profile", {}).get("years_of_experience", 0.0)
            skills_score = score_core_skills(candidate)
            if yoe >= 4.0 or skills_score >= 0.3:
                score = 0.5
            else:
                score = 0.3
        if score > best_score:
            best_score = score
            
    return best_score

def score_candidate(candidate: dict) -> float:
    """
    Computes final score for candidate using weighted JD scores and behavioral multiplier.
    Applies Layer 1 hard disqualifiers (zeros out these candidates).
    """
    # 1. Honeypots
    if is_honeypot(candidate):
        return 0.0
        
    # 2. Hard Disqualifier: Entire career is IT services / consulting with no product company
    services_keywords = ["tcs", "wipro", "infosys", "accenture", "cognizant", "capgemini", "hcl", "tech mahindra", "mphasis", "tata consultancy services"]
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
            return 0.0
            
    # 3. Hard Disqualifier: Current title has nothing to do with engineering
    current_title = candidate.get("profile", {}).get("current_title", "")
    if current_title and classify_title(current_title) == 0.0:
        return 0.0
        
    # 4. Hard Disqualifier: Primary domain is CV/speech/robotics, not NLP/IR
    cv_speech_roles = 0
    for job in career_history:
        title = job.get("title", "").lower()
        desc = job.get("description", "").lower()
        if any(kw in title for kw in NEGATIVE_KEYWORDS) or any(kw in desc for kw in NEGATIVE_KEYWORDS):
            cv_speech_roles += 1
    if cv_speech_roles > 2:
        return 0.0

    # Calculate component scores
    s_skills = score_core_skills(candidate)
    s_career = score_career_trajectory(candidate)
    s_exp = score_experience(candidate)
    s_location = score_location(candidate)
    s_edu = score_education(candidate)
    
    # Layer 2: JD Match Score (0-100 scale, weighted sum of inputs normalized to 0-1)
    jd_score = (
        0.35 * s_skills +
        0.30 * s_career +
        0.15 * s_exp +
        0.15 * s_location +
        0.05 * s_edu
    )
    
    # Layer 3: Behavioral availability multiplier (0.3 - 1.0)
    behavioral = score_behavioral(candidate)
    
    # Final score = JD_match_score * behavioral_multiplier
    # Convert base 0-1 to 0-100 scale
    final = (jd_score * 100.0) * behavioral
    
    return round(final, 6)
