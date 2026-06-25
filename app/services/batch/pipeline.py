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
