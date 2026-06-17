import numpy as np
from app.services.semantic_fit.embedder import embed

def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Since embeddings are L2-normalized, dot product == cosine similarity.
    Returns value between -1 and 1.
    """
    return float(np.dot(vec_a, vec_b))

def compute_section_similarities(
    resume_sections: dict[str, str],
    jd_sections: dict[str, str],
) -> dict[str, float]:
    """
    Match each resume section against the corresponding JD section.
    Falls back to 'full' if section missing in JD.
    """
    results = {}
    jd_full_embedding = embed([jd_sections.get("full", "")])[0]

    for section, resume_text in resume_sections.items():
        if not resume_text.strip():
            continue
        jd_text = jd_sections.get(section, jd_sections.get("full", ""))
        resume_emb = embed([resume_text])[0]
        jd_emb = embed([jd_text])[0]
        results[section] = cosine_similarity(resume_emb, jd_emb)

    return results