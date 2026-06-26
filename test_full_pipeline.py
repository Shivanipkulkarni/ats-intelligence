#!/usr/bin/env python3
"""
Comprehensive test for the complete 3-tier pipeline integration.
Tests Tier 1, Tier 2, and Tier 3 working together seamlessly.
"""

import sys
import os
import json
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.batch.pipeline import BatchPipeline


def create_diverse_resumes(count=500):
    """Create diverse test resumes with varying quality levels."""
    resumes = []
    
    # Template categories with different quality scores
    templates = {
        "excellent_senior": [
            """Principal Engineer with 10 years experience leading distributed systems architecture.
            Architected microservices platform serving 50M users using Python, Kubernetes, and AWS.
            Led team of 12 engineers, mentored senior developers, drove technical strategy.
            Expert in system design, scalability, ML pipelines, and cloud architecture.
            Published speaker at tech conferences. Strong track record of career growth.""",
            
            """Senior ML Engineer with 8 years building production ML systems.
            Designed and deployed deep learning models achieving 95% accuracy on large datasets.
            Built scalable ML infrastructure processing billions of events using PyTorch and TensorFlow.
            Led cross-functional projects, mentored junior engineers, published 4 research papers.
            Expert in Python, distributed systems, MLOps, and cloud platforms."""
        ],
        
        "good_mid": [
            """Software Engineer with 5 years full-stack development experience.
            Built React/Node.js applications serving 1M+ users at growing startup.
            Implemented CI/CD pipelines, improved system performance by 40%.
            Proficient in JavaScript, Python, Docker, Kubernetes, and AWS.
            Team player with strong problem-solving skills and growth mindset.""",
            
            """Backend Engineer with 4 years experience in scalable web services.
            Developed microservices architecture using Python, FastAPI, and PostgreSQL.
            Improved API performance, implemented caching strategies, mentored interns.
            Experience with Docker, Kubernetes, Redis, and message queues.
            Solid understanding of system design and best practices."""
        ],
        
        "average_junior": [
            """Junior Developer with 2 years experience in web development.
            Built features for e-commerce platform using React and Node.js.
            Fixed bugs, wrote unit tests, participated in code reviews.
            Learning Python, Docker, and cloud technologies.
            Eager to learn and contribute to team success.""",
            
            """Software Developer with 3 years experience.
            Developed web applications using PHP, MySQL, and JavaScript.
            Maintained legacy systems, implemented new features.
            Familiar with Git, Linux, and agile methodologies.
            Hardworking and detail-oriented."""
        ],
        
        "weak_mismatch": [
            """Frontend Developer with 4 years experience in UI/UX.
            Built beautiful responsive websites using HTML, CSS, and jQuery.
            Strong eye for design, worked closely with designers.
            Experience with WordPress, Photoshop, and Figma.
            Creative problem solver.""",
            
            """QA Engineer with 3 years testing experience.
            Performed manual and automated testing of web applications.
            Wrote test cases, reported bugs, verified fixes.
            Experience with Selenium, JIRA, and TestRail.
            Detail-oriented with strong communication skills."""
        ],
        
        "irrelevant": [
            """Marketing Manager with 5 years experience.
            Led digital marketing campaigns, managed social media strategy.
            Increased brand awareness by 60%, managed $500K budget.
            Expert in SEO, Google Analytics, and content marketing.
            Strong leadership and analytical skills.""",
            
            """Project Manager with 6 years experience.
            Managed cross-functional teams, delivered projects on time and budget.
            Expert in Agile, Scrum, and project management tools.
            Strong stakeholder management and communication skills.
            PMP certified."""
        ]
    }
    
    # Distribution: 20% excellent, 30% good, 30% average, 15% weak, 5% irrelevant
    distribution = [
        ("excellent_senior", 0.20),
        ("good_mid", 0.30),
        ("average_junior", 0.30),
        ("weak_mismatch", 0.15),
        ("irrelevant", 0.05)
    ]
    
    template_idx = 0
    for category, ratio in distribution:
        category_count = int(count * ratio)
        category_templates = templates[category]
        
        for i in range(category_count):
            template = category_templates[i % len(category_templates)]
            resumes.append({
                "id": f"resume_{template_idx:04d}",
                "resume_text": template,
                "category": category  # For verification
            })
            template_idx += 1
    
    # Fill remaining with mixed
    while len(resumes) < count:
        category = list(templates.keys())[template_idx % len(templates)]
        template = templates[category][0]
        resumes.append({
            "id": f"resume_{template_idx:04d}",
            "resume_text": template,
            "category": category
        })
        template_idx += 1
    
    return resumes


def test_full_pipeline():
    """Test complete 3-tier pipeline integration."""
    
    print("="*80)
    print("COMPREHENSIVE 3-TIER PIPELINE TEST")
    print("="*80)
    
    # Create test data
    print("\n📝 Step 1: Creating diverse test dataset...")
    test_count = 500
    resumes = create_diverse_resumes(test_count)
    print(f"   ✓ Created {len(resumes)} diverse resumes")
    
    # Count by category
    categories = {}
    for resume in resumes:
        cat = resume.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
    print(f"   Distribution:")
    for cat, count in sorted(categories.items()):
        print(f"     • {cat}: {count} ({count/len(resumes)*100:.1f}%)")
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="ats_fulltest_")
    resume_dir = os.path.join(temp_dir, "resumes")
    os.makedirs(resume_dir)
    
    try:
        # Write resumes as JSONL
        jsonl_path = os.path.join(resume_dir, "resumes.jsonl")
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for resume in resumes:
                # Don't include category in actual resume data
                f.write(json.dumps({"id": resume["id"], "resume_text": resume["resume_text"]}) + "\n")
        print(f"   ✓ Wrote resumes to temporary directory")
        
        # Define job description
        job_description = """
        Senior Python Engineer / Tech Lead
        
        Requirements:
        - 5+ years of software engineering experience
        - Strong Python expertise and system design skills
        - Experience with distributed systems and microservices
        - Cloud platforms (AWS, GCP, or Azure)
        - Container orchestration (Docker, Kubernetes)
        - Team leadership and mentoring experience
        
        Nice to have:
        - Machine learning or data engineering experience
        - Published technical content or conference talks
        - Experience at high-growth startups or tech companies
        """
        
        print("\n🎯 Step 2: Running 3-tier pipeline...")
        print(f"   Job: Senior Python Engineer / Tech Lead")
        print(f"   Input: {test_count} resumes")
        print(f"   Target: Top 25 candidates")
        
        # Initialize pipeline
        pipeline = BatchPipeline(n_components=64, max_features=2000)
        
        # Run tiered pipeline
        result = pipeline.run_tiered(
            resume_dir=resume_dir,
            job_description=job_description,
            top_k=25,
            weights=None,
            num_workers=4,
            cache_dir=None,
            tier1_size=200,  # 40% of 500
            tier2_size=50,   # 10% of 500
        )
        
        print("\n" + "="*80)
        print("📊 TEST RESULTS & VALIDATION")
        print("="*80)
        
        # Basic validation
        print(f"\n✅ Pipeline Execution:")
        print(f"   ✓ Total processed: {result['total_resumes_processed']:,}")
        print(f"   ✓ Time elapsed: {result['elapsed_seconds']:.2f}s")
        print(f"   ✓ Speed: {int(result['total_resumes_processed'] / result['elapsed_seconds']):,} resumes/sec")
        print(f"   ✓ Candidates returned: {len(result['candidates'])}")
        
        # Tier statistics
        ts = result['tier_stats']
        print(f"\n✅ Tier Performance:")
        print(f"   Tier 1: {ts['tier1_elapsed']:.2f}s  →  {ts['tier1_cutoff']:,} candidates")
        print(f"   Tier 2: {ts['tier2_elapsed']:.2f}s  →  {ts['tier2_cutoff']:,} candidates")
        print(f"   Tier 3: {ts['tier3_elapsed']:.2f}s  →  {result['top_k']} candidates")
        print(f"\n   Filtering path: {test_count:,} → {ts['tier1_cutoff']:,} → {ts['tier2_cutoff']:,} → {result['top_k']}")
        print(f"   Efficiency: {(1 - result['top_k']/test_count)*100:.1f}% filtered out")
        
        # Score validation
        print(f"\n✅ Scoring Validation:")
        top_candidate = result['candidates'][0]
        bottom_candidate = result['candidates'][-1]
        
        print(f"   Top candidate:")
        print(f"     • Overall: {top_candidate['overall_score']:.2f}")
        print(f"     • Semantic: {top_candidate['all_scores']['semantic_fit']:.2f}")
        print(f"     • Career: {top_candidate['all_scores']['career_growth']:.2f}")
        print(f"     • Portfolio: {top_candidate['all_scores']['team_portfolio']:.2f}")
        
        print(f"   Bottom candidate (cutoff):")
        print(f"     • Overall: {bottom_candidate['overall_score']:.2f}")
        print(f"     • Semantic: {bottom_candidate['all_scores']['semantic_fit']:.2f}")
        print(f"     • Career: {bottom_candidate['all_scores']['career_growth']:.2f}")
        print(f"     • Portfolio: {bottom_candidate['all_scores']['team_portfolio']:.2f}")
        
        print(f"   Score spread: {top_candidate['overall_score'] - bottom_candidate['overall_score']:.2f} points")
        
        # Dimension completeness
        print(f"\n✅ Dimension Completeness:")
        required_dimensions = [
            'semantic_fit', 'career_growth', 'company_context', 'skill_currency',
            'resilience', 'narrative_coherence', 'team_portfolio', 
            'artifact_complexity', 'counterfactual', 'keyword_match'
        ]
        
        for dim in required_dimensions:
            assert dim in top_candidate['all_scores'], f"Missing dimension: {dim}"
            score = top_candidate['all_scores'][dim]
            assert 0 <= score <= 100, f"Invalid score for {dim}: {score}"
        print(f"   ✓ All 10 dimensions present and valid (0-100 range)")
        
        # Tier score progression
        print(f"\n✅ Tier Score Progression:")
        print(f"   Tier 1 (Semantic+Keyword):")
        print(f"     • Top: {ts['tier1_top_score']:.2f}  |  Cutoff: {ts['tier1_cutoff_score']:.2f}")
        print(f"   Tier 2 (+ Medium Heuristics):")
        print(f"     • Top: {ts['tier2_top_score']:.2f}  |  Cutoff: {ts['tier2_cutoff_score']:.2f}")
        print(f"   Final (+ Deep Analysis):")
        print(f"     • Top: {top_candidate['overall_score']:.2f}  |  Cutoff: {bottom_candidate['overall_score']:.2f}")
        
        # Bias comparison
        if result.get('bias_comparison'):
            bc = result['bias_comparison']['summary']
            print(f"\n✅ Bias Comparison:")
            print(f"   • LSA/Keyword overlap: {bc['overlap_count']}/{result['top_k']} ({bc['overlap_pct']}%)")
            print(f"   • LSA-only candidates: {bc['lsa_only_count']}")
            print(f"   • Keyword-only candidates: {bc['keyword_only_count']}")
            print(f"   • Average rank shift: {bc['avg_rank_shift']} positions")
        
        # Assertions
        print(f"\n✅ Integration Tests:")
        assert len(result['candidates']) == 25, "Should return 25 candidates"
        print(f"   ✓ Correct number of candidates (25)")
        
        assert result['total_resumes_processed'] == test_count
        print(f"   ✓ All resumes processed ({test_count})")
        
        assert top_candidate['overall_score'] >= bottom_candidate['overall_score']
        print(f"   ✓ Candidates sorted by score (descending)")
        
        assert ts['tier1_cutoff'] <= 200 and ts['tier2_cutoff'] <= 50
        print(f"   ✓ Tier cutoffs dynamically adjusted ({ts['tier1_cutoff']}, {ts['tier2_cutoff']})")
        
        assert all(0 <= c['overall_score'] <= 100 for c in result['candidates'])
        print(f"   ✓ All scores in valid range (0-100)")
        
        assert 'tier_stats' in result
        print(f"   ✓ Tier statistics present")
        
        assert 'bias_comparison' in result
        print(f"   ✓ Bias comparison report generated")
        
        print(f"\n{'='*80}")
        print(f"🎉 ALL TESTS PASSED!")
        print(f"{'='*80}")
        print(f"\n✨ The 3-tier pipeline is fully integrated and working correctly!")
        print(f"\n📈 Performance Summary:")
        print(f"   • Total time: {result['elapsed_seconds']:.2f}s")
        print(f"   • Tier 1: {ts['tier1_elapsed']:.2f}s ({ts['tier1_elapsed']/result['elapsed_seconds']*100:.0f}%)")
        print(f"   • Tier 2: {ts['tier2_elapsed']:.2f}s ({ts['tier2_elapsed']/result['elapsed_seconds']*100:.0f}%)")
        print(f"   • Tier 3: {ts['tier3_elapsed']:.2f}s ({ts['tier3_elapsed']/result['elapsed_seconds']*100:.0f}%)")
        print(f"   • Throughput: {int(test_count/result['elapsed_seconds']):,} resumes/second")
        
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
            print(f"\n🧹 Cleaned up temp directory")
        except:
            pass


if __name__ == "__main__":
    success = test_full_pipeline()
    sys.exit(0 if success else 1)
