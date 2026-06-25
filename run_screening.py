#!/usr/bin/env python3
"""
ATS Intelligence Engine — Batch Resume Screener

Usage:
  # First run (fits TF-IDF + LSA on the corpus):
  python run_screening.py --resume-dir ./resumes --jd "Software Engineer with 5 years Python"

  # With a JD file:
  python run_screening.py --resume-dir ./resumes --jd-file ./job_description.txt

  # Using cached model (faster subsequent runs):
  python run_screening.py --resume-dir ./resumes --jd-file ./jd.txt --cache-dir ./cache

  # Using only cache (skip model fitting, use pre-computed):
  python run_screening.py --resume-dir ./resumes --jd-file ./jd.txt --cache-dir ./cache --from-cache

  # Custom weights and output:
  python run_screening.py --resume-dir ./resumes --jd "Python developer" --top-k 50 --output ./results.json

  # Parallel processing (use multiple CPU cores for heuristics):
  python run_screening.py --resume-dir ./resumes --jd "Data Scientist" --workers 4
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.batch.pipeline import BatchPipeline
from app.services.batch.screener import screen_from_cache
from app.services.batch.pipeline import DIMENSION_WEIGHTS


def main():
    parser = argparse.ArgumentParser(
        description="ATS Intelligence Engine — Batch Resume Screener",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--resume-dir", required=True, help="Directory containing resume JSON/TXT files.")
    parser.add_argument("--jd", help="Job description text (inline).")
    parser.add_argument("--jd-file", help="Path to file containing job description text.")
    parser.add_argument("--top-k", type=int, default=100, help="Number of top candidates to return (default: 100).")
    parser.add_argument("--output", help="Output file path for results (JSON). If omitted, prints to stdout.")
    parser.add_argument("--cache-dir", help="Directory to store/load fitted vectorizer and SVD model.")
    parser.add_argument("--from-cache", action="store_true", help="Skip fitting, load pre-computed models from cache-dir.")
    parser.add_argument("--workers", type=int, default=None, help="Number of parallel workers (default: CPU count).")
    parser.add_argument("--n-components", type=int, default=128, help="LSA dimensions (default: 128).")
    parser.add_argument("--max-features", type=int, default=10000, help="Max TF-IDF features (default: 10000).")
    parser.add_argument("--weights", help="JSON string of dimension weights, e.g. '{\"semantic_fit\":0.4}'")
    parser.add_argument("--verbose", action="store_true", help="Print detailed progress.")

    args = parser.parse_args()

    if not args.jd and not args.jd_file:
        print("Error: Provide either --jd or --jd-file.")
        sys.exit(1)

    jd_text = args.jd or open(args.jd_file, "r", encoding="utf-8").read()

    weights = DIMENSION_WEIGHTS
    if args.weights:
        try:
            custom = json.loads(args.weights)
            weights = {**DIMENSION_WEIGHTS, **custom}
            total = sum(weights.values())
            if abs(total - 1.0) > 0.01:
                weights = {k: round(v / total, 4) for k, v in weights.items()}
        except json.JSONDecodeError as e:
            print(f"Error parsing weights JSON: {e}")
            sys.exit(1)

    if args.from_cache and args.cache_dir:
        if not os.path.exists(args.cache_dir):
            print(f"Error: Cache directory '{args.cache_dir}' does not exist.")
            sys.exit(1)
        print("Running in cache-only mode...")
        result = screen_from_cache(
            cache_dir=args.cache_dir,
            job_description=jd_text,
            resume_dir=args.resume_dir,
            top_k=args.top_k,
            weights=weights,
        )
    else:
        pipeline = BatchPipeline(
            n_components=args.n_components,
            max_features=args.max_features,
        )
        result = pipeline.run(
            resume_dir=args.resume_dir,
            job_description=jd_text,
            top_k=args.top_k,
            weights=weights,
            num_workers=args.workers,
            cache_dir=args.cache_dir,
        )

    output = json.dumps(result, indent=2, default=str)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"\nResults written to {args.output}")
    else:
        print("\n" + "=" * 80)
        print("SCREENING RESULTS")
        print("=" * 80)
        print(f"Processed {result['total_resumes_processed']} resumes in {result['elapsed_seconds']}s")
        print(f"\nTop {args.top_k} Candidates:")
        print("-" * 80)
        for c in result["candidates"][:10]:
            print(f"  #{c['rank']:3d} | {c['resume_id']:<40s} | Score: {c['overall_score']:5.2f}")
        if len(result["candidates"]) > 10:
            print(f"  ... and {len(result['candidates']) - 10} more")

        if result.get("bias_comparison"):
            bc = result["bias_comparison"]["summary"]
            print(f"\nBias Mirroring:")
            print(f"  Overlap between LSA and Keyword rankings: {bc['overlap_count']}/{args.top_k} ({bc['overlap_pct']}%)")
            print(f"  Candidates unique to LSA ranking: {bc['lsa_only_count']}")
            print(f"  Candidates unique to Keyword ranking: {bc['keyword_only_count']}")
            print(f"  Average rank shift: {bc['avg_rank_shift']} positions")


if __name__ == "__main__":
    main()
