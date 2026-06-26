"""
Behavioral Signals Scorer

Analyzes candidate availability and engagement signals from redrob_signals data.
Down-weights candidates who are not actually available or engaged.

Key signals:
- Last active date (inactive candidates likely not available)
- Recruiter response rate (low = not looking)
- Notice period (high = difficult to hire)
- Profile completeness
- GitHub activity
- Willing to relocate (for location mismatch)
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional


class BehavioralSignalsScorer:
    """
    Scores candidates based on behavioral/engagement signals.
    
    Returns a multiplier (0.0 to 1.0) that adjusts the base score.
    A score of 1.0 means no penalty, <1.0 means candidate is penalized.
    """
    
    def __init__(self, jd_requirements: Optional[Dict[str, Any]] = None):
        """
        Args:
            jd_requirements: Parsed JD with location preferences, notice period limits, etc.
        """
        self.jd_requirements = jd_requirements or {}
        self.preferred_locations = self.jd_requirements.get('location', ['pune', 'noida', 'bangalore'])
        self.max_notice_days = self.jd_requirements.get('max_notice_days', 60)
    
    def compute_behavioral_score(
        self, 
        redrob_signals: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute behavioral availability score.
        
        Args:
            redrob_signals: The redrob_signals dict from candidate JSON
            profile: The profile dict (for location)
        
        Returns:
            Dict with:
                - behavioral_multiplier: float (0.0-1.0)
                - signals_breakdown: dict of individual signal scores
                - flags: list of warning flags
        """
        multiplier = 1.0
        breakdown = {}
        flags = []
        
        # 1. Last Active Date (CRITICAL - 6+ months inactive = likely not available)
        last_active_str = redrob_signals.get('last_active_date', '')
        if last_active_str:
            try:
                last_active = self._parse_date(last_active_str)
                days_inactive = (datetime.now() - last_active).days
                
                if days_inactive > 180:  # 6+ months
                    activity_penalty = 0.3  # 70% penalty
                    flags.append(f"Inactive for {days_inactive} days (6+ months)")
                elif days_inactive > 90:  # 3-6 months
                    activity_penalty = 0.6  # 40% penalty
                    flags.append(f"Inactive for {days_inactive} days (3+ months)")
                elif days_inactive > 60:  # 2-3 months
                    activity_penalty = 0.8  # 20% penalty
                    flags.append(f"Inactive for {days_inactive} days (2+ months)")
                elif days_inactive > 30:
                    activity_penalty = 0.9  # 10% penalty
                else:
                    activity_penalty = 1.0  # No penalty - active
                
                multiplier *= activity_penalty
                breakdown['activity_penalty'] = activity_penalty
                breakdown['days_inactive'] = days_inactive
                
            except Exception:
                # Can't parse date, assume moderate penalty
                multiplier *= 0.85
                flags.append("Unable to parse last_active_date")
        else:
            # No last active data
            multiplier *= 0.85
            flags.append("No last_active_date available")
        
        # 2. Recruiter Response Rate (LOW = not actually looking)
        response_rate = redrob_signals.get('recruiter_response_rate', -1)
        
        if response_rate >= 0:  # Valid data
            if response_rate < 0.10:  # <10% response rate
                response_penalty = 0.5  # 50% penalty - likely not looking
                flags.append(f"Very low response rate ({response_rate:.0%})")
            elif response_rate < 0.25:  # 10-25%
                response_penalty = 0.75  # 25% penalty
                flags.append(f"Low response rate ({response_rate:.0%})")
            elif response_rate < 0.40:  # 25-40%
                response_penalty = 0.9  # 10% penalty
            else:  # 40%+
                response_penalty = 1.0  # No penalty - engaged
            
            multiplier *= response_penalty
            breakdown['response_penalty'] = response_penalty
            breakdown['response_rate'] = response_rate
        
        # 3. Notice Period (HIGH = difficult to hire quickly)
        notice_days = redrob_signals.get('notice_period_days', 0)
        
        if notice_days > 120:  # 4+ months
            notice_penalty = 0.6  # 40% penalty
            flags.append(f"Very long notice period ({notice_days} days)")
        elif notice_days > 90:  # 3+ months
            notice_penalty = 0.75  # 25% penalty
            flags.append(f"Long notice period ({notice_days} days)")
        elif notice_days > self.max_notice_days:  # Over JD preference
            notice_penalty = 0.85  # 15% penalty
            flags.append(f"Notice period ({notice_days} days) exceeds preference")
        elif notice_days <= 30:  # Short notice
            notice_penalty = 1.0  # No penalty - can start quickly
        else:
            notice_penalty = 0.95  # Small 5% penalty
        
        multiplier *= notice_penalty
        breakdown['notice_penalty'] = notice_penalty
        breakdown['notice_days'] = notice_days
        
        # 4. Open to Work Flag
        open_to_work = redrob_signals.get('open_to_work_flag', False)
        
        if not open_to_work:
            # Not marked as open to work - moderate penalty
            multiplier *= 0.90
            flags.append("Not marked as open to work")
            breakdown['open_to_work'] = False
        else:
            breakdown['open_to_work'] = True
        
        # 5. Profile Completeness (LOW = less serious candidate)
        completeness = redrob_signals.get('profile_completeness_score', 0)
        
        if completeness < 50:  # Very incomplete
            completeness_penalty = 0.85
            flags.append(f"Low profile completeness ({completeness:.0f}%)")
        elif completeness < 70:
            completeness_penalty = 0.93
        else:
            completeness_penalty = 1.0
        
        multiplier *= completeness_penalty
        breakdown['completeness_penalty'] = completeness_penalty
        breakdown['profile_completeness'] = completeness
        
        # 6. GitHub Activity (for AI/ML roles)
        github_score = redrob_signals.get('github_activity_score', -1)
        
        if github_score == 0:
            # No GitHub activity for AI role - small penalty
            multiplier *= 0.95
            flags.append("No GitHub activity")
            breakdown['github_active'] = False
        elif github_score > 0:
            breakdown['github_active'] = True
            breakdown['github_score'] = github_score
        
        # 7. Location & Relocation Willingness
        location = profile.get('location', '').lower()
        willing_to_relocate = redrob_signals.get('willing_to_relocate', False)
        
        location_match = any(
            pref_loc in location 
            for pref_loc in self.preferred_locations
        )
        
        if not location_match and not willing_to_relocate:
            # Wrong location and won't relocate
            multiplier *= 0.75  # 25% penalty
            flags.append(f"Location mismatch ({profile.get('location', 'Unknown')}), not willing to relocate")
            breakdown['location_match'] = False
        elif not location_match and willing_to_relocate:
            # Wrong location but willing to relocate
            multiplier *= 0.90  # 10% penalty
            breakdown['location_match'] = False
            breakdown['willing_to_relocate'] = True
        else:
            breakdown['location_match'] = True
        
        # 8. Interview/Offer Metrics (if available)
        interview_rate = redrob_signals.get('interview_completion_rate', -1)
        offer_rate = redrob_signals.get('offer_acceptance_rate', -1)
        
        # Very low interview completion = flaky candidate
        if interview_rate >= 0 and interview_rate < 0.3:
            multiplier *= 0.90
            flags.append(f"Low interview completion rate ({interview_rate:.0%})")
            breakdown['interview_completion_low'] = True
        
        # Cap minimum multiplier at 0.2 (don't completely eliminate anyone)
        multiplier = max(0.2, multiplier)
        
        return {
            'behavioral_multiplier': round(multiplier, 4),
            'signals_breakdown': breakdown,
            'flags': flags,
            'penalty_total': round((1.0 - multiplier) * 100, 1)  # % penalty
        }
    
    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse date string in various formats.
        
        Supports:
        - ISO 8601: 2026-05-20
        - Common formats: 05/20/2026, 20-05-2026
        """
        formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d-%m-%Y',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Fallback: assume recent if can't parse
        raise ValueError(f"Unable to parse date: {date_str}")


def compute_behavioral_signals(
    candidate_data: Dict[str, Any],
    jd_requirements: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function to compute behavioral signals for a candidate.
    
    Args:
        candidate_data: Full candidate dict with profile and redrob_signals
        jd_requirements: Parsed JD requirements
    
    Returns:
        Dict with behavioral_multiplier and breakdown
    """
    scorer = BehavioralSignalsScorer(jd_requirements)
    
    redrob_signals = candidate_data.get('redrob_signals', {})
    profile = candidate_data.get('profile', {})
    
    return scorer.compute_behavioral_score(redrob_signals, profile)
