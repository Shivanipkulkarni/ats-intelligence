import os
import json
import time
import numpy as np

from app.services.batch.semantic_engine import BatchSemanticEngine
from app.services.batch.pipeline import (
    load_resumes,
    compute_heuristic_signals,
    compute_overall_score,
    DIMENSION_WEIGHTS,
)
from app.services.bias_mirror.scorer import (
    compute_keyword_match_resume_jd,
    compute_bias_comparison,
)


def screen_from_cache(
    cache_dir: str,
    job_description: str,
    resume_dir: str,
    top_k: int = 100,
    weights: dict[str, float] | None = None,
) -> dict:
    start = time.time()

    print(f"Loading semantic engine from {cache_dir}...")
    engine = BatchSemanticEngine.load(cache_dir)
    print("Loaded.")

    print(f"Loading resumes from {resume_dir}...")
    records = load_resumes(resume_dir)
    texts = [r["resume_text"] for r in records]
    n = len(records)
    print(f"Loaded {n} resumes.")

    jd_vec = engine.transform_one(job_description)

    cache_matrix_path = os.path.join(cache_dir, "lsa_matrix.npy")
    if os.path.exists(cache_matrix_path):
        lsa_matrix = np.load(cache_matrix_path)
        semantic_scores = engine.similarity(jd_vec, lsa_matrix)
    else:
        lsa_matrix = engine.transform(texts)
        np.save(cache_matrix_path, lsa_matrix)
        semantic_scores = engine.similarity(jd_vec, lsa_matrix)

    raw_scores = ((semantic_scores + 1) / 2) * 100

    print("Computing keyword match scores...")
    kw_scores = []
    for r in records:
        kw_result = compute_keyword_match_resume_jd(r["resume_text"], job_description)
        kw_scores.append(kw_result["keyword_match_score"])

    cache_signals_path = os.path.join(cache_dir, "signals_cache.json")
    if os.path.exists(cache_signals_path):
        print("Loading cached heuristic signals...")
        with open(cache_signals_path, "r", encoding="utf-8") as f:
            cached_signals = json.load(f)
        signals_list = [cached_signals.get(r["resume_id"], compute_heuristic_signals(r["resume_text"])) for r in records]
    else:
        print("Computing heuristic signals...")
        signals_list = [compute_heuristic_signals(r["resume_text"]) for r in records]
        if cache_dir:
            cache_data = {records[i]["resume_id"]: s for i, s in enumerate(signals_list)}
            with open(cache_signals_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f)

    print("Ranking candidates...")
    all_results = []
    for i in range(n):
        sem_score = round(float(raw_scores[i]), 2)
        signals = signals_list[i]
        overall = compute_overall_score(
            signals | {"semantic_fit_score": sem_score},
            sem_score,
            weights,
        )
        all_results.append({
            "resume_id": records[i]["resume_id"],
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
                "keyword_match": round(kw_scores[i], 2),
            },
            "reasons": signals["reasons"],
        })

    all_results.sort(key=lambda x: x["overall_score"], reverse=True)
    top = all_results[:top_k]

    kw_ranked = sorted(
        [
            {"resume_id": records[i]["resume_id"], "overall_score": round(kw_scores[i], 2)}
            for i in range(n)
        ],
        key=lambda x: x["overall_score"],
        reverse=True,
    )
    kw_top = kw_ranked[:top_k]
    bias = compute_bias_comparison(top, kw_top, top_k)

    elapsed = round(time.time() - start, 2)
    print(f"\nTotal elapsed: {elapsed:.2f}s for {n} resumes (cached).")

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
            for i, r in enumerate(kw_top)
        ],
        "bias_comparison": bias,
    }
