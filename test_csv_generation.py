#!/usr/bin/env python3
"""
Quick test of CSV generation with sample data
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.reasoning_generator import ReasoningGenerator, parse_jd_requirements
from app.services.csv_writer import write_submission_csv


def create_sample_candidates():
    """Create 100 sample candidates for testing"""
    candidates = []
    
    for i in range(1, 101):
        score = 100 - (i - 1) * 0.5  # Decreasing scores
        
        candidate = {
            'resume_id': f'CAND_{i:07d}',
            'rank': i,
            'overall_score': score,
            'all_scores': {
                'semantic_fit': score * 0.9,
                'career_growth': score * 0.8,
                'narrative_coherence': score * 0.85,
                'team_portfolio': score * 0.75,
                'artifact_complexity': score * 0.88,
            },
            'candidate_data': {
                'candidate_id': f'CAND_{i:07d}',
                'profile': {
                    'years_of_experience': 5 + (i % 10),
                    'current_title': 'Senior Engineer' if i <= 50 else 'Engineer',
                    'current_company': 'Tech Company',
                    'location': 'Pune' if i % 3 == 0 else 'Bangalore',
                },
                'career_history': [
                    {
                        'title': 'Senior Engineer',
                        'company': 'Tech Company',
                        'description': 'Built ML systems',
                    }
                ],
                'skills': [
                    {'name': 'Python', 'proficiency': 'advanced', 'duration_months': 60},
                    {'name': 'Machine Learning', 'proficiency': 'advanced', 'duration_months': 48},
                ],
                'redrob_signals': {
                    'last_active_date': '2026-06-01',
                    'recruiter_response_rate': 0.5 if i <= 50 else 0.2,
                    'notice_period_days': 30 if i <= 30 else 60,
                    'willing_to_relocate': i % 2 == 0,
                }
            }
        }
        
        candidates.append(candidate)
    
    return candidates


def main():
    print("Testing CSV Generation...")
    print("=" * 80)
    
    # Sample JD
    jd_text = """
    Senior AI Engineer
    
    Requirements:
    - 5-9 years experience
    - Python, embeddings, retrieval, vector databases
    - Location: Pune or Noida
    """
    
    jd_requirements = parse_jd_requirements(jd_text)
    print(f"\n1. Parsed JD requirements:")
    print(f"   Skills: {jd_requirements.get('skills', [])}")
    print(f"   Experience: {jd_requirements.get('min_experience', 0)}-{jd_requirements.get('max_experience', 0)} years")
    
    # Create sample candidates
    print(f"\n2. Creating 100 sample candidates...")
    candidates = create_sample_candidates()
    print(f"   Created {len(candidates)} candidates")
    
    # Generate reasoning
    print(f"\n3. Generating reasoning...")
    reasoning_gen = ReasoningGenerator(jd_requirements)
    
    for candidate in candidates:
        reasoning = reasoning_gen.generate(
            candidate=candidate['candidate_data'],
            rank=candidate['rank'],
            scores=candidate['all_scores']
        )
        candidate['reasoning'] = reasoning
    
    print(f"   Generated reasoning for {len(candidates)} candidates")
    
    # Show samples
    print(f"\n4. Sample reasoning:")
    for i in [0, 49, 99]:  # Rank 1, 50, 100
        c = candidates[i]
        print(f"\n   Rank {c['rank']} (Score: {c['overall_score']:.2f}):")
        print(f"   \"{c['reasoning']}\"")
    
    # Write CSV
    print(f"\n5. Writing CSV...")
    output_path = './test_submission.csv'
    
    try:
        result = write_submission_csv(candidates, output_path)
        
        print(f"   ✓ Success!")
        print(f"   Output: {result['output_path']}")
        print(f"   Rows: {result['rows_written']}")
        
        # Validation
        validation = result['validation']
        print(f"\n6. Validation:")
        print(f"   Valid: {validation['valid']}")
        print(f"   Errors: {len(validation['errors'])}")
        print(f"   Warnings: {len(validation['warnings'])}")
        
        if validation['warnings']:
            print(f"\n   Warnings:")
            for warning in validation['warnings']:
                print(f"     - {warning}")
        
        # Stats
        stats = validation['stats']
        print(f"\n7. Statistics:")
        print(f"   Total candidates: {stats['total_candidates']}")
        print(f"   Unique ranks: {stats['unique_ranks']}")
        print(f"   Unique candidate IDs: {stats['unique_candidate_ids']}")
        print(f"   Score range: {stats['min_score']:.2f} - {stats['max_score']:.2f}")
        print(f"   Empty reasoning: {stats['empty_reasoning_count']}")
        
        # Show CSV preview
        print(f"\n8. CSV Preview (first 5 rows):")
        with open(output_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i < 6:  # Header + 5 rows
                    print(f"   {line.rstrip()}")
        
        print(f"\n{'='*80}")
        print("✅ TEST PASSED!")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
