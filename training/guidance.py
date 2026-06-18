"""Rule-based guidance generation for Agent-RLVR style data."""

from __future__ import annotations

from typing import Any


class GuidanceGenerator:
    """Create lightweight repair guidance from observations and test feedback."""

    def generate(
        self,
        observation: dict[str, Any],
        action: str,
        test_output: str = "",
        reward: float = 0.0,
        done: bool = False,
        patch_diff: str = "",
        unsafe_edits: int = 0,
    ) -> dict[str, Any]:
        """Return a compact guidance record for training and failure analysis."""

        text = f"{observation.get('issue', '')}\n{test_output}".lower()
        bug_type = observation.get("diagnosis", {}).get("bug_type") or observation.get("bug_type_hint")
        if not bug_type or bug_type == "unknown":
            bug_type = self._infer_bug_type(text)
        risk_flags: list[str] = []
        if unsafe_edits:
            risk_flags.append("unsafe_edit")
        if "timeout" in text:
            risk_flags.append("timeout")
        if "syntaxerror" in text or "indentationerror" in text:
            risk_flags.append("syntax_error")

        failure_summary = "测试已通过" if done else self._failure_summary(text, patch_diff)
        return {
            "failure_summary": failure_summary,
            "suspected_bug_type": bug_type or "unknown",
            "suggested_next_action": self._next_action(done, patch_diff, action, risk_flags),
            "repair_hint": self._repair_hint(bug_type or "unknown", text),
            "risk_flags": risk_flags,
            "reward": reward,
        }

    @staticmethod
    def _infer_bug_type(text: str) -> str:
        if "zero" in text or "division" in text:
            return "division_by_zero"
        if "off-by-one" in text or "inclusive" in text or "upper bound" in text:
            return "off_by_one"
        if "descending" in text or "highest" in text:
            return "sorting_direction"
        if "empty" in text:
            return "empty_boundary"
        if "valueerror" in text or "invalid" in text:
            return "exception_handling"
        return "unknown"

    @staticmethod
    def _failure_summary(text: str, patch_diff: str) -> str:
        if not patch_diff:
            return "尚未生成补丁"
        if "assertionerror" in text or "failed" in text:
            return "补丁后测试仍失败"
        if "syntaxerror" in text or "indentationerror" in text:
            return "补丁引入语法或缩进错误"
        if "timeout" in text:
            return "测试运行超时"
        return "未验证通过，需要继续检查测试反馈"

    @staticmethod
    def _next_action(done: bool, patch_diff: str, action: str, risk_flags: list[str]) -> str:
        if done:
            return "submit_patch"
        if "unsafe_edit" in risk_flags or "syntax_error" in risk_flags:
            return "revert_or_repair_edit"
        if not patch_diff:
            return "inspect_or_edit_target_file"
        if action == "edit_file":
            return "run_tests"
        return "revise_patch_with_test_feedback"

    @staticmethod
    def _repair_hint(bug_type: str, text: str) -> str:
        hints = {
            "off_by_one": "检查循环、切片或 range 边界是否少包含一个元素。",
            "division_by_zero": "在除法或平均值计算前处理空输入或零分母。",
            "sorting_direction": "检查排序方向是否与最高/最低、升序/降序要求一致。",
            "empty_boundary": "为空列表、空字符串或 None 输入添加边界处理。",
            "exception_handling": "为解析失败或非法输入添加异常处理和默认返回值。",
        }
        if "assert" in text and bug_type == "unknown":
            return "对照断言左右两侧差异，优先修正返回值语义。"
        return hints.get(bug_type, "结合失败日志重新定位相关代码并生成更小的补丁。")
