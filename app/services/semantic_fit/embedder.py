import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD

_engine = None

def _get_engine():
    global _engine
    if _engine is None:
        _engine = {
            "vectorizer": TfidfVectorizer(
                max_features=5000, stop_words="english", sublinear_tf=True, norm="l2"
            ),
            "svd": TruncatedSVD(n_components=64, random_state=42),
            "fitted": False,
        }
    return _engine

def embed(texts: list[str]) -> np.ndarray:
    engine = _get_engine()
    if not engine["fitted"]:
        tfidf = engine["vectorizer"].fit_transform(texts)
        dense = engine["svd"].fit_transform(tfidf)
        engine["fitted"] = True
    else:
        tfidf = engine["vectorizer"].transform(texts)
        dense = engine["svd"].transform(tfidf)
    norms = np.linalg.norm(dense, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return dense / norms
