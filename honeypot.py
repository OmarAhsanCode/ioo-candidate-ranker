# honeypot.py
# Honeypot/trap detection logic

def is_honeypot(candidate: dict) -> bool:
    """
    Returns True if the candidate is flagged as a honeypot/trap.
    
    Checks:
    1. Timeline impossibility: job start_date is before plausible birth year (working before age 16).
    2. Skills contradiction: 3+ expert skills with duration_months = 0.
    3. Experience contradiction: claimed experience twice what history shows.
    4. Impossible completeness: profile completeness is 100 but summary or career history is empty/missing.
    """
    # 1. Timeline Impossibility (Simpler proxy)
    # years_of_experience implies starting work around age 22, birth year = 2026 - years_of_experience - 22.
    # If they worked before age 16 (start_date < birth_year + 16), flag it.
    years_of_experience = candidate.get("profile", {}).get("years_of_experience", 0.0)
    # Earliest work year allowed = 2026 - years_of_experience - 22 + 16 = 2026 - years_of_experience - 6
    earliest_plausible_work_year = 2026 - years_of_experience - 6
    
    career_history = candidate.get("career_history", [])
    for job in career_history:
        start_date = job.get("start_date")
        if start_date:
            try:
                start_year = int(start_date.split("-")[0])
                if start_year < earliest_plausible_work_year:
                    return True
            except (ValueError, IndexError, AttributeError):
                pass

    # 2. Skills Contradiction
    # 3+ skills marked "expert" with duration_months = 0
    expert_zero_duration_count = 0
    skills = candidate.get("skills", [])
    for skill in skills:
        proficiency = skill.get("proficiency", "")
        duration = skill.get("duration_months", 0)
        # Note: sometimes duration_months might be null, count it as 0 if missing/null
        if duration is None:
            duration = 0
        if isinstance(proficiency, str) and proficiency.lower() == "expert" and duration == 0:
            expert_zero_duration_count += 1
            
    if expert_zero_duration_count >= 3:
        return True

    # 3. Experience Contradiction
    # profile years_of_experience = X but sum of career history duration_months / 12 < X * 0.5
    if years_of_experience > 0:
        total_months = sum(job.get("duration_months", 0) or 0 for job in career_history)
        total_history_years = total_months / 12.0
        if total_history_years < years_of_experience * 0.5:
            return True

    # 4. Impossible Completeness
    # profile_completeness_score == 100 but key fields like summary or career history are empty
    profile_completeness = candidate.get("redrob_signals", {}).get("profile_completeness_score", 0.0)
    if profile_completeness == 100:
        summary = candidate.get("profile", {}).get("summary", "")
        if not summary or (isinstance(summary, str) and summary.strip() == ""):
            return True
        if not career_history:
            return True
        # If any job in career history has empty company or title
        for job in career_history:
            if not job.get("company", "") or not job.get("title", ""):
                return True
                
    return False
