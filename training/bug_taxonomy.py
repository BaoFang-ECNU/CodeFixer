"""Bug taxonomy and lightweight diagnosis rules."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class BugDiagnosis:
    """Structured bug diagnosis used by multi-agent repair."""

    bug_type: str
    confidence: float
    evidence: list[str]
    recommended_actions: list[str]
    risk_flags: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BugTaxonomy:
    """Rule-based bug taxonomy for code repair tasks."""

    RULES: list[tuple[str, list[str], list[str]]] = [
        ("syntax_error", ["SyntaxError", "invalid syntax", " if n ="], ["inspect_file", "edit_file", "run_tests"]),
        ("off_by_one", ["off-by-one", "inclusive", "upper bound", "range(1, n)"], ["inspect_file", "edit_file", "run_tests"]),
        ("division_by_zero", ["ZeroDivisionError", "division by zero", "/ len(", "empty average"], ["inspect_file", "edit_file", "run_tests"]),
        ("sorting_direction", ["descending", "highest", "lowest", "reverse=True", "sorted("], ["inspect_file", "edit_file", "run_tests"]),
        ("string_normalization", ["strip", "whitespace", "normalize", "lowercase"], ["inspect_file", "edit_file", "run_tests"]),
        ("empty_boundary", ["empty", "None", "max(values)"], ["inspect_file", "edit_file", "run_tests"]),
        ("dynamic_programming_transition", ["fibonacci", "dynamic programming", "transition", "dp[-1] + dp[-1]"], ["inspect_file", "edit_file", "run_tests"]),
        ("counting_update", ["count", "duplicate", "counts[word] = 1"], ["inspect_file", "edit_file", "run_tests"]),
        ("exception_handling", ["ValueError", "invalid", "default", "try", "except"], ["inspect_file", "edit_file", "run_tests"]),
    ]

    def diagnose(self, observation: dict[str, Any]) -> BugDiagnosis:
        text_parts = [
            observation.get("issue", ""),
            observation.get("last_test_output", ""),
            observation.get("bug_type_hint", ""),
            "\n".join(observation.get("source_snapshot", {}).values()),
        ]
        text = "\n".join(text_parts)
        text_lower = text.lower()
        evidence: list[str] = []
        best_type = "unknown"
        best_score = 0
        actions = ["inspect_file", "run_tests"]
        for bug_type, keywords, recommended in self.RULES:
            matches = [kw for kw in keywords if kw.lower() in text_lower]
            if len(matches) > best_score:
                best_score = len(matches)
                best_type = bug_type
                evidence = matches
                actions = recommended
        confidence = min(0.95, 0.25 + 0.18 * best_score)
        risks = self._risk_flags(text_lower)
        return BugDiagnosis(best_type, round(confidence, 3), evidence, actions, risks)

    @staticmethod
    def _risk_flags(text_lower: str) -> list[str]:
        flags: list[str] = []
        if "test_" in text_lower and ("delete" in text_lower or "remove" in text_lower):
            flags.append("possible_test_deletion")
        if "hardcode" in text_lower or "hard-code" in text_lower:
            flags.append("possible_hardcoding")
        return flags

