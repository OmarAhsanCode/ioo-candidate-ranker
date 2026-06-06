# reasoning.py
import datetime
from dateutil import parser

def generate_reasoning(candidate: dict, score: float, rank: int) -> str:
    """
    Generates a 1-2 sentence reasoning string matching the candidate's rank.
    """
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    career_history = candidate.get("career_history", [])
    
    title = profile.get("current_title", "AI/ML Engineer")
    yoe = profile.get("years_of_experience", 0.0)
    
    # 1. Extract 1-2 specific matching skills
    skills = candidate.get("skills", [])
    # Prioritize expert/advanced skills related to JD
    jd_keywords = ["embedding", "vector", "search", "python", "ndcg", "mrr", "map", "retrieval", "llm", "lora", "peft", "nlp", "transformer", "bert", "distributed", "spark", "kubernetes"]
    
    strong_skills = [s.get("name") for s in skills if s.get("proficiency") in ["expert", "advanced"]]
    matched_skills = []
    for s_name in strong_skills:
        if any(kw in s_name.lower() for kw in jd_keywords):
            matched_skills.append(s_name)
            
    # Fallback to other skills if none of the top skills matched JD keywords directly
    if len(matched_skills) < 2:
        for s_name in strong_skills:
            if s_name not in matched_skills:
                matched_skills.append(s_name)
    if len(matched_skills) < 2:
        # Check any skill
        for s in skills:
            s_name = s.get("name")
            if s_name not in matched_skills:
                matched_skills.append(s_name)
                
    skills_list = [s for s in matched_skills if s][:2]
    skills_phrase = " and ".join(skills_list) if skills_list else "ML/AI engineering"

    # 2. Extract company/industry signals
    services_keywords = ["tcs", "wipro", "infosys", "accenture", "cognizant", "capgemini", "hcl", "tech mahindra", "mphasis"]
    has_services = False
    has_product = False
    for job in career_history:
        comp = job.get("company", "").lower()
        if any(svc in comp for svc in services_keywords):
            has_services = True
        else:
            has_product = True
            
    company_type_str = "product companies" if (has_product and not has_services) else "services background"
    if has_product and has_services:
        company_type_str = "mixed product and services background"

    # 3. Calculate activity days
    last_active_str = signals.get("last_active_date")
    ref_date = datetime.date(2026, 6, 6)
    try:
        active_date = parser.parse(last_active_str).date()
        days_since = (ref_date - active_date).days
    except:
        days_since = 30
        
    notice = signals.get("notice_period_days", 0)
    loc = profile.get("location", "India")
    willing = signals.get("willing_to_relocate", False)

    # Generate reasoning based on rank
    if rank <= 20:
        # Strong: leads with strengths
        active_phrase = f"active on platform (logged in {days_since} days ago)" if days_since < 30 else "solid trajectory"
        reason = (
            f"Strong fit: {title} with {yoe} YoE; production expertise in {skills_phrase} "
            f"and experience at {company_type_str}; {active_phrase} with a {notice}-day notice."
        )
    elif 21 <= rank <= 70:
        # Balanced: strength + one concern
        # Find a primary concern
        if has_services and not has_product:
            concern = "entire career is at IT services firms"
        elif notice > 60:
            concern = f"notice period is high at {notice} days"
        elif not willing and "india" not in loc.lower():
            concern = "located internationally with no relocation willingness"
        else:
            concern = "requires location relocation alignment"
            
        reason = (
            f"Qualified {title} ({yoe} YoE) showing strong proficiency in {skills_phrase}; "
            f"included despite concern regarding {concern} due to solid skill alignment."
        )
    else:
        # Borderline (71-100): honest about why they're borderline
        if has_services:
            concern = f"entire career is at IT services firms and location is {loc}"
        elif notice > 90:
            concern = f"a long {notice}-day notice period"
        else:
            concern = "marginal core JD match scores"
            
        reason = (
            f"Borderline pick: {title} with {yoe} YoE who offers relevant {skills_phrase} experience; "
            f"retained for technical depth despite weaker signals on {concern}."
        )

    # Ensure no double spacing or formatting glitches
    reason = " ".join(reason.split())
    return reason
