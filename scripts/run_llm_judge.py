#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JSON_OBJECT_RE = re.compile(r"\{.*\}", re.S)


def main() -> int:
    args = parse_args()
    input_path = resolve_path(args.input_jsonl)
    output_path = resolve_path(args.output_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    done = load_done(output_path, args.mode) if args.resume else set()
    requests = read_jsonl(input_path)
    if args.limit:
        requests = requests[: args.limit]

    written = 0
    skipped = 0
    failed = 0
    with output_path.open("a", encoding="utf-8") as out:
        for index, request in enumerate(requests, 1):
            key = request_key(request, args.mode)
            if key in done:
                skipped += 1
                continue
            try:
                result = run_one(request, args)
            except Exception as exc:  # noqa: BLE001 - CLI should keep going and report per-row failures.
                failed += 1
                result = failure_result(request, args.mode, str(exc))
            out.write(json.dumps(result, ensure_ascii=False) + "\n")
            out.flush()
            written += 1
            if args.sleep_sec:
                time.sleep(args.sleep_sec)
            if written % args.progress_every == 0:
                print(f"[judge] processed={index} written={written} skipped={skipped} failed={failed}", flush=True)

    print(f"[judge] input: {input_path}")
    print(f"[judge] output: {output_path}")
    print(f"[judge] written: {written}")
    print(f"[judge] skipped: {skipped}")
    print(f"[judge] failed: {failed}")
    return 0 if failed == 0 or args.allow_failures else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LLM judge requests against an OpenAI-compatible chat endpoint.")
    parser.add_argument("--mode", choices=["semantic", "pairwise"], required=True)
    parser.add_argument("--input-jsonl", required=True)
    parser.add_argument("--output-jsonl", required=True)
    parser.add_argument("--api-base", default="http://127.0.0.1:8001/v1")
    parser.add_argument("--model", default="qwen3-coder-30b-a3b")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--timeout-sec", type=int, default=180)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--sleep-sec", type=float, default=0.0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--progress-every", type=int, default=10)
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--allow-failures", action="store_true")
    return parser.parse_args()


def run_one(request: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    content = call_chat_completion(
        api_base=args.api_base,
        model=args.model,
        prompt=str(request["prompt"]),
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        timeout_sec=args.timeout_sec,
        retries=args.retries,
    )
    parsed = extract_json_object(content)
    if args.mode == "semantic":
        return semantic_result(request, parsed, content)
    return pairwise_result(request, parsed, content)


def call_chat_completion(
    *,
    api_base: str,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    timeout_sec: int,
    retries: int,
) -> str:
    url = api_base.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a strict code-repair judge. Return exactly one JSON object and no markdown.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    data = json.dumps(payload).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as response:
                obj = json.loads(response.read().decode("utf-8"))
            return str(obj["choices"][0]["message"]["content"])
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(min(8, 2**attempt))
    raise RuntimeError(f"chat completion failed: {last_error}")


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = JSON_OBJECT_RE.search(stripped)
        if not match:
            raise ValueError(f"No JSON object found in model output: {stripped[:200]}")
        return json.loads(match.group(0))


def semantic_result(request: dict[str, Any], parsed: dict[str, Any], raw: str) -> dict[str, Any]:
    return {
        "task_id": request["task_id"],
        "candidate_index": int(request["candidate_index"]),
        "fixes_root_cause": clamp_int(parsed.get("fixes_root_cause"), 0, 5),
        "minimal_and_targeted": clamp_int(parsed.get("minimal_and_targeted"), 0, 5),
        "risk_of_regression": clamp_int(parsed.get("risk_of_regression"), 0, 5),
        "test_relevance": clamp_int(parsed.get("test_relevance"), 0, 5),
        "reason": str(parsed.get("reason", ""))[:1000],
        "raw_response": raw[:2000],
    }


def pairwise_result(request: dict[str, Any], parsed: dict[str, Any], raw: str) -> dict[str, Any]:
    winner = str(parsed.get("winner", "")).strip().upper()
    if winner not in {"A", "B", "TIE"}:
        winner = "TIE"
    return {
        "task_id": request["task_id"],
        "candidate_a": int(request["candidate_a"]),
        "candidate_b": int(request["candidate_b"]),
        "winner": winner,
        "confidence": clamp_float(parsed.get("confidence"), 0.0, 1.0),
        "reason": str(parsed.get("reason", ""))[:1000],
        "raw_response": raw[:2000],
    }


def failure_result(request: dict[str, Any], mode: str, error: str) -> dict[str, Any]:
    if mode == "semantic":
        return {
            "task_id": request.get("task_id", ""),
            "candidate_index": int(request.get("candidate_index", -1)),
            "fixes_root_cause": 0,
            "minimal_and_targeted": 0,
            "risk_of_regression": 5,
            "test_relevance": 0,
            "reason": f"judge_failed: {error}",
            "judge_error": error,
        }
    return {
        "task_id": request.get("task_id", ""),
        "candidate_a": int(request.get("candidate_a", -1)),
        "candidate_b": int(request.get("candidate_b", -1)),
        "winner": "TIE",
        "confidence": 0.0,
        "reason": f"judge_failed: {error}",
        "judge_error": error,
    }


def load_done(path: Path, mode: str) -> set[tuple[Any, ...]]:
    done = set()
    if not path.exists():
        return done
    for row in read_jsonl(path):
        done.add(request_key(row, mode))
    return done


def request_key(row: dict[str, Any], mode: str) -> tuple[Any, ...]:
    if mode == "semantic":
        return (str(row["task_id"]), int(row["candidate_index"]))
    return (str(row["task_id"]), int(row["candidate_a"]), int(row["candidate_b"]))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def clamp_int(value: Any, low: int, high: int) -> int:
    try:
        parsed = int(round(float(value)))
    except (TypeError, ValueError):
        parsed = low
    return max(low, min(high, parsed))


def clamp_float(value: Any, low: float, high: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = low
    return round(max(low, min(high, parsed)), 4)


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


if __name__ == "__main__":
    raise SystemExit(main())
