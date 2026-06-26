#!/usr/bin/env python3
"""
Quick test for Tier 1 and Tier 2 implementation.
Creates sample resumes, runs tiered filtering, and validates the pipeline.
"""

import sys
import os
import json
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.batch.pipeline import BatchPipeline


def create_test_resumes(num_resumes=1000):
    """Create sample resume data for testing."""
    
    # High-quality resume templates
    high_quality_templates = [
        """Senior Software Engineer at TechCorp (2020-2023)
- Led team of 5 engineers building distributed microservices architecture on AWS
- Designed and implemented scalable ML pipeline processing 10M events/day using Python and Spark
- Mentored junior engineers and conducted code reviews, improving team velocity by 40%
- Technologies: Python, Go, Kubernetes, Docker, PostgreSQL, Redis, Kafka

Software Engineer at StartupXYZ (2018-2020)
- Built React frontend and Node.js backend for SaaS product serving 50K users
- Implemented CI/CD pipeline using Jenkins and Docker, reducing deployment time by 60%
- Designed RESTful APIs and GraphQL endpoints for mobile and web clients
- Technologies: JavaScript, React, Node.js, MongoDB, AWS, Docker

Junior Developer at WebAgency (2016-2018)
- Developed responsive websites using HTML, CSS, JavaScript
- Maintained legacy PHP applications and fixed production bugs
- Collaborated with designers to implement pixel-perfect UIs
""",
        """Principal Engineer at BigTech Inc (2021-2023)
- Architected distributed systems handling 1B+ requests/day with 99.99% uptime
- Led cross-functional teams in designing and implementing microservices migration
- Established best practices for system design, code review, and testing
- Technologies: Java, Spring Boot, Kubernetes, Cassandra, Kafka, AWS

Senior Engineer at FinTech Startup (2018-2021)
- Built real-time payment processing system handling $100M+ daily transactions
- Implemented fraud detection using machine learning models (TensorFlow, scikit-learn)
- Optimized database queries reducing latency by 70%
- Technologies: Python, Django, PostgreSQL, Redis, Celery, Docker

Software Engineer at ConsultingCo (2015-2018)
- Developed enterprise web applications for Fortune 500 clients
- Integrated third-party APIs and payment gateways
- Participated in Agile ceremonies and sprint planning
""",
    ]
    
    # Medium-quality resume templates
    medium_quality_templates = [
        """Software Developer at MediumCorp (2019-2023)
- Developed web applications using Python and JavaScript
- Fixed bugs and added new features to existing codebase
- Worked with databases and APIs
- Technologies: Python, JavaScript, MySQL, REST APIs

Junior Developer at SmallCompany (2017-2019)
- Created websites and web applications
- Maintained existing code and fixed issues
- Worked in team environment
""",
        """Web Developer (2018-2023)
- Built websites using HTML, CSS, JavaScript
- Worked with WordPress and PHP
- Created responsive designs
- Technologies: HTML, CSS, JavaScript, PHP, MySQL

Developer at StartupCo (2016-2018)
- Developed features for web application
- Fixed bugs and tested code
- Collaborated with team members
""",
    ]
    
    # Low-quality resume templates
    low_quality_templates = [
        """Developer (2020-2023)
- Coded stuff
- Fixed bugs
- Worked on projects

Junior Developer (2018-2020)
- Learned programming
- Wrote some code
- Helped team
""",
        """Software Engineer
- Experience with programming
- Worked on various projects
- Team player
- Good communication skills
""",
    ]
    
    resumes = []
    
    # Generate mix of high, medium, low quality resumes
    for i in range(num_resumes):
        if i < num_resumes * 0.1:  # 10% high quality
            template = high_quality_templates[i % len(high_quality_templates)]
        elif i < num_resumes * 0.4:  # 30% medium quality
            template = medium_quality_templates[i % len(medium_quality_templates)]
        else:  # 60% low quality
            template = low_quality_templates[i % len(low_quality_templates)]
        
        resumes.append({
            "id": f"resume_{i:04d}",
            "resume_text": template
        })
    
    return resumes


def test_tiered_pipeline():
    """Test the tiered filtering pipeline."""
    
    print("=" * 80)
    print("TIER 1 & 2 IMPLEMENTATION TEST")
    print("=" * 80)
    
    # Create test data
    print("\n1. Creating test data...")
    num_resumes = 1000
    resumes = create_test_resumes(num_resumes)
    print(f"   ✓ Created {num_resumes} test resumes")
    
    # Create temporary directory for resumes
    temp_dir = tempfile.mkdtemp()
    resume_file = os.path.join(temp_dir, "resumes.jsonl")
    
    try:
        # Write resumes to JSONL file
        with open(resume_file, 'w', encoding='utf-8') as f:
            for resume in resumes:
                f.write(json.dumps(resume) + '\n')
        print(f"   ✓ Written to {resume_file}")
        
        # Define job description
        job_description = """
        Senior Software Engineer
        
        We are looking for an experienced software engineer with:
        - 5+ years of Python development experience
        - Strong background in distributed systems and microservices
        - Experience with AWS, Docker, Kubernetes
        - Machine learning experience is a plus
        - Leadership and mentoring experience
        - Strong system design skills
        
        Responsibilities:
        - Design and implement scalable backend services
        - Lead technical projects and mentor junior engineers
        - Collaborate with cross-functional teams
        - Participate in code reviews and architecture discussions
        """
        
        print("\n2. Initializing tiered pipeline...")
        pipeline = BatchPipeline(n_components=50, max_features=5000)
        print("   ✓ Pipeline initialized")
        
        # Run tiered filtering
        print("\n3. Running tiered filtering (Tier 1 + Tier 2)...")
        print("-" * 80)
        
        result = pipeline.run_tiered(
            resume_dir=temp_dir,
            job_description=job_description,
            top_k=10,
            num_workers=4,  # Use 4 workers for testing
            tier1_size=100,  # Filter to 100 candidates
            tier2_size=20,   # Filter to 20 candidates
        )
        
        print("-" * 80)
        
        # Validate results
        print("\n4. Validating results...")
        print("=" * 80)
        
        # Check tier stats
        if 'tier_stats' in result:
            ts = result['tier_stats']
            print(f"\n✓ Tier Statistics:")
            print(f"  Tier 1 Time:    {ts['tier1_elapsed']:.2f}s")
            print(f"  Tier 2 Time:    {ts['tier2_elapsed']:.2f}s")
            print(f"  Tier 3 Time:    {ts['tier3_elapsed']:.2f}s")
            print(f"  Total Time:     {result['elapsed_seconds']:.2f}s")
            print(f"  Tier 1 Cutoff:  {ts['tier1_cutoff']} candidates")
            print(f"  Tier 2 Cutoff:  {ts['tier2_cutoff']} candidates")
            
            # Validate tier cutoffs
            assert ts['tier1_cutoff'] == 100, f"Expected tier1_cutoff=100, got {ts['tier1_cutoff']}"
            assert ts['tier2_cutoff'] == 20, f"Expected tier2_cutoff=20, got {ts['tier2_cutoff']}"
            print("\n✓ Tier cutoffs are correct")
            
            # Validate scores exist
            if 'tier1_top_score' in ts:
                print(f"\n✓ Tier 1 Scores:")
                print(f"  Top score:    {ts['tier1_top_score']:.2f}")
                print(f"  Cutoff score: {ts['tier1_cutoff_score']:.2f}")
                assert ts['tier1_top_score'] >= ts['tier1_cutoff_score'], "Top score should be >= cutoff score"
            
            if 'tier2_top_score' in ts:
                print(f"\n✓ Tier 2 Scores:")
                print(f"  Top score:    {ts['tier2_top_score']:.2f}")
                print(f"  Cutoff score: {ts['tier2_cutoff_score']:.2f}")
                assert ts['tier2_top_score'] >= ts['tier2_cutoff_score'], "Top score should be >= cutoff score"
        else:
            print("⚠ Warning: tier_stats not found in result")
        
        # Check candidates
        print(f"\n✓ Top {len(result['candidates'])} Candidates:")
        print("-" * 80)
        for i, candidate in enumerate(result['candidates'][:5], 1):
            scores = candidate['all_scores']
            print(f"\n#{i} {candidate['resume_id']} (Overall: {candidate['overall_score']:.2f})")
            print(f"   Semantic:   {scores['semantic_fit']:.2f}")
            print(f"   Keyword:    {scores['keyword_match']:.2f}")
            print(f"   Narrative:  {scores['narrative_coherence']:.2f}")
            print(f"   Portfolio:  {scores['team_portfolio']:.2f}")
            print(f"   Artifact:   {scores['artifact_complexity']:.2f}")
            print(f"   Career:     {scores['career_growth']:.2f}")
            
            # Validate scores are in valid range
            for score_name, score_value in scores.items():
                assert 0 <= score_value <= 100, f"Score {score_name}={score_value} out of range [0,100]"
        
        # Check that we got expected number of candidates
        assert len(result['candidates']) == 10, f"Expected 10 candidates, got {len(result['candidates'])}"
        print("\n✓ Correct number of candidates returned")
        
        # Check overall scores are properly sorted
        scores = [c['overall_score'] for c in result['candidates']]
        assert scores == sorted(scores, reverse=True), "Candidates not properly sorted by overall score"
        print("✓ Candidates properly sorted by overall score")
        
        # Validate bias comparison
        if result.get('bias_comparison'):
            bc = result['bias_comparison']['summary']
            print(f"\n✓ Bias Comparison:")
            print(f"  Overlap:    {bc['overlap_count']}/{len(result['candidates'])} ({bc['overlap_pct']}%)")
            print(f"  LSA only:   {bc['lsa_only_count']}")
            print(f"  Keyword only: {bc['keyword_only_count']}")
        
        print("\n" + "=" * 80)
        print("✓ ALL TESTS PASSED!")
        print("=" * 80)
        print(f"\nSummary:")
        print(f"  • Processed {num_resumes} resumes")
        print(f"  • Tier 1: {num_resumes} → {ts['tier1_cutoff']} candidates")
        print(f"  • Tier 2: {ts['tier1_cutoff']} → {ts['tier2_cutoff']} candidates")
        print(f"  • Tier 3: {ts['tier2_cutoff']} → {len(result['candidates'])} candidates")
        print(f"  • Total time: {result['elapsed_seconds']:.2f}s")
        print(f"  • Throughput: {int(num_resumes / result['elapsed_seconds'])} resumes/sec")
        
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    success = test_tiered_pipeline()
    sys.exit(0 if success else 1)
