"""
Reasoning Generator for ATS Intelligence Engine

Generates non-templated, candidate-specific reasoning for submission CSV.
Avoids common pitfalls: empty strings, identical text, hallucinations.
"""

from typing import Dict, List, Any


class ReasoningGenerator:
    """
    Generates human-readable reasoning for why a candidate ranks where they do.
    
    Rules (from submission spec):
    - Must be specific to the candidate (not templated)
    - Must reference actual profile details (no hallucination)
    - Must be consistent with rank (don't praise rank 100)
    - Should be honest about weaknesses
    - Keep concise (200-500 chars recommended)
    """
    
    def __init__(self, jd_requirements: Dict[str, Any] = None):
        """
        Args:
            jd_requirements: Parsed JD with key requirements, skills, location, etc.
        """
        self.jd_requirements = jd_requirements or {}
    
    def generate(self, candidate: Dict[str, Any], rank: int, scores: Dict[str, float]) -> str:
        """
        Generate reasoning for a single candidate.
        
        Args:
            candidate: Full candidate profile dict
            rank: Candidate's rank (1-100)
            scores: All dimension scores dict
        
        Returns:
            Reasoning string (200-500 chars)
        """
        reasons = []
        concerns = []
        
        # Extract key data
        profile = candidate.get('profile', {})
        career = candidate.get('career_history', [])
        skills = candidate.get('skills', [])
        signals = candidate.get('redrob_signals', {})
        
        yoe = profile.get('years_of_experience', 0)
        current_title = profile.get('current_title', '')
        current_company = profile.get('current_company', '')
        location = profile.get('location', '')
        
        # 1. Experience level assessment
        if yoe >= 5:
            if 'Senior' in current_title or 'Lead' in current_title or 'Principal' in current_title:
                reasons.append(f"{yoe:.1f} years experience with senior-level title")
            else:
                reasons.append(f"{yoe:.1f} years experience")
        elif yoe >= 3:
            reasons.append(f"{yoe:.1f} years experience (mid-level)")
        else:
            concerns.append(f"Only {yoe:.1f} years experience (below typical 5-9 years)")
        
        # 2. Semantic fit assessment
        semantic_score = scores.get('semantic_fit', 0)
        if semantic_score > 85:
            reasons.append("strong semantic alignment with JD")
        elif semantic_score > 70:
            reasons.append("good semantic fit")
        elif semantic_score < 50:
            concerns.append("weak semantic alignment")
        
        # 3. Career trajectory
        career_score = scores.get('career_growth', 0)
        if career_score > 75:
            reasons.append("career shows upward trajectory")
        elif career_score > 60:
            reasons.append("steady career progression")
        elif career_score < 45:
            concerns.append("limited career progression signals")
        
        # 4. Skill relevance (check for AI/ML skills)
        skill_names = [s.get('name', '').lower() for s in skills]
        relevant_skills = []
        
        ml_skills = ['python', 'machine learning', 'nlp', 'embeddings', 'retrieval', 
                     'vector database', 'llm', 'transformers', 'pytorch', 'tensorflow']
        
        for skill in ml_skills:
            if any(skill in sn for sn in skill_names):
                # Find the actual skill object
                for s in skills:
                    if skill in s.get('name', '').lower():
                        prof = s.get('proficiency', '')
                        if prof in ['advanced', 'expert']:
                            relevant_skills.append(s.get('name'))
                        break
        
        if len(relevant_skills) >= 3:
            reasons.append(f"relevant skills: {', '.join(relevant_skills[:3])}")
        elif len(relevant_skills) >= 1:
            reasons.append(f"has {', '.join(relevant_skills[:2])}")
        
        # 5. Company context (product vs consulting)
        consulting_firms = ['tcs', 'infosys', 'wipro', 'accenture', 'cognizant', 'capgemini']
        
        if career:
            recent_companies = [role.get('company', '').lower() for role in career[:2]]
            if all(any(cf in comp for cf in consulting_firms) for comp in recent_companies if comp):
                concerns.append("primarily consulting firm background")
            
            # Check for product company experience
            product_indicators = ['google', 'amazon', 'microsoft', 'meta', 'apple', 'startup']
            has_product = any(
                any(pi in role.get('company', '').lower() for pi in product_indicators)
                for role in career
            )
            if has_product:
                reasons.append("product company experience")
        
        # 6. Activity/availability signals
        if signals:
            last_active = signals.get('last_active_date', '')
            response_rate = signals.get('recruiter_response_rate', 0)
            notice_days = signals.get('notice_period_days', 0)
            
            # Check if recently active
            # For now, just check if response rate is decent
            if response_rate > 0.5:
                reasons.append("active and responsive")
            elif response_rate < 0.2:
                concerns.append("low recruiter response rate")
            
            # Notice period
            if notice_days > 90:
                concerns.append(f"{notice_days} days notice period")
            elif notice_days <= 30:
                reasons.append("short notice period")
        
        # 7. Portfolio/breadth
        portfolio_score = scores.get('team_portfolio', 0)
        if portfolio_score > 75:
            reasons.append("broad skill portfolio (T-shaped)")
        
        # 8. Project complexity
        complexity_score = scores.get('artifact_complexity', 0)
        if complexity_score > 80:
            reasons.append("high-complexity project experience")
        
        # 9. Location considerations
        if location:
            preferred_locs = ['pune', 'noida', 'delhi', 'bangalore', 'hyderabad', 'mumbai']
            if any(loc in location.lower() for loc in preferred_locs):
                reasons.append(f"located in {location}")
            else:
                if signals.get('willing_to_relocate'):
                    reasons.append(f"{location}-based, willing to relocate")
                else:
                    concerns.append(f"{location}-based, not willing to relocate")
        
        # Build final reasoning based on rank tier
        if rank <= 10:
            # Top 10: Emphasize strengths
            reasoning = "; ".join(reasons[:4])
            if concerns and len(reasons) < 3:
                reasoning += f". Minor concern: {concerns[0]}"
        
        elif rank <= 50:
            # Top 50: Balanced
            reasoning = "; ".join(reasons[:3])
            if concerns:
                reasoning += f". Concern: {concerns[0]}"
        
        elif rank <= 75:
            # 51-75: Lead with concerns
            if concerns:
                reasoning = f"{concerns[0].capitalize()}"
                if reasons:
                    reasoning += f", but {reasons[0]}"
            else:
                reasoning = "; ".join(reasons[:2])
        
        else:
            # 76-100: Honest about weaknesses
            if len(concerns) >= 2:
                reasoning = f"{concerns[0].capitalize()}; {concerns[1]}"
            elif concerns:
                reasoning = concerns[0].capitalize()
                if reasons:
                    reasoning += f". Has {reasons[0]}"
            else:
                reasoning = "; ".join(reasons[:2]) + " (lower overall fit)"
        
        # Fallback if nothing generated
        if not reasoning:
            reasoning = f"Overall score {scores.get('overall_score', 0):.1f}; rank {rank} based on multi-dimensional analysis"
        
        # Truncate to reasonable length
        if len(reasoning) > 500:
            reasoning = reasoning[:497] + "..."
        
        return reasoning
    
    def generate_batch(self, candidates: List[Dict[str, Any]]) -> List[str]:
        """
        Generate reasoning for multiple candidates.
        
        Args:
            candidates: List of candidate dicts (must have 'rank' and 'scores')
        
        Returns:
            List of reasoning strings in same order
        """
        return [
            self.generate(
                candidate=c.get('candidate_data', {}),
                rank=c.get('rank', 0),
                scores=c.get('all_scores', {})
            )
            for c in candidates
        ]


def parse_jd_requirements(jd_text: str) -> Dict[str, Any]:
    """
    Extract key requirements from JD text.
    
    Args:
        jd_text: Job description text
    
    Returns:
        Dict with parsed requirements (skills, experience, location, etc.)
    """
    requirements = {
        'skills': [],
        'min_experience': 0,
        'max_experience': 100,
        'location': [],
        'disqualifiers': [],
    }
    
    # Simple keyword extraction (can be enhanced)
    jd_lower = jd_text.lower()
    
    # Experience range
    if '5-9 years' in jd_lower or '5–9 years' in jd_lower:
        requirements['min_experience'] = 5
        requirements['max_experience'] = 9
    elif 'years' in jd_lower:
        # Extract first number before 'years'
        import re
        matches = re.findall(r'(\d+)[+\-–]?\s*years', jd_lower)
        if matches:
            requirements['min_experience'] = int(matches[0])
    
    # Location
    if 'pune' in jd_lower:
        requirements['location'].append('pune')
    if 'noida' in jd_lower:
        requirements['location'].append('noida')
    if 'bangalore' in jd_lower:
        requirements['location'].append('bangalore')
    
    # Key skills (AI/ML focused)
    skill_keywords = [
        'python', 'embeddings', 'retrieval', 'vector database', 'llm',
        'machine learning', 'nlp', 'ranking', 'search', 'recommendation'
    ]
    
    for skill in skill_keywords:
        if skill in jd_lower:
            requirements['skills'].append(skill)
    
    # Disqualifiers
    if 'consulting' in jd_lower and 'not' in jd_lower:
        requirements['disqualifiers'].append('consulting_only')
    
    return requirements
