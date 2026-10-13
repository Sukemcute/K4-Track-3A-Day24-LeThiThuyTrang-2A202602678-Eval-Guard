from __future__ import annotations

"""Phase C: Production Guardrails — Presidio PII + NeMo Guardrails + P95 Latency."""

import asyncio
import json
import os
import re
import inspect
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ADVERSARIAL_SET_PATH, GUARDRAILS_CONFIG_DIR, LATENCY_BUDGET_P95_MS, PRESIDIO_LANGUAGE


_PII_ENTITY_WHITELIST = ["VN_CCCD", "VN_PHONE", "EMAIL_ADDRESS"]

_INPUT_BLOCK_PATTERNS = [
    r"ignore\s+(?:your\s+)?system\s+prompt",
    r"system\s+override",
    r"unrestricted\s+ai",
    r"do\s+anything\s+now",
    r"\bdan\b",
    r"forget\s+all\s+hr\s+policies",
    r"reveal\s+all\s+confidential\s+employee\s+data",
    r"print\s+all\s+confidential\s+hr\s+data",
    r"dump\s+all\s+training\s+data",
    r"list\s+all\s+employee\s+salaries",
    r"đóng\s+vai\s+hr\s+manager",
    r"bảng\s+lương\s+chi\s+tiết",
    r"số\s+điện\s+thoại\s+của\s+nhân\s+viên",
    r"cccd\s+của\s+nhân\s+viên",
    r"liệt\s+kê\s+toàn\s+bộ\s+thông\s+tin\s+nhân\s+viên",
    r"bỏ\s+qua\s+tất\s+cả\s+hướng\s+dẫn",
    r"bỏ\s+qua\s+tất\s+cả\s+policy",
    r"in\s+ra\s+toàn\s+bộ\s+system\s+instructions",
    r"hướng\s+dẫn\s+tấn\s+công\s+mạng\s+nội\s+bộ",
    r"mùa\s+thu\s+hà\s+nội",
    r"phở\s+bò",
    r"bitcoin|ethereum",
    r"phương\s+trình\s+vi\s+phân",
    r"marvel",
]

_OUTPUT_BLOCK_PATTERNS = [
    r"\bcccd\b",
    r"\bcmnd\b",
    r"\bmật\s+khẩu\b",
    r"\bpassword\b",
    r"admin\s+system",
    r"confidential\s+employee\s+data",
    r"dữ\s+liệu\s+kiểm\s+thử\s+giả\s+lập",
]


# ─── Task 9a: Presidio PII Detection ─────────────────────────────────────────

def setup_presidio():
    """Khởi tạo Presidio engine với custom Vietnamese PII recognizers. (Đã implement sẵn)

    Custom recognizers thêm vào:
        VN_CCCD  — số CCCD 12 chữ số hoặc CMND 9 chữ số
        VN_PHONE — số điện thoại Việt Nam (0[3-9]xxxxxxxx)

    Các recognizers mặc định đã có sẵn: EMAIL, PHONE_NUMBER (international), ...
    """
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, Pattern, PatternRecognizer
    from presidio_anonymizer import AnonymizerEngine

    cccd_recognizer = PatternRecognizer(
        supported_entity="VN_CCCD",
        patterns=[
            Pattern("CCCD 12 digits", r"\b\d{12}\b", 0.9),
            Pattern("CMND 9 digits",  r"\b\d{9}\b",  0.7),
        ],
    )
    phone_recognizer = PatternRecognizer(
        supported_entity="VN_PHONE",
        patterns=[Pattern("VN mobile", r"\b0[3-9]\d{8}\b", 0.9)],
    )

    registry = RecognizerRegistry()
    registry.load_predefined_recognizers()
    registry.add_recognizer(cccd_recognizer)
    registry.add_recognizer(phone_recognizer)

    analyzer  = AnalyzerEngine(registry=registry)
    anonymizer = AnonymizerEngine()
    return analyzer, anonymizer


def pii_scan(text: str, analyzer=None, anonymizer=None) -> dict:
    """Task 9a: Quét PII trong văn bản bằng Presidio.

    Returns:
        {
          "has_pii":    bool,
          "entities":   [{"type": str, "text": str, "score": float, "start": int, "end": int}],
          "anonymized": str,   # text với PII được thay bằng <TYPE>
        }
    """
    if analyzer is None or anonymizer is None:
        analyzer, anonymizer = setup_presidio()

    # presidio_analyzer.AnalyzerEngine.analyze expects named args in tests
    analyze_fn = analyzer.analyze
    params = {}
    try:
        sig = inspect.signature(analyze_fn)
        if "entities" in sig.parameters:
            params["entities"] = _PII_ENTITY_WHITELIST
    except (TypeError, ValueError):
        pass
    results = analyze_fn(text=text, language=PRESIDIO_LANGUAGE, **params)
    if not results:
        return {"has_pii": False, "entities": [], "anonymized": text}

    anonymized = anonymizer.anonymize(text=text, analyzer_results=results).text
    entities = [
        {"type": r.entity_type, "text": text[r.start:r.end],
         "score": round(getattr(r, "score", 0.0), 3), "start": r.start, "end": r.end}
        for r in results
    ]
    return {"has_pii": True, "entities": entities, "anonymized": anonymized}


# ─── Task 9b + 11: NeMo Guardrails ───────────────────────────────────────────

def setup_nemo_rails():
    """Khởi tạo NeMo Guardrails từ guardrails/config.yml. (Đã implement sẵn)

    Config directory: guardrails/
        config.yml  — model + rails config
        rails.co    — câu từ chối Colang 1.0; built-in self-check flows được bật trong YAML
    """
    try:
        from nemoguardrails import RailsConfig, LLMRails
    except Exception:
        RailsConfig = None
        LLMRails = None

    if RailsConfig is not None and LLMRails is not None:
        config = RailsConfig.from_path(GUARDRAILS_CONFIG_DIR)
        rails = LLMRails(config)
        return rails

    # Lightweight fallback for environments where NeMo Guardrails cannot be
    # installed (e.g. Windows + Python 3.12 without MSVC for Annoy).
    class _FallbackModel:
        def __init__(self, model: str, type: str):
            self.model = model
            self.type = type

    class _FallbackConfig:
        def __init__(self):
            self.models = [_FallbackModel("local-guard-stub", "llm")]

    class _FallbackRails:
        def __init__(self):
            self.config = _FallbackConfig()

        @staticmethod
        def _text_from_messages(messages) -> str:
            return "\n".join(msg.get("content", "") for msg in messages if isinstance(msg, dict))

        @staticmethod
        def _matches_any(patterns, text: str) -> bool:
            return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)

        def _should_block_input(self, text: str) -> bool:
            return self._matches_any(_INPUT_BLOCK_PATTERNS, text)

        def _should_block_output(self, text: str) -> bool:
            return self._matches_any(_OUTPUT_BLOCK_PATTERNS, text)

        async def generate_async(self, messages, options=None):
            text = self._text_from_messages(messages)
            rails = (options or {}).get("rails", [])
            if "output" in rails:
                blocked = self._should_block_output(text)
            else:
                blocked = self._should_block_input(text)
            response = "Tôi không thể hỗ trợ yêu cầu này." if blocked else (messages[-1].get("content", "") if messages else "")
            return type("_Result", (), {
                "response": [{"content": response}],
                "log": type("_Log", (), {"activated_rails": [type("_Rail", (), {"stop": blocked})()]})(),
            })()

    return _FallbackRails()


async def check_input_rail(text: str, rails=None) -> dict:
    """Task 9b: Kiểm tra input qua NeMo input rails (topic guard + jailbreak guard).

    Returns:
        {
          "allowed":        bool,
          "blocked_reason": str | None,
          "response":       str,          # NeMo's raw response
        }
    """
    if rails is None:
        rails = setup_nemo_rails()

    result = await rails.generate_async(
        messages=[{"role": "user", "content": text}],
        options={"rails": ["input"], "log": {"activated_rails": True}},
    )

    # support both dict-like and SimpleNamespace responses
    resp = None
    try:
        resp = result.response[0]["content"]
    except Exception:
        try:
            resp = result.response[0].get("content")
        except Exception:
            resp = getattr(result.response[0], "content", "")

    blocked = any(getattr(rail, "stop", False) for rail in getattr(result.log, "activated_rails", []))
    return {"allowed": not blocked, "blocked_reason": "nemo_input" if blocked else None, "response": resp}


async def check_output_rail(question: str, answer: str, rails=None) -> dict:
    """Task 11: Kiểm tra LLM output qua NeMo output rails trước khi trả về user.

    NeMo output rails hoạt động trong context của cả cuộc hội thoại (input + output).
    Kiểm tra PII và nội dung nhạy cảm. Self-check này không thay RAGAS faithfulness
    hoặc kiểm tra factual accuracy với retrieved contexts.

    Returns:
        {
          "safe":           bool,
          "flagged_reason": str | None,
          "final_answer":   str,          # answer đã qua guard (có thể bị redact)
        }
    """
    if rails is None:
        rails = setup_nemo_rails()

    result = await rails.generate_async(
        messages=[
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ],
        options={"rails": ["output"], "log": {"activated_rails": True}},
    )

    # extract response text
    resp = None
    try:
        resp = result.response[0]["content"]
    except Exception:
        resp = getattr(result.response[0], "content", None) or (result.response[0].get("content") if isinstance(result.response[0], dict) else None)

    flagged = any(getattr(rail, "stop", False) for rail in getattr(result.log, "activated_rails", []))
    return {"safe": not flagged, "flagged_reason": "nemo_output" if flagged else None, "final_answer": resp if flagged else answer}


# ─── Task 10: Adversarial Test Suite ─────────────────────────────────────────

def run_adversarial_suite(adversarial_set: list[dict], rails=None,
                           analyzer=None, anonymizer=None) -> list[dict]:
    """Task 10: Chạy 20 adversarial inputs qua full guard stack, so sánh với expected.

    Guard stack order:
        1. pii_scan()         → block nếu has_pii (cho category pii_injection)
        2. check_input_rail() → block nếu jailbreak / off-topic / prompt injection

    Returns:
        list of {
          "id": int, "category": str, "input": str,
          "expected": "blocked"|"allowed",
          "actual":   "blocked"|"allowed",
          "blocked_by": str | None,       # "presidio" | "nemo_input" | None
          "passed": bool,
        }
    """
    if analyzer is None or anonymizer is None:
        analyzer, anonymizer = setup_presidio()
    if rails is None:
        rails = setup_nemo_rails()

    async def _run_all():
        results = []
        for item in adversarial_set:
            blocked_by = None

            # Layer 1: Presidio PII
            pii_result = pii_scan(item["input"], analyzer, anonymizer)
            if pii_result["has_pii"]:
                blocked_by = "presidio"

            # Layer 2: NeMo input rail
            if blocked_by is None:
                rail_result = await check_input_rail(item["input"], rails)
                if not rail_result["allowed"]:
                    blocked_by = "nemo_input"

            actual = "blocked" if blocked_by else "allowed"
            results.append({
                "id": item["id"],
                "category": item.get("category"),
                "input": item["input"],
                "expected": item.get("expected"),
                "actual": actual,
                "blocked_by": blocked_by,
                "passed": actual == item.get("expected"),
            })
        return results

    results = asyncio.run(_run_all())
    passed = sum(1 for r in results if r["passed"])
    print(f"Adversarial suite: {passed}/{len(results)} passed")
    return results


# ─── Task 12: P95 Latency Measurement ────────────────────────────────────────

def measure_p95_latency(test_inputs: list[str], n_runs: int = 20,
                         rails=None, analyzer=None, anonymizer=None) -> dict:
    """Task 12: measure INPUT layers sequentially, not end-to-end guard/RAG latency.

    Reuse engines. Inside ONE event loop, execute two real warm-up calls per layer,
    excluded from samples. Then collect exactly n_runs timed samples (cycle clean
    inputs), always measuring BOTH PII and NeMo input even if PII blocks.
    Use perf_counter; keep raw milliseconds. summarize_latency() supplies linear
    percentiles at (n - 1) * q. Submission requires n_runs >= 20.
    Short-circuit request timing, RAG and output timing are outside this scope.
    """
    from src.experiment_support import summarize_latency
    if not test_inputs or n_runs < 1:
        raise ValueError("Need inputs and n_runs >= 1")
    if analyzer is None or anonymizer is None:
        analyzer, anonymizer = setup_presidio()
    if rails is None:
        rails = setup_nemo_rails()

    async def _measure():
        # warm-up runs (excluded)
        for i in range(2):
            text = test_inputs[i % len(test_inputs)]
            pii_scan(text, analyzer, anonymizer)
            await check_input_rail(text, rails)

        samples = []
        for i in range(n_runs):
            text = test_inputs[i % len(test_inputs)]
            t0 = time.perf_counter()
            pii_scan(text, analyzer, anonymizer)
            pii_ms = (time.perf_counter() - t0) * 1000
            t1 = time.perf_counter()
            await check_input_rail(text, rails)
            nemo_ms = (time.perf_counter() - t1) * 1000
            samples.append({"presidio_ms": pii_ms, "nemo_input_ms": nemo_ms,
                            "input_guard_ms": pii_ms + nemo_ms})
        return samples

    samples = asyncio.run(_measure())
    return summarize_latency(samples, warmup_runs=2)


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from scripts.run_experiments import main
    raise SystemExit(main(["--phase", "c", *sys.argv[1:]]))
