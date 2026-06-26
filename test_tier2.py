#!/usr/bin/env python3
"""
Quick test to verify Tier 2 implementation is working correctly.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.career_trajectory.extractor import parse_roles_from_text
from app.services.narrative_coherence.scorer import compute_narrative_coherence
from app.services.team_portfolio.scorer import compute_team_portfolio
from app.services.artifact_complexity.scorer import compute_artifact_complexity


def test_tier2_scoring():
    """Test that Tier 2 dimensions compute correctly."""
    
    sample_resume = """
    Senior Software Engineer at TechCorp (2020-2023)
    - Led team of 5 engineers building distributed microservices architecture
    - Designed and implemented scalable ML pipeline processing 10M events/day
    - Mentored junior engineers and conducted code reviews
    
    Software Engineer at StartupXYZ (2018-2020)
    - Built React frontend and Node.js backend for SaaS product
    - Implemented CI/CD pipeline using Jenkins and Docker
    - Contributed to system design and architecture decisions
    
    Junior Developer at WebAgency (2016-2018)
    - Developed WordPress websites and custom PHP applications
    - Fixed bugs and maintained legacy codebases
    """
    
    print("Testing Tier 2 dimensions...")
    print("=" * 80)
    
    # Parse roles
    roles = parse_roles_from_text(sample_resume)
    print(f"\nParsed {len(roles)} roles from resume")
    
    # Test narrative coherence
    print("\n1. Narrative Coherence:")
    narrative = compute_narrative_coherence(sample_resume, roles)
    print(f"   Score: {narrative['narrative_coherence_score']:.2f}")
    print(f"   Confidence: {narrative['confidence']}")
    print(f"   Reasons: {narrative['reasons'][:2]}")
    
    # Test team portfolio
    print("\n2. Team Portfolio:")
    portfolio = compute_team_portfolio(sample_resume, roles)
    print(f"   Score: {portfolio['team_portfolio_score']:.2f}")
    print(f"   Confidence: {portfolio['confidence']}")
    print(f"   Domains: {portfolio.get('domains_covered', [])}")
    print(f"   Reasons: {portfolio['reasons'][:2]}")
    
    # Test artifact complexity
    print("\n3. Artifact Complexity:")
    artifact = compute_artifact_complexity(sample_resume, roles)
    print(f"   Score: {artifact['artifact_complexity_score']:.2f}")
    print(f"   Confidence: {artifact['confidence']}")
    print(f"   High complexity signals: {artifact.get('high_complexity_signals', 0)}")
    print(f"   Reasons: {artifact['reasons'][:2]}")
    
    # Calculate Tier 2 score
    print("\n" + "=" * 80)
    semantic_fit = 85.0  # Mock value
    keyword_match = 75.0  # Mock value
    
    tier2_score = (
        semantic_fit * 0.35 +
        keyword_match * 0.15 +
        narrative['narrative_coherence_score'] * 0.20 +
        portfolio['team_portfolio_score'] * 0.15 +
        artifact['artifact_complexity_score'] * 0.15
    )
    
    print(f"\nTier 2 Combined Score: {tier2_score:.2f}")
    print(f"  Semantic Fit (35%):     {semantic_fit:.2f} → {semantic_fit * 0.35:.2f}")
    print(f"  Keyword Match (15%):    {keyword_match:.2f} → {keyword_match * 0.15:.2f}")
    print(f"  Narrative (20%):        {narrative['narrative_coherence_score']:.2f} → {narrative['narrative_coherence_score'] * 0.20:.2f}")
    print(f"  Portfolio (15%):        {portfolio['team_portfolio_score']:.2f} → {portfolio['team_portfolio_score'] * 0.15:.2f}")
    print(f"  Artifact (15%):         {artifact['artifact_complexity_score']:.2f} → {artifact['artifact_complexity_score'] * 0.15:.2f}")
    
    print("\n✓ Tier 2 scoring test complete!")
    return tier2_score


if __name__ == "__main__":
    test_tier2_scoring()
