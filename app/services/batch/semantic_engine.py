import numpy as np
from scipy.sparse import csr_matrix, vstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import joblib
import os


class BatchSemanticEngine:
    def __init__(self, n_components: int = 128, max_features: int = 10000):
        self.n_components = n_components
        self.max_features = max_features
        self.vectorizer: TfidfVectorizer | None = None
        self.svd: TruncatedSVD | None = None
        self._fitted = False

    def fit(self, texts: list[str]):
        self.vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            stop_words="english",
            sublinear_tf=True,
            norm="l2",
        )
        tfidf_matrix = self.vectorizer.fit_transform(texts)

        self.svd = TruncatedSVD(
            n_components=min(self.n_components, tfidf_matrix.shape[1] - 1),
            random_state=42,
        )
        self.svd.fit(tfidf_matrix)
        self._fitted = True

    def transform(self, texts: list[str]) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Engine not fitted. Call fit() first.")
        tfidf = self.vectorizer.transform(texts)
        dense = self.svd.transform(tfidf)
        norms = np.linalg.norm(dense, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return dense / norms

    def transform_one(self, text: str) -> np.ndarray:
        return self.transform([text])[0]

    def similarity(self, query_vec: np.ndarray, corpus_mat: np.ndarray) -> np.ndarray:
        return np.dot(corpus_mat, query_vec)

    def fit_transform(self, texts: list[str]) -> np.ndarray:
        self.vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            stop_words="english",
            sublinear_tf=True,
            norm="l2",
        )
        tfidf_matrix = self.vectorizer.fit_transform(texts)

        n = min(self.n_components, tfidf_matrix.shape[1] - 1)
        self.svd = TruncatedSVD(n_components=n, random_state=42)
        dense = self.svd.fit_transform(tfidf_matrix)
        norms = np.linalg.norm(dense, axis=1, keepdims=True)
        norms[norms == 0] = 1
        self._fitted = True
        return dense / norms

    def save(self, directory: str):
        os.makedirs(directory, exist_ok=True)
        joblib.dump(self.vectorizer, os.path.join(directory, "vectorizer.joblib"))
        joblib.dump(self.svd, os.path.join(directory, "svd.joblib"))
        np.save(os.path.join(directory, "n_components.npy"), np.array([self.n_components]))
        np.save(os.path.join(directory, "max_features.npy"), np.array([self.max_features]))

    @classmethod
    def load(cls, directory: str):
        instance = cls()
        instance.vectorizer = joblib.load(os.path.join(directory, "vectorizer.joblib"))
        instance.svd = joblib.load(os.path.join(directory, "svd.joblib"))
        instance.n_components = int(np.load(os.path.join(directory, "n_components.npy"))[0])
        instance.max_features = int(np.load(os.path.join(directory, "max_features.npy"))[0])
        instance._fitted = True
        return instance
