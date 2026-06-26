#!/usr/bin/env python3
"""
Hackathon Submission Generator

Generates properly formatted CSV submission for Redrob Hackathon v4.

Usage:
    python generate_submission.py \
        --candidates ./docs/candidates.jsonl \
        --jd ./docs/job_description.txt \
        --output team_xxx.csv

This script:
1. Loads candidates from JSONL
2. Runs the screening pipeline
3. Generates non-templated reasoning for each candidate
4. Outputs CSV in exact submission format (100 rows)
"""

import argparse
import json
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.batch.pipeline import BatchPipeline
from app.services.reasoning_generator import ReasoningGenerator, parse_jd_requirements
from app.services.csv_writer import write_submission_csv
from app.services.behavioral_signals.scorer import apply_behavioral_multiplier
from app.services.honeypot_detector import HoneypotDetector


def load_candidates_jsonl(jsonl_path: str) -> list[dict]:
    """
    Load candidates from JSONL file.
    
    Expected format:
    {"candidate_id": "CAND_0000001", "profile": {...}, "career_history": [...], ...}
    
    Returns:
        List of candidate dicts with candidate_data and resume_text
    """
    candidates = []
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                
                # Extract text representation for screening
                # Combine profile, career history, and skills into searchable text
                resume_text = _candidate_to_text(data)
                
                candidates.append({
                    'candidate_id': data.get('candidate_id', f'CAND_{line_num:07d}'),
                    'resume_text': resume_text,
                    'candidate_data': data  # Keep full data for reasoning
                })
                
            except json.JSONDecodeError as e:
                print(f"Warning: Skipping invalid JSON on line {line_num}: {e}")
                continue
    
    return candidates


def _candidate_to_text(candidate: dict) -> str:
    """
    Convert structured candidate JSON to text for TF-IDF processing.
    
    Extracts:
    - Profile summary, headline, title, company
    - Career history descriptions
    - Skills list
    - Education
    """
    parts = []
    
    # Profile
    if 'profile' in candidate:
        profile = candidate['profile']
        parts.append(profile.get('headline', ''))
        parts.append(profile.get('summary', ''))
        parts.append(profile.get('current_title', ''))
        parts.append(profile.get('current_company', ''))
        parts.append(profile.get('location', ''))
    
    # Career history
    if 'career_history' in candidate:
        for role in candidate['career_history']:
            parts.append(role.get('title', ''))
            parts.append(role.get('company', ''))
            parts.append(role.get('description', ''))
    
    # Skills
    if 'skills' in candidate:
        skill_names = [s.get('name', '') for s in candidate['skills']]
        parts.append(' '.join(skill_names))
    
    # Education
    if 'education' in candidate:
        for edu in candidate['education']:
            parts.append(edu.get('institution', ''))
            parts.append(edu.get('degree', ''))
            parts.append(edu.get('field_of_study', ''))
    
    return ' '.join(filter(None, parts))


def save_temp_resumes(candidates: list[dict], temp_dir: str) -> str:
    """
    Save candidates as individual text files for pipeline processing.
    
    Args:
        candidates: List of candidate dicts with resume_text
        temp_dir: Temporary directory to save files
    
    Returns:
        Path to temp directory
    """
    temp_path = Path(temp_dir)
    temp_path.mkdir(parents=True, exist_ok=True)
    
    for candidate in candidates:
        cid = candidate['candidate_id']
        text = candidate['resume_text']
        
        file_path = temp_path / f"{cid}.txt"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
    
    return str(temp_path)


def main():
    parser = argparse.ArgumentParser(
        description="Generate hackathon submission CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--candidates', required=True, help='Path to candidates.jsonl')
    parser.add_argument('--jd', '--jd-file', dest='jd_file', required=True, help='Path to job_description.txt')
    parser.add_argument('--output', required=True, help='Output CSV path (e.g., team_xxx.csv)')
    parser.add_argument('--top-k', type=int, default=100, help='Number of candidates (must be 100 for submission)')
    parser.add_argument('--tiered', action='store_true', default=True, help='Use 3-tier filtering (default: True)')
    parser.add_argument('--workers', type=int, default=8, help='Number of parallel workers (default: 8)')
    parser.add_argument('--temp-dir', default='./temp_resumes', help='Temporary directory for processing')
    parser.add_argument('--validate-only', action='store_true', help='Only validate, do not write CSV')
    parser.add_argument('--verbose', action='store_true', help='Print detailed progress')
    
    args = parser.parse_args()
    
    # Validate top-k is 100
    if args.top_k != 100:
        print(f"Warning: Submission requires exactly 100 candidates. Setting --top-k to 100.")
        args.top_k = 100
    
    print(f"{'='*80}")
    print("HACKATHON SUBMISSION GENERATOR")
    print(f"{'='*80}\n")
    
    # Step 1: Load job description
    print(f"[1/6] Loading job description from {args.jd_file}...")
    with open(args.jd_file, 'r', encoding='utf-8') as f:
        jd_text = f.read()
    
    jd_requirements = parse_jd_requirements(jd_text)
    print(f"      Parsed requirements: {len(jd_requirements.get('skills', []))} skills, "
          f"{jd_requirements.get('min_experience', 0)}-{jd_requirements.get('max_experience', 0)} years experience")
    
    # Step 2: Load candidates
    print(f"\n[2/7] Loading candidates from {args.candidates}...")
    candidates = load_candidates_jsonl(args.candidates)
    print(f"      Loaded {len(candidates)} candidates")
    
    if len(candidates) == 0:
        print("Error: No candidates found in JSONL file")
        sys.exit(1)
    
    # Step 2.5: Filter honeypots
    print(f"\n[2.5/7] Detecting and filtering honeypot candidates...")
    honeypot_detector = HoneypotDetector(strict_mode=False)
    valid_candidates, honeypots = honeypot_detector.filter_honeypots(
        [c['candidate_data'] for c in candidates]
    )
    
    print(f"      Found {len(honeypots)} honeypot candidates")
    print(f"      Kept {len(valid_candidates)} valid candidates")
    
    if args.verbose and honeypots:
        print(f"\n      Sample honeypot detection:")
        for i, honey in enumerate(honeypots[:3]):
            cid = honey.get('candidate_id') or honey.get('profile', {}).get('anonymized_name', 'Unknown')
            print(f"        {i+1}. {cid}")
            for reason in honey.get('honeypot_reasons', [])[:2]:
                print(f"           - {reason}")
    
    # Filter candidates list to only valid ones
    valid_candidate_ids = {c.get('candidate_id') for c in valid_candidates}
    candidates = [c for c in candidates if c['candidate_id'] in valid_candidate_ids]
    
    # Step 3: Prepare temp files for pipeline
    print(f"\n[3/7] Preparing candidates for screening pipeline...")
    temp_dir = save_temp_resumes(candidates, args.temp_dir)
    print(f"      Saved {len(candidates)} resume files to {temp_dir}")
    
    # Step 4: Run screening pipeline
    print(f"\n[4/7] Running screening pipeline (tiered={args.tiered})...")
    print(f"      This may take a few minutes for large datasets...")
    
    pipeline = BatchPipeline()
    
    if args.tiered:
        result = pipeline.run_tiered(
            resume_dir=temp_dir,
            job_description=jd_text,
            top_k=args.top_k,
            num_workers=args.workers
        )
    else:
        result = pipeline.run(
            resume_dir=temp_dir,
            job_description=jd_text,
            top_k=args.top_k,
            num_workers=args.workers
        )
    
    print(f"      ✓ Processed {result['total_resumes_processed']} resumes in {result['elapsed_seconds']:.1f}s")
    print(f"      ✓ Ranked top {len(result['candidates'])} candidates")
    
    # Step 4.5: Apply behavioral signals
    print(f"\n[4.5/7] Applying behavioral signals...")
    candidates_with_behavioral = []
    
    for ranked_candidate in result['candidates']:
        cid = ranked_candidate['resume_id']
        full_data = candidate_lookup.get(cid, {})
        redrob_signals = full_data.get('redrob_signals', {})
        
        # Apply behavioral multiplier
        behavioral_result = apply_behavioral_multiplier(
            base_score=ranked_candidate['overall_score'],
            redrob_signals=redrob_signals,
            jd_requirements=jd_requirements
        )
        
        # Update score
        ranked_candidate['base_score'] = ranked_candidate['overall_score']
        ranked_candidate['overall_score'] = behavioral_result['final_score']
        ranked_candidate['behavioral_multiplier'] = behavioral_result['behavioral_multiplier']
        ranked_candidate['behavioral_penalties'] = behavioral_result['penalties']
        ranked_candidate['behavioral_boosts'] = behavioral_result['boosts']
        
        candidates_with_behavioral.append(ranked_candidate)
    
    # Re-sort by new scores and re-rank
    candidates_with_behavioral.sort(key=lambda x: x['overall_score'], reverse=True)
    for new_rank, candidate in enumerate(candidates_with_behavioral, 1):
        candidate['rank'] = new_rank
    
    # Update result
    result['candidates'] = candidates_with_behavioral
    
    print(f"      ✓ Applied behavioral multipliers (range: "
          f"{min(c['behavioral_multiplier'] for c in result['candidates']):.2f} - "
          f"{max(c['behavioral_multiplier'] for c in result['candidates']):.2f})")
    
    # Step 5: Generate reasoning
    print(f"\n[5/7] Generating reasoning for each candidate...")
    reasoning_gen = ReasoningGenerator(jd_requirements)
    
    # Attach full candidate data to results
    candidate_lookup = {c['candidate_id']: c['candidate_data'] for c in candidates}
    
    for ranked_candidate in result['candidates']:
        cid = ranked_candidate['resume_id']
        
        # Get full candidate data
        full_data = candidate_lookup.get(cid, {})
        
        # Generate reasoning
        reasoning = reasoning_gen.generate(
            candidate=full_data,
            rank=ranked_candidate['rank'],
            scores=ranked_candidate['all_scores']
        )
        
        ranked_candidate['reasoning'] = reasoning
        ranked_candidate['candidate_data'] = full_data  # Attach for CSV writer
    
    print(f"      ✓ Generated reasoning for {len(result['candidates'])} candidates")
    
    # Show sample
    if args.verbose and len(result['candidates']) > 0:
        print(f"\n      Sample reasoning (Rank 1):")
        sample = result['candidates'][0]
        print(f"      {sample['resume_id']}: \"{sample['reasoning']}\"")
    
    # Step 6: Validate honeypot rate in top 100
    print(f"\n[6/7] Checking honeypot rate in top 100...")
    top_100_data = [
        candidate_lookup.get(c['resume_id'], {}) 
        for c in result['candidates'][:100]
    ]
    
    honeypot_check = honeypot_detector.calculate_honeypot_rate(top_100_data)
    
    print(f"      Honeypot rate: {honeypot_check['honeypot_rate']:.1f}% "
          f"({honeypot_check['honeypots_detected']}/100)")
    
    if honeypot_check['passes_threshold']:
        print(f"      ✓ PASSES threshold (≤10%)")
    else:
        print(f"      ✗ FAILS threshold (>10%) - Submission will be disqualified!")
        print(f"      Consider adjusting your ranking algorithm.")
    
    if args.verbose and honeypot_check['honeypot_list']:
        print(f"\n      Detected honeypots in top 100:")
        for hp in honeypot_check['honeypot_list'][:3]:
            print(f"        - {hp['candidate_id']}")
            for reason in hp['reasons'][:2]:
                print(f"          • {reason}")
    
    # Step 7: Write CSV
    print(f"\n[7/7] Writing submission CSV to {args.output}...")
    
    try:
        write_result = write_submission_csv(
            candidates=result['candidates'],
            output_path=args.output,
            validate_only=args.validate_only
        )
        
        if args.validate_only:
            if write_result['valid']:
                print(f"      ✓ Validation PASSED")
            else:
                print(f"      ✗ Validation FAILED:")
                for error in write_result['validation']['errors']:
                    print(f"        - {error}")
                sys.exit(1)
        else:
            print(f"      ✓ Written {write_result['rows_written']} rows to {write_result['output_path']}")
            
            # Show validation warnings
            if write_result['validation']['warnings']:
                print(f"\n      Warnings:")
                for warning in write_result['validation']['warnings']:
                    print(f"        ⚠ {warning}")
            
            # Show stats
            stats = write_result['validation']['stats']
            print(f"\n      Statistics:")
            print(f"        - Total candidates: {stats['total_candidates']}")
            print(f"        - Unique ranks: {stats['unique_ranks']}")
            print(f"        - Score range: {stats['min_score']:.2f} - {stats['max_score']:.2f}")
            print(f"        - Empty reasoning: {stats['empty_reasoning_count']}")
    
    except Exception as e:
        print(f"      ✗ Error writing CSV: {e}")
        sys.exit(1)
    
    # Cleanup temp files
    import shutil
    if os.path.exists(temp_dir) and temp_dir.startswith('./temp'):
        shutil.rmtree(temp_dir)
        print(f"\n      Cleaned up temporary files in {temp_dir}")
    
    print(f"\n{'='*80}")
    print("✅ SUBMISSION GENERATION COMPLETE!")
    print(f"{'='*80}\n")
    print(f"Output: {args.output}")
    print(f"Candidates: {len(result['candidates'])}")
    print(f"Time: {result['elapsed_seconds']:.1f}s")
    print(f"\nReady to submit! 🚀")


if __name__ == '__main__':
    main()
