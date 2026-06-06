"""Build a lightweight self-contained Python/JavaScript repair benchmark."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from env.task_loader import load_yaml


PY_ASSERT_HEADER = ""
JS_ASSERT_HEADER = "const assert = require('assert');\nconst lib = require('./buggy_code');\n"


TASK_TEMPLATES = [
    {
        "task_id": "bench_py_001",
        "language": "python",
        "bug_type": "off_by_one",
        "issue": "sum_to_n should include the upper bound when summing 1..n.",
        "source": "def sum_to_n(n):\n    return sum(range(1, n))\n",
        "visible": "from buggy_code import sum_to_n\n\ndef test_visible():\n    assert sum_to_n(3) == 6\n",
        "hidden": "from buggy_code import sum_to_n\n\ndef test_hidden():\n    assert sum_to_n(1) == 1\n    assert sum_to_n(5) == 15\n",
    },
    {
        "task_id": "bench_py_002",
        "language": "python",
        "bug_type": "division_by_zero",
        "issue": "safe_average should return 0.0 for an empty list.",
        "source": "def safe_average(values):\n    return sum(values) / len(values)\n",
        "visible": "from buggy_code import safe_average\n\ndef test_visible():\n    assert safe_average([]) == 0.0\n",
        "hidden": "from buggy_code import safe_average\n\ndef test_hidden():\n    assert safe_average([2, 4, 6]) == 4\n",
    },
    {
        "task_id": "bench_py_003",
        "language": "python",
        "bug_type": "sorting_direction",
        "issue": "top_scores should return the highest scores in descending order.",
        "source": "def top_scores(scores, k):\n    return sorted(scores)[:k]\n",
        "visible": "from buggy_code import top_scores\n\ndef test_visible():\n    assert top_scores([1, 3, 2], 2) == [3, 2]\n",
        "hidden": "from buggy_code import top_scores\n\ndef test_hidden():\n    assert top_scores([10, 40, 20, 30], 3) == [40, 30, 20]\n",
    },
    {
        "task_id": "bench_py_004",
        "language": "python",
        "bug_type": "string_normalization",
        "issue": "normalize_username should strip whitespace and lowercase names.",
        "source": "def normalize_username(name):\n    return name.lower()\n",
        "visible": "from buggy_code import normalize_username\n\ndef test_visible():\n    assert normalize_username(' Alice ') == 'alice'\n",
        "hidden": "from buggy_code import normalize_username\n\ndef test_hidden():\n    assert normalize_username('\\tBOB\\n') == 'bob'\n",
    },
    {
        "task_id": "bench_py_005",
        "language": "python",
        "bug_type": "dynamic_programming_transition",
        "issue": "fib uses the wrong dynamic programming transition.",
        "source": "def fib(n):\n    if n < 2:\n        return n\n    dp = [0, 1]\n    for _ in range(2, n + 1):\n        dp.append(dp[-1] + dp[-1])\n    return dp[-1]\n",
        "visible": "from buggy_code import fib\n\ndef test_visible():\n    assert fib(5) == 5\n",
        "hidden": "from buggy_code import fib\n\ndef test_hidden():\n    assert fib(7) == 13\n",
    },
    {
        "task_id": "bench_py_006",
        "language": "python",
        "bug_type": "counting_update",
        "issue": "count_words should increment duplicate word counts.",
        "source": "def count_words(words):\n    counts = {}\n    for word in words:\n        counts[word] = 1\n    return counts\n",
        "visible": "from buggy_code import count_words\n\ndef test_visible():\n    assert count_words(['a', 'a']) == {'a': 2}\n",
        "hidden": "from buggy_code import count_words\n\ndef test_hidden():\n    assert count_words(['a', 'b', 'a']) == {'a': 2, 'b': 1}\n",
    },
    {
        "task_id": "bench_js_001",
        "language": "javascript",
        "bug_type": "string_normalization",
        "issue": "normalizeUsername should trim whitespace and lowercase names.",
        "source": "function normalizeUsername(name) {\n  return name.toLowerCase();\n}\nmodule.exports = { normalizeUsername };\n",
        "visible": JS_ASSERT_HEADER + "assert.strictEqual(lib.normalizeUsername(' Alice '), 'alice');\n",
        "hidden": JS_ASSERT_HEADER + "assert.strictEqual(lib.normalizeUsername('\\tBOB\\n'), 'bob');\n",
    },
    {
        "task_id": "bench_js_002",
        "language": "javascript",
        "bug_type": "empty_boundary",
        "issue": "largestOrNull should return null for an empty array.",
        "source": "function largestOrNull(values) {\n  return Math.max(...values);\n}\nmodule.exports = { largestOrNull };\n",
        "visible": JS_ASSERT_HEADER + "assert.strictEqual(lib.largestOrNull([]), null);\n",
        "hidden": JS_ASSERT_HEADER + "assert.strictEqual(lib.largestOrNull([2, 9, 1]), 9);\n",
    },
    {
        "task_id": "bench_js_003",
        "language": "javascript",
        "bug_type": "counting_update",
        "issue": "countWords should increment duplicate word counts.",
        "source": "function countWords(words) {\n  const counts = {};\n  for (const word of words) {\n    counts[word] = 1;\n  }\n  return counts;\n}\nmodule.exports = { countWords };\n",
        "visible": JS_ASSERT_HEADER + "assert.deepStrictEqual(lib.countWords(['a', 'a']), { a: 2 });\n",
        "hidden": JS_ASSERT_HEADER + "assert.deepStrictEqual(lib.countWords(['a', 'b', 'a']), { a: 2, b: 1 });\n",
    },
    {
        "task_id": "bench_js_004",
        "language": "javascript",
        "bug_type": "exception_handling",
        "issue": "parseIntOrDefault should return the default value for invalid input.",
        "source": "function parseIntOrDefault(text, defaultValue = 0) {\n  return Number.parseInt(text, 10);\n}\nmodule.exports = { parseIntOrDefault };\n",
        "visible": JS_ASSERT_HEADER + "assert.strictEqual(lib.parseIntOrDefault('bad', -1), -1);\n",
        "hidden": JS_ASSERT_HEADER + "assert.strictEqual(lib.parseIntOrDefault('42', -1), 42);\n",
    },
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/benchmark_sources.yaml")
    parser.add_argument("--max-tasks", type=int, default=20)
    args = parser.parse_args()

    root = Path.cwd()
    config = load_yaml(root / args.config)
    output_dir = root / config.get("output_dir", "examples/benchmark_tasks")
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = []
    for template in TASK_TEMPLATES[: args.max_tasks]:
        task_dir = output_dir / template["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        source_name = "buggy_code.py" if template["language"] == "python" else "buggy_code.js"
        visible_name = "test_visible.py" if template["language"] == "python" else "test_visible.js"
        hidden_name = "test_hidden.py" if template["language"] == "python" else "test_hidden.js"
        (task_dir / "issue.md").write_text(template["issue"] + "\n", encoding="utf-8")
        (task_dir / source_name).write_text(template["source"], encoding="utf-8")
        (task_dir / visible_name).write_text(template["visible"], encoding="utf-8")
        (task_dir / hidden_name).write_text(template["hidden"], encoding="utf-8")
        visible_command = f"python -m pytest {visible_name}" if template["language"] == "python" else f"node {visible_name}"
        hidden_command = f"python -m pytest {hidden_name}" if template["language"] == "python" else f"node {hidden_name}"
        tasks.append(
            {
                "task_id": template["task_id"],
                "language": template["language"],
                "project_source": "open-source-style-micro-benchmark",
                "construction": "manual_injection",
                "bug_type": template["bug_type"],
                "difficulty": "easy",
                "issue": str((task_dir / "issue.md").relative_to(root)).replace("\\", "/"),
                "source_files": [str((task_dir / source_name).relative_to(root)).replace("\\", "/")],
                "allowed_files": [str((task_dir / source_name).relative_to(root)).replace("\\", "/")],
                "test_files": [str((task_dir / visible_name).relative_to(root)).replace("\\", "/")],
                "hidden_test_files": [str((task_dir / hidden_name).relative_to(root)).replace("\\", "/")],
                "test_command": visible_command,
                "visible_test_command": visible_command,
                "hidden_test_command": hidden_command,
            }
        )
    output_tasks_file = root / config.get("output_tasks_file", "configs/tasks_benchmark.yaml")
    output_tasks_file.write_text(json.dumps({"tasks": tasks}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(tasks)} benchmark tasks to {output_tasks_file}")


if __name__ == "__main__":
    main()

