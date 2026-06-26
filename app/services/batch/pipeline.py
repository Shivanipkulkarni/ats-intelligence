import os
import json
import time
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

from app.services.batch.semantic_engine import BatchSemanticEngine
from app.services.career_trajectory.scorer import compute_career_trajectory
from app.services.narrative_coherence.scorer import compute_narrative_coherence
from app.services.team_portfolio.scorer import compute_team_portfolio
from app.services.artifact_complexity.scorer import compute_artifact_complexity
from app.services.counterfactual.scorer import compute_counterfactual


DIMENSION_WEIGHTS = {
    "semantic_fit": 0.25,
    "career_growth": 0.15,
    "company_context": 0.05,
    "skill_currency": 0.10,
    "resilience": 0.10,
    "narrative_coherence": 0.10,
    "team_portfolio": 0.10,
    "artifact_complexity": 0.10,
    "counterfactual": 0.05,
}


def load_resumes(resume_dir: str) -> list[dict]:
    jsonl_path = os.path.join(resume_dir, "resumes.jsonl")
    if os.path.exists(jsonl_path):
        records = []
        with open(jsonl_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                text = data.get("text", data.get("resume_text", data.get("content", "")))
                records.append({
                    "resume_id": data.get("id", data.get("resume_id", str(len(records)))),
                    "resume_text": text,
                    "metadata": {k: v for k, v in data.items() if k not in ("text", "resume_text", "content")},
                })
        return records

    records = []
    for fname in os.listdir(resume_dir):
        path = os.path.join(resume_dir, fname)
        ext = os.path.splitext(fname)[1].lower()

        if ext == ".json":
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            if isinstance(data, dict):
                text = data.get("text", data.get("resume_text", data.get("content", "")))
                records.append({
                    "resume_id": data.get("id", data.get("resume_id", fname)),
                    "resume_text": text,
                    "metadata": {k: v for k, v in data.items() if k not in ("text", "resume_text", "content")},
                })
            elif isinstance(data, str):
                records.append({"resume_id": fname, "resume_text": data, "metadata": {}})

        elif ext == ".txt":
            with open(path, "r", encoding="utf-8-sig") as f:
                records.append({"resume_id": fname, "resume_text": f.read(), "metadata": {}})

        else:
            continue

    return records


def compute_heuristic_signals(resume_text: str) -> dict:
    from app.services.career_trajectory.extractor import parse_roles_from_text
    roles = parse_roles_from_text(resume_text)

    career = compute_career_trajectory(resume_text, roles)
    narrative = compute_narrative_coherence(resume_text, roles)
    portfolio = compute_team_portfolio(resume_text, roles)
    artifact = compute_artifact_complexity(resume_text, roles)
    counterfactual = compute_counterfactual(resume_text, roles)

    return {
        "career_growth_score": career["career_growth_score"],
        "company_context_score": 65.0,
        "skill_currency_score": 60.0,
        "resilience_score": 65.0,
        "narrative_coherence_score": narrative["narrative_coherence_score"],
        "team_portfolio_score": portfolio["team_portfolio_score"],
        "artifact_complexity_score": artifact["artifact_complexity_score"],
        "counterfactual_score": counterfactual["counterfactual_score"],
        "reasons": (
            career["reasons"][:2] +
            narrative["reasons"][:1] +
            portfolio["reasons"][:1] +
            artifact["reasons"][:1] +
            counterfactual["reasons"][:1]
        ),
    }


def compute_keyword_scores_batch(records: list[dict], jd_text: str) -> list[float]:
    from app.services.bias_mirror.scorer import compute_keyword_match_resume_jd
    scores = []
    for i, r in enumerate(records):
        if i % 5000 == 0 and i > 0:
            print(f"  Keyword progress: {i}/{len(records)}")
        kw = compute_keyword_match_resume_jd(r["resume_text"], jd_text)
        scores.append(kw["keyword_match_score"])
    return scores


def process_chunk_heuristic(chunk: list[dict]) -> list[dict]:
    results = []
    for record in chunk:
        signals = compute_heuristic_signals(record["resume_text"])
        results.append({
            "resume_id": record["resume_id"],
            **signals,
        })
    return results


def process_chunk_keyword(chunk_data: list[tuple]) -> list[dict]:
    results = []
    for resume_id, resume_text, jd_text in chunk_data:
        from app.services.bias_mirror.scorer import compute_keyword_match_resume_jd
        kw = compute_keyword_match_resume_jd(resume_text, jd_text)
        results.append({
            "resume_id": resume_id,
            "keyword_match_score": kw["keyword_match_score"],
        })
    return results


def compute_overall_score(
    signals: dict,
    jd_semantic_score: float,
    weights: dict[str, float] | None = None,
) -> float:
    w = weights or DIMENSION_WEIGHTS
    score = (
        jd_semantic_score * w.get("semantic_fit", 0.25) +
        signals.get("career_growth_score", 0) * w.get("career_growth", 0.15) +
        signals.get("company_context_score", 0) * w.get("company_context", 0.05) +
        signals.get("skill_currency_score", 0) * w.get("skill_currency", 0.10) +
        signals.get("resilience_score", 0) * w.get("resilience", 0.10) +
        signals.get("narrative_coherence_score", 0) * w.get("narrative_coherence", 0.10) +
        signals.get("team_portfolio_score", 0) * w.get("team_portfolio", 0.10) +
        signals.get("artifact_complexity_score", 0) * w.get("artifact_complexity", 0.10) +
        signals.get("counterfactual_score", 0) * w.get("counterfactual", 0.05)
    )
    return round(score, 2)


class BatchPipeline:
    def __init__(self, n_components: int = 128, max_features: int = 10000):
        self.semantic_engine = BatchSemanticEngine(
            n_components=n_components,
            max_features=max_features,
        )
        self.resume_records: list[dict] = []
        self.lsa_matrix: np.ndarray | None = None
        self.cache_dir: str | None = None

    def run_tiered(
        self,
        resume_dir: str,
        job_description: str,
        top_k: int = 100,
        weights: dict[str, float] | None = None,
        num_workers: int | None = None,
        cache_dir: str | None = None,
        tier1_size: int = 40000,
        tier2_size: int = 5000,
    ) -> dict:
        """
        Three-tiered filtering pipeline for efficient large-scale resume screening.
        
        Tier 1 (200K → 40K): Fast semantic + keyword filtering
        Tier 2 (40K → 5K): Add medium-cost heuristics
        Tier 3 (5K → 100): Full deep analysis with all dimensions
        """
        self.cache_dir = cache_dir
        start = time.time()

        if num_workers is None:
            num_workers = os.cpu_count() or 1

        print(f"Loading resumes from {resume_dir}...")
        records = load_resumes(resume_dir)
        n = len(records)
        print(f"Loaded {n} resumes. Using {num_workers} workers.")
        
        # Adjust tier sizes dynamically if input is smaller than expected
        actual_tier1_size = min(tier1_size, max(int(n * 0.2), top_k))  # At least 20% or top_k
        actual_tier2_size = min(tier2_size, max(int(actual_tier1_size * 0.125), top_k))  # At least 12.5% of tier1 or top_k
        
        print(f"Tiered filtering enabled: {n} → {actual_tier1_size} → {actual_tier2_size} → {top_k}")

        if n == 0:
            raise ValueError("No resumes found in directory.")

        # ========== TIER 1: Semantic + Keyword Filter (Fast) ==========
        print(f"\n{'='*80}")
        print(f"TIER 1: Semantic + Keyword filtering ({n} → {tier1_size})")
        print(f"{'='*80}")
        
        tier1_start = time.time()
        
        # Fit semantic engine on full corpus
        print("Fitting TF-IDF + LSA semantic engine on corpus...")
        fit_start = time.time()
        self.lsa_matrix = self.semantic_engine.fit_transform([r["resume_text"] for r in records])
        print(f"Semantic engine fitted in {time.time() - fit_start:.2f}s. Shape: {self.lsa_matrix.shape}")

        if cache_dir:
            self.semantic_engine.save(cache_dir)

        # Compute semantic scores for all resumes
        print("Computing semantic similarity scores...")
        jd_vec = self.semantic_engine.transform_one(job_description)
        semantic_scores = self.semantic_engine.similarity(jd_vec, self.lsa_matrix)
        raw_sem_scores = ((semantic_scores + 1) / 2) * 100  # Normalize to 0-100

        # Compute keyword scores for all resumes (parallel)
        print(f"Computing keyword match scores ({num_workers} workers)...")
        kw_start = time.time()
        kw_results = _run_parallel_keyword(records, job_description, num_workers)
        kw_scores_map = {r["resume_id"]: r["keyword_match_score"] for r in kw_results}
        print(f"Keyword scores computed in {time.time() - kw_start:.2f}s.")

        # Tier 1 scoring: 70% semantic + 30% keyword
        print("Ranking candidates for Tier 1...")
        tier1_candidates = []
        for i in range(n):
            rid = records[i]["resume_id"]
            sem_score = round(float(raw_sem_scores[i]), 2)
            kw_score = kw_scores_map.get(rid, 0)
            
            tier1_score = round(sem_score * 0.7 + kw_score * 0.3, 2)
            
            tier1_candidates.append({
                "resume_id": rid,
                "resume_text": records[i]["resume_text"],
                "semantic_fit": sem_score,
                "keyword_match": kw_score,
                "tier1_score": tier1_score,
            })

        # Sort and filter to top tier1_size candidates
        tier1_candidates.sort(key=lambda x: x["tier1_score"], reverse=True)
        tier1_shortlist = tier1_candidates[:actual_tier1_size]
        
        tier1_elapsed = time.time() - tier1_start
        print(f"✓ Tier 1 complete in {tier1_elapsed:.2f}s")
        print(f"  Top score: {tier1_shortlist[0]['tier1_score']:.2f}")
        print(f"  Cutoff score: {tier1_shortlist[-1]['tier1_score']:.2f}")
        print(f"  Filtered out: {n - actual_tier1_size:,} resumes ({(n - actual_tier1_size) / n * 100:.1f}%)")

        # ========== TIER 2: Medium-Cost Heuristics ==========
        print(f"\n{'='*80}")
        print(f"TIER 2: Adding medium-cost heuristics ({actual_tier1_size:,} → {actual_tier2_size:,})")
        print(f"{'='*80}")
        
        tier2_start = time.time()
        
        # Compute narrative, portfolio, and artifact complexity
        print(f"Computing medium-cost dimensions ({num_workers} workers)...")
        tier2_signals = _run_parallel_tier2(tier1_shortlist, num_workers)
        
        # Tier 2 scoring: semantic 35%, keyword 15%, narrative 20%, portfolio 15%, artifact 15%
        tier2_candidates = []
        for i, candidate in enumerate(tier1_shortlist):
            signals = tier2_signals[i]
            
            tier2_score = round(
                candidate["semantic_fit"] * 0.35 +
                candidate["keyword_match"] * 0.15 +
                signals["narrative_coherence_score"] * 0.20 +
                signals["team_portfolio_score"] * 0.15 +
                signals["artifact_complexity_score"] * 0.15,
                2
            )
            
            tier2_candidates.append({
                **candidate,
                "narrative_coherence": signals["narrative_coherence_score"],
                "team_portfolio": signals["team_portfolio_score"],
                "artifact_complexity": signals["artifact_complexity_score"],
                "tier2_score": tier2_score,
                "tier2_reasons": signals["reasons"],
            })
        
        # Sort and filter to top tier2_size candidates
        tier2_candidates.sort(key=lambda x: x["tier2_score"], reverse=True)
        tier2_shortlist = tier2_candidates[:actual_tier2_size]
        
        tier2_elapsed = time.time() - tier2_start
        print(f"✓ Tier 2 complete in {tier2_elapsed:.2f}s")
        print(f"  Top score: {tier2_shortlist[0]['tier2_score']:.2f}")
        print(f"  Cutoff score: {tier2_shortlist[-1]['tier2_score']:.2f}")
        print(f"  Average score: {sum(c['tier2_score'] for c in tier2_shortlist) / len(tier2_shortlist):.2f}")
        print(f"  Filtered out: {actual_tier1_size - actual_tier2_size:,} resumes ({(actual_tier1_size - actual_tier2_size) / actual_tier1_size * 100:.1f}%)")

        # ========== TIER 3: Full Deep Analysis ==========
        print(f"\n{'='*80}")
        print(f"TIER 3: Full deep analysis ({actual_tier2_size:,} → {top_k})")
        print(f"{'='*80}")
        
        tier3_start = time.time()
        
        # Compute expensive dimensions (career, counterfactual)
        print(f"Computing deep analysis dimensions ({num_workers} workers)...")
        tier3_signals = _run_parallel_tier3(tier2_shortlist, num_workers)
        
        # Final scoring with all 10 dimensions
        final_candidates = []
        for i, candidate in enumerate(tier2_shortlist):
            signals = tier3_signals[i]
            
            overall = compute_overall_score(
                {
                    "semantic_fit_score": candidate["semantic_fit"],
                    "career_growth_score": signals["career_growth_score"],
                    "company_context_score": 65.0,
                    "skill_currency_score": 60.0,
                    "resilience_score": 65.0,
                    "narrative_coherence_score": candidate["narrative_coherence"],
                    "team_portfolio_score": candidate["team_portfolio"],
                    "artifact_complexity_score": candidate["artifact_complexity"],
                    "counterfactual_score": signals["counterfactual_score"],
                },
                candidate["semantic_fit"],
                weights,
            )
            
            # Combine reasons from all tiers
            all_reasons = (
                signals["career_reasons"][:2] +
                candidate.get("tier2_reasons", [])[:2] +
                signals["counterfactual_reasons"][:1]
            )
            
            final_candidates.append({
                "resume_id": candidate["resume_id"],
                "overall_score": overall,
                "all_scores": {
                    "semantic_fit": candidate["semantic_fit"],
                    "career_growth": signals["career_growth_score"],
                    "company_context": 65.0,
                    "skill_currency": 60.0,
                    "resilience": 65.0,
                    "narrative_coherence": candidate["narrative_coherence"],
                    "team_portfolio": candidate["team_portfolio"],
                    "artifact_complexity": candidate["artifact_complexity"],
                    "counterfactual": signals["counterfactual_score"],
                    "keyword_match": candidate["keyword_match"],
                },
                "reasons": all_reasons,
            })
        
        # Sort and get top K
        final_candidates.sort(key=lambda x: x["overall_score"], reverse=True)
        top_candidates = final_candidates[:top_k]
        
        tier3_elapsed = time.time() - tier3_start
        print(f"✓ Tier 3 complete in {tier3_elapsed:.2f}s")
        print(f"  Top score: {top_candidates[0]['overall_score']:.2f}")
        print(f"  Cutoff score: {top_candidates[-1]['overall_score']:.2f}")
        print(f"  Average score: {sum(c['overall_score'] for c in top_candidates) / len(top_candidates):.2f}")
        print(f"  Score spread: {top_candidates[0]['overall_score'] - top_candidates[-1]['overall_score']:.2f} points")
        print(f"  Final selection: {len(top_candidates)} candidates")

        # Bias comparison (using original keyword ranking)
        print(f"\nGenerating bias comparison report...")
        kw_ranked = sorted(
            [{"resume_id": r["resume_id"], "overall_score": kw_scores_map.get(r["resume_id"], 0)} 
             for r in records],
            key=lambda x: x["overall_score"],
            reverse=True,
        )[:top_k]

        from app.services.bias_mirror.scorer import compute_bias_comparison
        bias = compute_bias_comparison(top_candidates, kw_ranked, top_k)

        total_elapsed = round(time.time() - start, 2)
        print(f"\n{'='*80}")
        print(f"TIERED PIPELINE COMPLETE")
        print(f"{'='*80}")
        print(f"Total time: {total_elapsed:.2f}s for {n:,} resumes")
        print(f"  Tier 1 (Semantic + Keyword):  {tier1_elapsed:>6.2f}s  ({tier1_elapsed/total_elapsed*100:>5.1f}%)")
        print(f"  Tier 2 (Medium Heuristics):   {tier2_elapsed:>6.2f}s  ({tier2_elapsed/total_elapsed*100:>5.1f}%)")
        print(f"  Tier 3 (Deep Analysis):       {tier3_elapsed:>6.2f}s  ({tier3_elapsed/total_elapsed*100:>5.1f}%)")
        print(f"\nProcessing speed: {int(n / total_elapsed):,} resumes/second")
        print(f"Filtering efficiency: {n:,} → {actual_tier1_size:,} → {actual_tier2_size:,} → {top_k}")
        print(f"Reduction rate: {(1 - top_k/n)*100:.2f}% of candidates filtered out")
        
        if bias and bias.get('summary'):
            bc = bias['summary']
            print(f"\n📊 Bias Comparison:")
            print(f"  Overlap: {bc['overlap_count']}/{top_k} ({bc['overlap_pct']}%)")
            print(f"  LSA-only: {bc['lsa_only_count']} | Keyword-only: {bc['keyword_only_count']}")

        return {
            "job_title": "",
            "top_k": top_k,
            "total_resumes_processed": n,
            "elapsed_seconds": total_elapsed,
            "tier_stats": {
                "tier1_elapsed": round(tier1_elapsed, 2),
                "tier2_elapsed": round(tier2_elapsed, 2),
                "tier3_elapsed": round(tier3_elapsed, 2),
                "tier1_cutoff": actual_tier1_size,
                "tier2_cutoff": actual_tier2_size,
                "tier1_top_score": round(tier1_shortlist[0]['tier1_score'], 2),
                "tier1_cutoff_score": round(tier1_shortlist[-1]['tier1_score'], 2),
                "tier2_top_score": round(tier2_shortlist[0]['tier2_score'], 2),
                "tier2_cutoff_score": round(tier2_shortlist[-1]['tier2_score'], 2),
            },
            "candidates": [
                {"rank": i + 1, "resume_id": r["resume_id"], "overall_score": r["overall_score"],
                 "all_scores": r["all_scores"], "reasons": r["reasons"]}
                for i, r in enumerate(top_candidates)
            ],
            "lsa_ranking": [
                {"rank": i + 1, "resume_id": r["resume_id"], "overall_score": r["overall_score"],
                 "all_scores": r["all_scores"], "reasons": r["reasons"]}
                for i, r in enumerate(top_candidates)
            ],
            "keyword_ranking": [
                {"rank": i + 1, "resume_id": r["resume_id"], "overall_score": r["overall_score"],
                 "all_scores": {}, "reasons": []}
                for i, r in enumerate(kw_ranked)
            ],
            "bias_comparison": bias,
        }

    def run(
        self,
        resume_dir: str,
        job_description: str,
        top_k: int = 100,
        weights: dict[str, float] | None = None,
        num_workers: int | None = None,
        cache_dir: str | None = None,
    ) -> dict:
        self.cache_dir = cache_dir
        start = time.time()

        if num_workers is None:
            num_workers = os.cpu_count() or 1

        print(f"Loading resumes from {resume_dir}...")
        records = load_resumes(resume_dir)
        n = len(records)
        print(f"Loaded {n} resumes. Using {num_workers} workers.")

        if n == 0:
            raise ValueError("No resumes found in directory.")

        fit_start = time.time()
        print("Fitting TF-IDF + LSA semantic engine on corpus...")
        self.lsa_matrix = self.semantic_engine.fit_transform([r["resume_text"] for r in records])
        print(f"Semantic engine fitted in {time.time() - fit_start:.2f}s. Shape: {self.lsa_matrix.shape}")

        if cache_dir:
            self.semantic_engine.save(cache_dir)

        jd_vec = self.semantic_engine.transform_one(job_description)
        semantic_scores = self.semantic_engine.similarity(jd_vec, self.lsa_matrix)
        raw_sem_scores = ((semantic_scores + 1) / 2) * 100

        heuristic_start = time.time()
        print(f"Computing heuristic signals ({num_workers} workers)...")
        signals_list = _run_parallel_heuristic(records, num_workers)
        print(f"Heuristic signals computed in {time.time() - heuristic_start:.2f}s.")

        kw_start = time.time()
        print(f"Computing keyword match scores ({num_workers} workers)...")
        kw_results = _run_parallel_keyword(records, job_description, num_workers)
        kw_scores_map = {r["resume_id"]: r["keyword_match_score"] for r in kw_results}
        print(f"Keyword scores computed in {time.time() - kw_start:.2f}s.")

        rank_start = time.time()
        print("Ranking candidates...")
        all_results = []
        for i in range(n):
            rid = records[i]["resume_id"]
            signals = signals_list[i]
            sem_score = round(float(raw_sem_scores[i]), 2)
            kw_score = kw_scores_map.get(rid, 0)

            overall = compute_overall_score(
                signals | {"semantic_fit_score": sem_score},
                sem_score,
                weights,
            )

            all_results.append({
                "resume_id": rid,
                "overall_score": overall,
                "all_scores": {
                    "semantic_fit": sem_score,
                    "career_growth": signals["career_growth_score"],
                    "company_context": signals["company_context_score"],
                    "skill_currency": signals["skill_currency_score"],
                    "resilience": signals["resilience_score"],
                    "narrative_coherence": signals["narrative_coherence_score"],
                    "team_portfolio": signals["team_portfolio_score"],
                    "artifact_complexity": signals["artifact_complexity_score"],
                    "counterfactual": signals["counterfactual_score"],
                    "keyword_match": round(kw_score, 2),
                },
                "reasons": signals["reasons"],
            })

        all_results.sort(key=lambda x: x["overall_score"], reverse=True)
        top = all_results[:top_k]

        kw_ranked = sorted(
            [{"resume_id": rid, "overall_score": kw_scores_map.get(rid, 0)} for rid in [r["resume_id"] for r in records]],
            key=lambda x: x["overall_score"],
            reverse=True,
        )[:top_k]

        from app.services.bias_mirror.scorer import compute_bias_comparison
        bias = compute_bias_comparison(top, kw_ranked, top_k)

        elapsed = round(time.time() - start, 2)
        print(f"\nTotal elapsed: {elapsed:.2f}s for {n} resumes.")

        return {
            "job_title": "",
            "top_k": top_k,
            "total_resumes_processed": n,
            "elapsed_seconds": elapsed,
            "candidates": [
                {"rank": i + 1, "resume_id": r["resume_id"], "overall_score": r["overall_score"],
                 "all_scores": r["all_scores"], "reasons": r["reasons"]}
                for i, r in enumerate(top)
            ],
            "lsa_ranking": [
                {"rank": i + 1, "resume_id": r["resume_id"], "overall_score": r["overall_score"],
                 "all_scores": r["all_scores"], "reasons": r["reasons"]}
                for i, r in enumerate(top)
            ],
            "keyword_ranking": [
                {"rank": i + 1, "resume_id": r["resume_id"], "overall_score": r["overall_score"],
                 "all_scores": {}, "reasons": []}
                for i, r in enumerate(kw_ranked)
            ],
            "bias_comparison": bias,
        }


def _chunk_records(records: list, num_chunks: int) -> list:
    chunk_size = max(1, len(records) // num_chunks)
    return [records[i:i + chunk_size] for i in range(0, len(records), chunk_size)]


def _run_parallel_heuristic(records: list[dict], num_workers: int) -> list[dict]:
    if num_workers <= 1:
        signals_list = []
        for i, rec in enumerate(records):
            if i % 1000 == 0 and i > 0:
                print(f"  Heuristic progress: {i}/{len(records)}")
            signals_list.append(compute_heuristic_signals(rec["resume_text"]))
        return signals_list

    chunks = _chunk_records(records, num_workers)
    all_results = [None] * len(records)

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(process_chunk_heuristic, chunk): i for i, chunk in enumerate(chunks)}
        for future in as_completed(futures):
            chunk_idx = futures[future]
            chunk_results = future.result()
            start_idx = chunk_idx * max(1, len(records) // num_workers)
            for j, result in enumerate(chunk_results):
                all_results[start_idx + j] = result

    return [
        {k: v for k, v in r.items() if k not in ("resume_id",)}
        for r in all_results
    ]


def _run_parallel_keyword(records: list[dict], jd_text: str, num_workers: int) -> list[dict]:
    if num_workers <= 1:
        scores = compute_keyword_scores_batch(records, jd_text)
        return [
            {"resume_id": records[i]["resume_id"], "keyword_match_score": scores[i]}
            for i in range(len(records))
        ]

    chunk_data = []
    for r in records:
        chunk_data.append((r["resume_id"], r["resume_text"], jd_text))

    chunks = _chunk_records(chunk_data, num_workers)
    all_results = [None] * len(records)

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(process_chunk_keyword, chunk): i for i, chunk in enumerate(chunks)}
        for future in as_completed(futures):
            chunk_idx = futures[future]
            chunk_results = future.result()
            start_idx = chunk_idx * max(1, len(chunk_data) // num_workers)
            for j, result in enumerate(chunk_results):
                all_results[start_idx + j] = result

    return [r for r in all_results if r is not None]


def process_chunk_tier2(chunk: list[dict]) -> list[dict]:
    """Process Tier 2 medium-cost heuristics for a chunk of candidates."""
    results = []
    for candidate in chunk:
        from app.services.career_trajectory.extractor import parse_roles_from_text
        roles = parse_roles_from_text(candidate["resume_text"])
        
        narrative = compute_narrative_coherence(candidate["resume_text"], roles)
        portfolio = compute_team_portfolio(candidate["resume_text"], roles)
        artifact = compute_artifact_complexity(candidate["resume_text"], roles)
        
        results.append({
            "resume_id": candidate["resume_id"],
            "narrative_coherence_score": narrative["narrative_coherence_score"],
            "team_portfolio_score": portfolio["team_portfolio_score"],
            "artifact_complexity_score": artifact["artifact_complexity_score"],
            "reasons": (
                narrative["reasons"][:1] +
                portfolio["reasons"][:1] +
                artifact["reasons"][:1]
            ),
        })
    return results


def process_chunk_tier3(chunk: list[dict]) -> list[dict]:
    """Process Tier 3 deep analysis dimensions for a chunk of candidates."""
    results = []
    for candidate in chunk:
        from app.services.career_trajectory.extractor import parse_roles_from_text
        roles = parse_roles_from_text(candidate["resume_text"])
        
        career = compute_career_trajectory(candidate["resume_text"], roles)
        counterfactual = compute_counterfactual(candidate["resume_text"], roles)
        
        results.append({
            "resume_id": candidate["resume_id"],
            "career_growth_score": career["career_growth_score"],
            "counterfactual_score": counterfactual["counterfactual_score"],
            "career_reasons": career["reasons"],
            "counterfactual_reasons": counterfactual["reasons"],
        })
    return results


def _run_parallel_tier2(candidates: list[dict], num_workers: int) -> list[dict]:
    """Run Tier 2 processing in parallel with progress tracking."""
    if num_workers <= 1:
        signals_list = []
        total = len(candidates)
        for i, candidate in enumerate(candidates):
            if i % 1000 == 0 and i > 0:
                print(f"  Tier 2 progress: {i:,}/{total:,} ({i/total*100:.1f}%)")
            from app.services.career_trajectory.extractor import parse_roles_from_text
            roles = parse_roles_from_text(candidate["resume_text"])
            
            narrative = compute_narrative_coherence(candidate["resume_text"], roles)
            portfolio = compute_team_portfolio(candidate["resume_text"], roles)
            artifact = compute_artifact_complexity(candidate["resume_text"], roles)
            
            signals_list.append({
                "narrative_coherence_score": narrative["narrative_coherence_score"],
                "team_portfolio_score": portfolio["team_portfolio_score"],
                "artifact_complexity_score": artifact["artifact_complexity_score"],
                "reasons": (
                    narrative["reasons"][:1] +
                    portfolio["reasons"][:1] +
                    artifact["reasons"][:1]
                ),
            })
        return signals_list

    chunks = _chunk_records(candidates, num_workers)
    all_results = [None] * len(candidates)
    completed_chunks = 0
    total_chunks = len(chunks)

    print(f"  Processing {len(candidates):,} candidates in {total_chunks} chunks...")
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(process_chunk_tier2, chunk): i for i, chunk in enumerate(chunks)}
        for future in as_completed(futures):
            chunk_idx = futures[future]
            try:
                chunk_results = future.result()
                start_idx = chunk_idx * max(1, len(candidates) // num_workers)
                for j, result in enumerate(chunk_results):
                    all_results[start_idx + j] = result
                completed_chunks += 1
                if completed_chunks % max(1, total_chunks // 4) == 0:
                    print(f"  Progress: {completed_chunks}/{total_chunks} chunks ({completed_chunks/total_chunks*100:.0f}%)")
            except Exception as e:
                print(f"  Warning: Chunk {chunk_idx} failed with error: {e}")
                # Fill with neutral scores for failed chunk
                for j in range(len(chunks[chunk_idx])):
                    all_results[start_idx + j] = {
                        "narrative_coherence_score": 65.0,
                        "team_portfolio_score": 65.0,
                        "artifact_complexity_score": 65.0,
                        "reasons": ["Error in processing"],
                    }

    return [
        {k: v for k, v in r.items() if k not in ("resume_id",)}
        for r in all_results if r is not None
    ]


def _run_parallel_tier3(candidates: list[dict], num_workers: int) -> list[dict]:
    """Run Tier 3 processing in parallel with progress tracking."""
    if num_workers <= 1:
        signals_list = []
        total = len(candidates)
        for i, candidate in enumerate(candidates):
            if i % 500 == 0 and i > 0:
                print(f"  Tier 3 progress: {i:,}/{total:,} ({i/total*100:.1f}%)")
            from app.services.career_trajectory.extractor import parse_roles_from_text
            roles = parse_roles_from_text(candidate["resume_text"])
            
            career = compute_career_trajectory(candidate["resume_text"], roles)
            counterfactual = compute_counterfactual(candidate["resume_text"], roles)
            
            signals_list.append({
                "career_growth_score": career["career_growth_score"],
                "counterfactual_score": counterfactual["counterfactual_score"],
                "career_reasons": career["reasons"],
                "counterfactual_reasons": counterfactual["reasons"],
            })
        return signals_list

    chunks = _chunk_records(candidates, num_workers)
    all_results = [None] * len(candidates)
    completed_chunks = 0
    total_chunks = len(chunks)

    print(f"  Processing {len(candidates):,} candidates in {total_chunks} chunks...")
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(process_chunk_tier3, chunk): i for i, chunk in enumerate(chunks)}
        for future in as_completed(futures):
            chunk_idx = futures[future]
            try:
                chunk_results = future.result()
                start_idx = chunk_idx * max(1, len(candidates) // num_workers)
                for j, result in enumerate(chunk_results):
                    all_results[start_idx + j] = result
                completed_chunks += 1
                if completed_chunks % max(1, total_chunks // 4) == 0:
                    print(f"  Progress: {completed_chunks}/{total_chunks} chunks ({completed_chunks/total_chunks*100:.0f}%)")
            except Exception as e:
                print(f"  Warning: Chunk {chunk_idx} failed with error: {e}")
                # Fill with neutral scores for failed chunk
                for j in range(len(chunks[chunk_idx])):
                    all_results[start_idx + j] = {
                        "career_growth_score": 65.0,
                        "counterfactual_score": 65.0,
                        "career_reasons": ["Error in processing"],
                        "counterfactual_reasons": [],
                    }

    return [
        {k: v for k, v in r.items() if k not in ("resume_id",)}
        for r in all_results if r is not None
    ]
