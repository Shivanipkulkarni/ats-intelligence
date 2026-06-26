#!/usr/bin/env python3
"""
Quick test for Tier 1 and Tier 2 implementation.
Creates synthetic resumes and tests the tiered pipeline.
"""

import sys
import os
import json
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.batch.pipeline import BatchPipeline


def create_test_resumes(count=1000):
    """Create synthetic test resumes."""
    resumes = []
    
    templates = [
        # High quality - senior engineers
        """Senior Software Engineer with 8 years of experience in distributed systems.
        Led team of 5 engineers building microservices architecture.
        Designed scalable ML pipeline processing 10M events/day using Python, Kafka, and Kubernetes.
        Expert in Python, Java, AWS, Docker, and system design.
        Strong leadership and mentoring skills.""",
        
        # Medium quality - mid-level
        """Software Engineer with 4 years experience in full-stack development.
        Built React frontend and Node.js backend for SaaS application.
        Implemented CI/CD pipeline using Jenkins and Docker.
        Proficient in JavaScript, Python, SQL, and cloud technologies.
        Team player with good communication skills.""",
        
        # Lower quality - junior
        """Junior Developer with 2 years experience.
        Developed web applications using PHP and MySQL.
        Fixed bugs and maintained legacy codebases.
        Learning Python and modern web frameworks.
        Eager to learn and grow.""",
        
        # Irrelevant - different field
        """Marketing Manager with 5 years experience.
        Led digital marketing campaigns and social media strategy.
        Managed team of 3 marketing specialists.
        Expert in SEO, Google Analytics, and content marketing.
        Strong analytical and communication skills.""",
        
        # High quality - ML engineer
        """Machine Learning Engineer with 6 years experience.
        Built and deployed deep learning models for computer vision.
        Designed scalable ML infrastructure on AWS using PyTorch and TensorFlow.
        Published 3 papers in top-tier conferences.
        Expert in Python, ML, distributed systems, and cloud architecture.""",
    ]
    
    for i in range(count):
        template_idx = i % len(templates)
        resume_text = templates[template_idx]
        
        resumes.append({
            "id": f"resume_{i:04d}",
            "resume_text": resume_text
        })
    
    return resumes


def test_tier_implementation():
    """Test Tier 1 and Tier 2 implementation."""
    
    print("="*80)
    print("QUICK TEST: Tier 1 & Tier 2 Implementation")
    print("="*80)
    
    # Create test data
    print("\n1. Creating test dataset...")
    test_count = 1000
    resumes = create_test_resumes(test_count)
    print(f"   ✓ Created {len(resumes)} synthetic resumes")
    
    # Create temp directory for resumes
    temp_dir = tempfile.mkdtemp(prefix="ats_test_")
    resume_dir = os.path.join(temp_dir, "resumes")
    os.makedirs(resume_dir)
    
    try:
        # Write resumes as JSONL
        jsonl_path = os.path.join(resume_dir, "resumes.jsonl")
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for resume in resumes:
                f.write(json.dumps(resume) + "\n")
        print(f"   ✓ Wrote resumes to {jsonl_path}")
        
        # Define job description
        job_description = """
        Senior Python Engineer with 5+ years experience.
        Must have strong experience in:
        - Distributed systems and microservices
        - Python, Docker, Kubernetes
        - Cloud platforms (AWS/GCP)
        - Team leadership and mentoring
        - Machine learning is a plus
        """
        
        print("\n2. Running tiered pipeline...")
        print(f"   Job Description: Senior Python Engineer")
        print(f"   Target: Top 50 candidates from {test_count} resumes")
        
        # Initialize pipeline
        pipeline = BatchPipeline(n_components=50, max_features=1000)
        
        # Run tiered pipeline
        result = pipeline.run_tiered(
            resume_dir=resume_dir,
            job_description=job_description,
            top_k=50,
            weights=None,
            num_workers=4,
            cache_dir=None,
            tier1_size=400,  # 40% of 1000
            tier2_size=100,  # 10% of 1000
        )
        
        print("\n" + "="*80)
        print("TEST RESULTS")
        print("="*80)
        
        # Verify results
        print(f"\n✓ Total resumes processed: {result['total_resumes_processed']}")
        print(f"✓ Time elapsed: {result['elapsed_seconds']:.2f}s")
        print(f"✓ Candidates returned: {len(result['candidates'])}")
        
        # Check tier stats
        if 'tier_stats' in result:
            ts = result['tier_stats']
            print(f"\n📊 Tier Statistics:")
            print(f"   Tier 1: {ts['tier1_elapsed']:.2f}s → {ts['tier1_cutoff']} candidates")
            print(f"   Tier 2: {ts['tier2_elapsed']:.2f}s → {ts['tier2_cutoff']} candidates")
            print(f"   Tier 3: {ts['tier3_elapsed']:.2f}s → {result['top_k']} candidates")
            print(f"\n   Tier 1 scores: {ts['tier1_top_score']:.2f} (top) | {ts['tier1_cutoff_score']:.2f} (cutoff)")
            print(f"   Tier 2 scores: {ts['tier2_top_score']:.2f} (top) | {ts['tier2_cutoff_score']:.2f} (cutoff)")
        
        # Show top 10 candidates
        print(f"\n🏆 Top 10 Candidates:")
        print(f"   {'Rank':<6} {'Resume ID':<15} {'Score':<8} {'Semantic':<10} {'Career':<8} {'Portfolio':<10}")
        print(f"   {'-'*70}")
        for i, candidate in enumerate(result['candidates'][:10], 1):
            scores = candidate['all_scores']
            print(f"   #{i:<5} {candidate['resume_id']:<15} "
                  f"{candidate['overall_score']:<8.2f} "
                  f"{scores['semantic_fit']:<10.2f} "
                  f"{scores['career_growth']:<8.2f} "
                  f"{scores['team_portfolio']:<10.2f}")
        
        # Verify tier filtering worked
        print(f"\n✅ Verification:")
        
        # Check that we got results
        assert len(result['candidates']) == 50, "Should return exactly 50 candidates"
        print(f"   ✓ Correct number of candidates returned (50)")
        
        # Check that scores are reasonable
        top_score = result['candidates'][0]['overall_score']
        bottom_score = result['candidates'][-1]['overall_score']
        assert top_score >= bottom_score, "Scores should be sorted descending (or equal)"
        assert 0 <= bottom_score <= 100, "Scores should be in 0-100 range"
        assert 0 <= top_score <= 100, "Scores should be in 0-100 range"
        print(f"   ✓ Scores are valid and sorted (range: {bottom_score:.2f} - {top_score:.2f})")
        
        # Check that all dimension scores exist
        required_scores = [
            'semantic_fit', 'career_growth', 'company_context', 'skill_currency',
            'resilience', 'narrative_coherence', 'team_portfolio', 
            'artifact_complexity', 'counterfactual', 'keyword_match'
        ]
        first_candidate = result['candidates'][0]
        for score_name in required_scores:
            assert score_name in first_candidate['all_scores'], f"Missing score: {score_name}"
        print(f"   ✓ All 10 dimension scores present")
        
        # Check tier stats exist
        assert 'tier_stats' in result, "Tier stats should be present"
        # Note: Dynamic sizing may adjust these if input is smaller
        assert ts['tier1_cutoff'] <= 400, f"Tier 1 cutoff should be <= 400, got {ts['tier1_cutoff']}"
        assert ts['tier2_cutoff'] <= 100, f"Tier 2 cutoff should be <= 100, got {ts['tier2_cutoff']}"
        print(f"   ✓ Tier filtering worked correctly (1000 → {ts['tier1_cutoff']} → {ts['tier2_cutoff']} → 50)")
        
        # Check bias comparison
        assert 'bias_comparison' in result, "Bias comparison should be present"
        print(f"   ✓ Bias comparison report generated")
        
        print(f"\n{'='*80}")
        print(f"🎉 ALL TESTS PASSED!")
        print(f"{'='*80}")
        print(f"\nTier 1 and Tier 2 are working correctly!")
        print(f"• Tier 1 (Semantic + Keyword) filtered {test_count} → {ts['tier1_cutoff']}")
        print(f"• Tier 2 (+ Medium Heuristics) filtered {ts['tier1_cutoff']} → {ts['tier2_cutoff']}")
        print(f"• Tier 3 (+ Deep Analysis) filtered {ts['tier2_cutoff']} → {result['top_k']}")
        print(f"\nTotal time: {result['elapsed_seconds']:.2f}s for {test_count} resumes")
        print(f"Speed: {int(test_count / result['elapsed_seconds'])} resumes/second")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED!")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
            print(f"\n🧹 Cleaned up temp directory: {temp_dir}")
        except:
            pass


if __name__ == "__main__":
    success = test_tier_implementation()
    sys.exit(0 if success else 1)
