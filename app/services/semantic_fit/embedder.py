from sentence_transformers import SentenceTransformer
from app.core.config import settings
import numpy as np

# Singleton — model loads once at startup
_model: SentenceTransformer | None = None

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.MODEL_NAME)
    return _model

def embed(texts: list[str]) -> np.ndarray:
    """
    Returns L2-normalized embeddings.
    Normalization ensures cosine similarity = dot product (faster).
    """
    model = get_model()
    embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return embeddings