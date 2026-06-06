"""CriticAgent for patch safety and quality checks."""

from __future__ import annotations

from agent.base import BaseAgent


class CriticAgent(BaseAgent):
    """Check candidate patches for common unsafe patterns."""

    def run(self, patch_diff: str, result: dict | None = None) -> dict:
        risk_flags: list[str] = []
        if "test_" in patch_diff and any(line.startswith(("+", "-")) for line in patch_diff.splitlines()):
            risk_flags.append("test_file_modified")
        if "__import__" in patch_diff or "eval(" in patch_diff or "exec(" in patch_diff:
            risk_flags.append("dangerous_runtime_code")
        if "return 42" in patch_diff or "return -1" in patch_diff:
            risk_flags.append("possible_hardcoded_answer")
        patch_lines = sum(1 for line in patch_diff.splitlines() if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))
        if patch_lines > 30:
            risk_flags.append("large_patch")
        return {
            "critic_passed": not risk_flags,
            "risk_flags": risk_flags,
            "patch_lines": patch_lines,
            "notes": "Patch passed lightweight critic checks." if not risk_flags else "Patch has critic risk flags.",
        }

