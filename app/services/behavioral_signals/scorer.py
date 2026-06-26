"""
Behavioral Signals Scorer

Evaluates candidate availability and engagement based on redrob_signals data.

Key insight from JD:
"A perfect-on-paper candidate who hasn't logged in for 6 months and has a 
5% recruiter response rate is, for hiring purposes, not actually available."

This module down-weights candidates with poor behavioral signals.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional


def compute_behavioral_score(
    redrob_signals: Dict[str, Any],
    jd_requirements: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Compute behavioral score multiplier (0.0 - 1.0).
    
    This is a MULTIPLIER applied to the base score:
    - 1.0 = No penalty (good signals)
    - 0.5 = 50% penalty (moderate concerns)
    - 0.3 = 70% penalty (severe concerns)
    
    Args:
        redrob_signals: Dict with behavioral data from candidate profile
        jd_requirements: Optional JD requirements (location, notice period, etc.)
    
    Returns:
        Dict with:
        - behavioral_multiplier (float): 0.0 - 1.0 multiplier
        - penalties (list): List of penalty descriptions
        - boosts (list): List of boost descriptions
    """
    multiplier = 1.0
    penalties = []
    boosts = []
    
    # Default JD requirements if not provided
    if jd_requirements is None:
        jd_requirements = {}
    
    # =========================================================================
    # 1. LAST ACTIVE DATE (CRITICAL - Highest weight)
    # =========================================================================
    last_active = redrob_signals.get('last_active_date')
    if last_active:
        try:
            last_active_dt = datetime.fromisoformat(last_active.replace('Z', '+00:00'))
            days_inactive = (datetime.now(last_active_dt.tzinfo) - last_active_dt).days
            
            if days_inactive > 180:  # 6+ months
                multiplier *= 0.3
                penalties.append(f"Inactive for {days_inactive} days (6+ months)")
            elif days_inactive > 90:  # 3-6 months
                multiplier *= 0.6
                penalties.append(f"Inactive for {days_inactive} days (3-6 months)")
            elif days_inactive > 30:  # 1-3 months
                multiplier *= 0.85
                penalties.append(f"Inactive for {days_inactive} days")
            elif days_inactive <= 7:  # Very recent
                multiplier *= 1.05  # Small boost
                boosts.append(f"Very active (last seen {days_inactive} days ago)")
        except (ValueError, TypeError) as e:
            # Invalid date format - apply moderate penalty
            multiplier *= 0.7
            penalties.append("Unable to parse last_active_date")
    else:
        # Missing last_active_date - assume moderate concern
        multiplier *= 0.75
        penalties.append("Missing last_active_date")
    
    # =========================================================================
    # 2. RECRUITER RESPONSE RATE (High weight)
    # =========================================================================
    response_rate = redrob_signals.get('recruiter_response_rate', 0)
    
    if response_rate < 0.10:  # <10% response
        multiplier *= 0.5
        penalties.append(f"Very low response rate ({response_rate:.0%})")
    elif response_rate < 0.25:  # <25% response
        multiplier *= 0.75
        penalties.append(f"Low response rate ({response_rate:.0%})")
    elif response_rate >= 0.50:  # >=50% response
        multiplier *= 1.05
        boosts.append(f"Good response rate ({response_rate:.0%})")
    
    # =========================================================================
    # 3. OPEN TO WORK FLAG
    # =========================================================================
    open_to_work = redrob_signals.get('open_to_work_flag', True)
    
    if not open_to_work:
        multiplier *= 0.6
        penalties.append("Not marked as open to work")
    else:
        boosts.append("Open to work")
    
    # =========================================================================
    # 4. NOTICE PERIOD (JD prefers <30 days, can buy out up to 30 days)
    # =========================================================================
    notice_days = redrob_signals.get('notice_period_days', 60)
    
    if notice_days > 90:  # >90 days
        multiplier *= 0.7
        penalties.append(f"{notice_days} days notice (long)")
    elif notice_days > 60:  # 60-90 days
        multiplier *= 0.85
        penalties.append(f"{notice_days} days notice")
    elif notice_days <= 30:  # <=30 days (preferred)
        multiplier *= 1.02
        boosts.append(f"Short notice period ({notice_days} days)")
    
    # =========================================================================
    # 5. LOCATION & RELOCATION
    # =========================================================================
    willing_to_relocate = redrob_signals.get('willing_to_relocate', False)
    
    # Note: Actual location check should use profile.location, not signals
    # This is handled in reasoning generation
    if willing_to_relocate:
        boosts.append("Willing to relocate")
    
    # =========================================================================
    # 6. PROFILE COMPLETENESS
    # =========================================================================
    completeness = redrob_signals.get('profile_completeness_score', 0)
    
    if completeness < 50:
        multiplier *= 0.9
        penalties.append(f"Low profile completeness ({completeness:.0f}%)")
    elif completeness >= 85:
        boosts.append(f"High profile completeness ({completeness:.0f}%)")
    
    # =========================================================================
    # 7. VERIFICATION STATUS
    # =========================================================================
    email_verified = redrob_signals.get('verified_email', False)
    phone_verified = redrob_signals.get('verified_phone', False)
    
    if not email_verified or not phone_verified:
        multiplier *= 0.95
        penalties.append("Incomplete verification")
    
    # =========================================================================
    # 8. INTERVIEW & OFFER RATES (Secondary signals)
    # =========================================================================
    interview_rate = redrob_signals.get('interview_completion_rate', -1)
    offer_rate = redrob_signals.get('offer_acceptance_rate', -1)
    
    if interview_rate >= 0 and interview_rate < 0.3:
        multiplier *= 0.95
        penalties.append(f"Low interview completion ({interview_rate:.0%})")
    
    if offer_rate >= 0 and offer_rate < 0.3:
        multiplier *= 0.95
        penalties.append(f"Low offer acceptance ({offer_rate:.0%})")
    
    # =========================================================================
    # 9. ENGAGEMENT SIGNALS
    # =========================================================================
    github_score = redrob_signals.get('github_activity_score', -1)
    
    if github_score >= 50:
        multiplier *= 1.03
        boosts.append(f"Active GitHub ({github_score:.0f})")
    
    applications_30d = redrob_signals.get('applications_submitted_30d', 0)
    if applications_30d > 10:
        boosts.append(f"Actively applying ({applications_30d} apps in 30d)")
    
    # =========================================================================
    # Cap multiplier between 0.1 and 1.1
    # =========================================================================
    multiplier = max(0.1, min(1.1, multiplier))
    
    return {
        'behavioral_multiplier': multiplier,
        'penalties': penalties,
        'boosts': boosts,
        'signals_used': {
            'last_active_date': last_active,
            'recruiter_response_rate': response_rate,
            'open_to_work_flag': open_to_work,
            'notice_period_days': notice_days,
            'profile_completeness_score': completeness,
        }
    }


def apply_behavioral_multiplier(
    base_score: float,
    redrob_signals: Dict[str, Any],
    jd_requirements: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Apply behavioral multiplier to a base score.
    
    Args:
        base_score: Base score from multi-dimensional analysis (0-100)
        redrob_signals: Behavioral signals dict
        jd_requirements: Optional JD requirements
    
    Returns:
        Dict with:
        - final_score: Adjusted score after behavioral multiplier
        - behavioral_multiplier: The multiplier applied
        - penalties: List of penalties
        - boosts: List of boosts
    """
    behavioral_result = compute_behavioral_score(redrob_signals, jd_requirements)
    
    final_score = base_score * behavioral_result['behavioral_multiplier']
    
    return {
        'final_score': final_score,
        'base_score': base_score,
        'behavioral_multiplier': behavioral_result['behavioral_multiplier'],
        'penalties': behavioral_result['penalties'],
        'boosts': behavioral_result['boosts'],
    }
