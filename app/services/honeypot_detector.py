"""
Honeypot Candidate Detector

Identifies impossible/suspicious profiles that are planted to test if the 
ranking system actually reads profiles.

From submission spec:
"The dataset contains ~80 honeypot candidates with subtly impossible profiles:
- 8 years of experience at a company founded 3 years ago
- 'expert' proficiency in 10 skills with 0 years used
- Senior title with 1 year experience"

Submissions with >10% honeypots in top 100 are DISQUALIFIED.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime


class HoneypotDetector:
    """
    Detects honeypot (fake/impossible) candidate profiles.
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Args:
            strict_mode: If True, more aggressive detection (may have false positives)
        """
        self.strict_mode = strict_mode
        self.company_founding_dates = self._load_company_dates()
    
    def _load_company_dates(self) -> Dict[str, int]:
        """
        Known company founding years for validation.
        In production, this would be a comprehensive database.
        """
        return {
            # Major tech companies
            'google': 1998,
            'amazon': 1994,
            'microsoft': 1975,
            'apple': 1976,
            'meta': 2004,
            'facebook': 2004,
            'netflix': 1997,
            'uber': 2009,
            'airbnb': 2008,
            'stripe': 2010,
            'openai': 2015,
            'anthropic': 2021,
            
            # Indian companies
            'flipkart': 2007,
            'zomato': 2008,
            'paytm': 2010,
            'ola': 2010,
            'swiggy': 2014,
            'byju': 2011,
            
            # Consulting (common in dataset)
            'tcs': 1968,
            'infosys': 1981,
            'wipro': 1945,
            'accenture': 1989,
            'cognizant': 1994,
            'capgemini': 1967,
            
            # Others
            'mindtree': 1999,
        }
    
    def is_honeypot(self, candidate: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Check if candidate is a honeypot.
        
        Args:
            candidate: Full candidate profile dict
        
        Returns:
            (is_honeypot, reasons) tuple
            - is_honeypot: True if honeypot detected
            - reasons: List of detection reasons
        """
        reasons = []
        
        profile = candidate.get('profile', {})
        career = candidate.get('career_history', [])
        skills = candidate.get('skills', [])
        education = candidate.get('education', [])
        
        # =====================================================================
        # CHECK 1: Experience vs Company Age
        # =====================================================================
        for role in career:
            company = role.get('company', '').lower()
            duration_months = role.get('duration_months', 0)
            start_date = role.get('start_date', '')
            
            if company in self.company_founding_dates:
                founding_year = self.company_founding_dates[company]
                
                # Extract year from start_date
                if start_date:
                    try:
                        start_year = int(start_date[:4])
                        
                        # Check if started before company founded
                        if start_year < founding_year:
                            reasons.append(
                                f"Started at {role.get('company')} in {start_year}, "
                                f"but company founded in {founding_year}"
                            )
                        
                        # Check if duration exceeds company age
                        company_age_years = datetime.now().year - founding_year
                        role_years = duration_months / 12
                        
                        if role_years > company_age_years + 1:  # +1 for tolerance
                            reasons.append(
                                f"{role_years:.1f} years at {role.get('company')}, "
                                f"but company only {company_age_years} years old"
                            )
                    except (ValueError, TypeError):
                        pass
        
        # =====================================================================
        # CHECK 2: Expert Skills with Zero Duration
        # =====================================================================
        expert_zero_duration = []
        
        for skill in skills:
            proficiency = skill.get('proficiency', '')
            duration = skill.get('duration_months', 0)
            name = skill.get('name', '')
            
            if proficiency in ['advanced', 'expert'] and duration == 0:
                expert_zero_duration.append(name)
        
        if len(expert_zero_duration) >= 5:  # 5+ is suspicious
            reasons.append(
                f"{len(expert_zero_duration)} expert skills with 0 duration: "
                f"{', '.join(expert_zero_duration[:5])}"
            )
        
        # =====================================================================
        # CHECK 3: Too Many Expert Skills (Impossible Breadth)
        # =====================================================================
        expert_skills = [
            s.get('name', '') for s in skills 
            if s.get('proficiency') in ['advanced', 'expert']
        ]
        
        if len(expert_skills) >= 20:  # 20+ expert skills is unlikely
            reasons.append(
                f"{len(expert_skills)} expert-level skills (impossible breadth)"
            )
        
        # =====================================================================
        # CHECK 4: Title vs Experience Mismatch
        # =====================================================================
        yoe = profile.get('years_of_experience', 0)
        title = profile.get('current_title', '').lower()
        
        # Senior with <3 years
        if any(senior in title for senior in ['senior', 'sr.', 'lead']) and yoe < 3:
            reasons.append(
                f"Senior/Lead title ('{profile.get('current_title')}') "
                f"with only {yoe:.1f} years experience"
            )
        
        # Principal/Staff with <7 years
        if any(senior in title for senior in ['principal', 'staff', 'architect']) and yoe < 7:
            reasons.append(
                f"Principal/Staff title ('{profile.get('current_title')}') "
                f"with only {yoe:.1f} years experience"
            )
        
        # Director/VP with <10 years
        if any(exec in title for exec in ['director', 'vp', 'vice president']) and yoe < 10:
            reasons.append(
                f"Executive title ('{profile.get('current_title')}') "
                f"with only {yoe:.1f} years experience"
            )
        
        # =====================================================================
        # CHECK 5: Education Dates vs Career Dates
        # =====================================================================
        if education and career:
            # Get most recent education end year
            edu_end_years = [
                edu.get('end_year', 0) for edu in education 
                if edu.get('end_year', 0) > 0
            ]
            
            if edu_end_years:
                latest_edu_year = max(edu_end_years)
                
                # Check if any role started before education ended
                for role in career:
                    start_date = role.get('start_date', '')
                    if start_date:
                        try:
                            start_year = int(start_date[:4])
                            
                            # Started work before finishing education
                            if start_year < latest_edu_year - 1:  # -1 for gap year
                                # This is actually common (people work during school)
                                # Only flag if difference is large
                                if latest_edu_year - start_year > 5:
                                    reasons.append(
                                        f"Started work in {start_year}, "
                                        f"but education ended in {latest_edu_year}"
                                    )
                        except (ValueError, TypeError):
                            pass
        
        # =====================================================================
        # CHECK 6: Skill Duration Exceeds Total Experience
        # =====================================================================
        total_months = yoe * 12
        
        for skill in skills:
            skill_duration = skill.get('duration_months', 0)
            
            if skill_duration > total_months + 12:  # +12 months tolerance
                reasons.append(
                    f"Skill '{skill.get('name')}' used for {skill_duration} months, "
                    f"but only {yoe:.1f} years total experience"
                )
                break  # One example is enough
        
        # =====================================================================
        # CHECK 7: Career Gap Anomalies
        # =====================================================================
        if len(career) >= 2:
            # Check for overlapping roles
            for i in range(len(career) - 1):
                role1 = career[i]
                role2 = career[i + 1]
                
                end1 = role1.get('end_date')
                start2 = role2.get('start_date')
                
                if end1 and start2:
                    try:
                        end1_dt = datetime.fromisoformat(end1[:10])
                        start2_dt = datetime.fromisoformat(start2[:10])
                        
                        # Started next role before previous ended (overlap)
                        if start2_dt < end1_dt:
                            days_overlap = (end1_dt - start2_dt).days
                            
                            # Small overlaps (<30 days) are normal
                            if days_overlap > 60:
                                reasons.append(
                                    f"Overlapping roles: {role2.get('company')} "
                                    f"started {days_overlap} days before "
                                    f"{role1.get('company')} ended"
                                )
                    except (ValueError, TypeError):
                        pass
        
        # =====================================================================
        # CHECK 8: Impossible Skill Combinations (Strict Mode)
        # =====================================================================
        if self.strict_mode:
            skill_names_lower = [s.get('name', '').lower() for s in skills]
            
            # Check for obviously incompatible skills
            # (e.g., expert in both ancient and bleeding-edge tech)
            ancient_tech = ['cobol', 'fortran', 'pascal', 'perl']
            modern_tech = ['react', 'vue', 'svelte', 'nextjs', 'llm', 'transformers']
            
            has_ancient = any(tech in ' '.join(skill_names_lower) for tech in ancient_tech)
            has_modern = any(tech in ' '.join(skill_names_lower) for tech in modern_tech)
            
            if has_ancient and has_modern and yoe < 15:
                reasons.append(
                    f"Unlikely skill combination (ancient + modern tech) "
                    f"with only {yoe:.1f} years experience"
                )
        
        # =====================================================================
        # Decision
        # =====================================================================
        is_honeypot = len(reasons) >= 3  # Need at least 3 red flags to avoid false positives
        
        return is_honeypot, reasons
    
    def filter_honeypots(
        self, 
        candidates: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Filter out honeypot candidates.
        
        Args:
            candidates: List of candidate dicts
        
        Returns:
            (valid_candidates, honeypots) tuple
            - valid_candidates: Candidates that passed checks
            - honeypots: Detected honeypot candidates with reasons
        """
        valid = []
        honeypots = []
        
        for candidate in candidates:
            is_honey, reasons = self.is_honeypot(candidate)
            
            if is_honey:
                candidate['honeypot_reasons'] = reasons
                honeypots.append(candidate)
            else:
                valid.append(candidate)
        
        return valid, honeypots
    
    def calculate_honeypot_rate(
        self, 
        top_candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate honeypot rate in top candidates.
        
        Used to check if we're below the 10% threshold.
        
        Args:
            top_candidates: List of top N candidates
        
        Returns:
            Dict with:
            - total: Total candidates checked
            - honeypots_detected: Number of honeypots
            - honeypot_rate: Percentage (0-100)
            - honeypot_list: List of honeypot candidate IDs
        """
        honeypot_count = 0
        honeypot_list = []
        
        for candidate in top_candidates:
            is_honey, reasons = self.is_honeypot(candidate)
            
            if is_honey:
                honeypot_count += 1
                cid = candidate.get('candidate_id') or candidate.get('profile', {}).get('candidate_id')
                honeypot_list.append({
                    'candidate_id': cid,
                    'reasons': reasons
                })
        
        total = len(top_candidates)
        rate = (honeypot_count / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'honeypots_detected': honeypot_count,
            'honeypot_rate': rate,
            'honeypot_list': honeypot_list,
            'passes_threshold': rate <= 10.0  # Must be <=10% to pass
        }