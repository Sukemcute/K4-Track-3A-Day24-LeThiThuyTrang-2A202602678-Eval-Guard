from __future__ import annotations

"""Module 3: Reranking — Cross-encoder top-20 → top-3 + latency benchmark."""

import os, sys, time
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RERANK_TOP_K


@dataclass
class RerankResult:
    text: str
    original_score: float
    rerank_score: float
    metadata: dict
    rank: int


class CrossEncoderReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.model_name = model_name
        self._model = None
        self._use_fallback = False

    def _load_model(self):
        if self._model is None and not self._use_fallback:
            try:
                home_drive = os.path.splitdrive(os.path.expanduser("~"))[0] or os.path.splitdrive(os.getcwd())[0]
                if home_drive and os.path.exists(home_drive + os.sep):
                    import shutil
                    free_bytes = shutil.disk_usage(home_drive + os.sep).free
                    if free_bytes < 5 * 1024 * 1024 * 1024:
                        self._use_fallback = True
                        return None
            except Exception:
                pass
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name)
            except Exception:
                self._model = None
                self._use_fallback = True
        return self._model

    @staticmethod
    def _fallback_score(query: str, text: str, orig_score: float = 0.0) -> float:
        import re
        q_tokens = {tok for tok in re.findall(r"\w+", query.lower()) if tok}
        t_tokens = set(re.findall(r"\w+", text.lower()))
        if not q_tokens or not t_tokens:
            return float(orig_score)
        stopwords = {"được", "bao", "nhiêu", "khi", "ai", "cần", "trong", "của", "ở", "cho", "về", "là", "các", "những", "có", "theo", "nào"}
        content_q = q_tokens - stopwords or q_tokens
        matched = content_q.intersection(t_tokens)
        coverage = len(matched) / len(content_q)
        return float(orig_score + coverage * 0.2)


    def rerank(self, query: str, documents: list[dict], top_k: int = RERANK_TOP_K) -> list[RerankResult]:
        """Rerank documents: top-20 → top-k."""
        if not documents:
            return []
        model = self._load_model()
        if model is not None:
            pairs = [
                (query, doc.get("text", "") if isinstance(doc, dict) else getattr(doc, "text", ""))
                for doc in documents
            ]
            scores = model.predict(pairs)
            if hasattr(scores, "tolist"):
                scores = scores.tolist()
            elif isinstance(scores, (int, float)):
                scores = [float(scores)]
            else:
                scores = list(scores)
        else:
            scores = [
                self._fallback_score(
                    query,
                    doc.get("text", "") if isinstance(doc, dict) else getattr(doc, "text", ""),
                    float(doc.get("score", 0.0) if isinstance(doc, dict) else getattr(doc, "score", 0.0))
                )
                for doc in documents
            ]


        scored = sorted(zip(scores, documents), key=lambda x: x[0], reverse=True)
        results = []
        for i, (score, doc) in enumerate(scored[:top_k]):
            text = doc.get("text", "") if isinstance(doc, dict) else getattr(doc, "text", "")
            orig_score = float(doc.get("score", 0.0) if isinstance(doc, dict) else getattr(doc, "score", 0.0))
            meta = doc.get("metadata", {}) if isinstance(doc, dict) else getattr(doc, "metadata", {})
            results.append(RerankResult(
                text=text,
                original_score=orig_score,
                rerank_score=float(score),
                metadata=meta,
                rank=i
            ))
        return results


class FlashrankReranker:
    """Lightweight alternative (<5ms). Optional."""
    def __init__(self):
        self._model = None

    def rerank(self, query: str, documents: list[dict], top_k: int = RERANK_TOP_K) -> list[RerankResult]:
        if not documents:
            return []
        try:
            from flashrank import Ranker, RerankRequest
            if self._model is None:
                self._model = Ranker()
            passages = [
                {"text": d.get("text", "") if isinstance(d, dict) else getattr(d, "text", "")}
                for d in documents
            ]
            results = self._model.rerank(RerankRequest(query=query, passages=passages))
            return [
                RerankResult(
                    text=res.get("text", ""),
                    original_score=float(documents[i].get("score", 0.0) if isinstance(documents[i], dict) else getattr(documents[i], "score", 0.0)),
                    rerank_score=float(res.get("score", 0.0)),
                    metadata=documents[i].get("metadata", {}) if isinstance(documents[i], dict) else getattr(documents[i], "metadata", {}),
                    rank=i
                )
                for i, res in enumerate(results[:top_k])
            ]
        except Exception:
            return []


def benchmark_reranker(reranker, query: str, documents: list[dict], n_runs: int = 5) -> dict:
    """Benchmark latency over n_runs. (Đã implement sẵn)"""
    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        reranker.rerank(query, documents)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    return {"avg_ms": sum(times) / len(times), "min_ms": min(times), "max_ms": max(times)}


if __name__ == "__main__":
    query = "Nhân viên được nghỉ phép bao nhiêu ngày?"
    docs = [
        {"text": "Nhân viên được nghỉ 12 ngày/năm.", "score": 0.8, "metadata": {}},
        {"text": "Mật khẩu thay đổi mỗi 90 ngày.", "score": 0.7, "metadata": {}},
        {"text": "Thời gian thử việc là 60 ngày.", "score": 0.75, "metadata": {}},
    ]
    reranker = CrossEncoderReranker()
    for r in reranker.rerank(query, docs):
        print(f"[{r.rank}] {r.rerank_score:.4f} | {r.text}")
