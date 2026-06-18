"""Policy interfaces and a small rule-based repair policy."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class ActionProposal:
    """An action selected by a policy."""

    action: str
    args: dict[str, Any]
    rationale: str = ""


class Policy:
    """Base policy interface."""

    def propose_action(self, observation: dict[str, Any], memory: dict[str, Any] | None = None, config: dict[str, Any] | None = None) -> ActionProposal:
        raise NotImplementedError


class RuleBasedPolicy(Policy):
    """Simple policy that uses issues, source text, and test feedback."""

    def __init__(self):
        self._attempted_edits: set[str] = set()

    def propose_action(self, observation: dict[str, Any], memory: dict[str, Any] | None = None, config: dict[str, Any] | None = None) -> ActionProposal:
        config = config or {}
        source_files = observation.get("source_files", [])
        if not config.get("agent", {}).get("use_test_feedback", True) and not observation.get("diff"):
            return ActionProposal("final_answer", {}, "Ablation disables test feedback, so the agent avoids feedback-driven edits.")

        if not observation.get("last_test_output") and not observation.get("diff"):
            return ActionProposal("run_tests", {"command": observation["test_command"]}, "Establish failing test signal before editing.")

        for path, content in observation.get("source_snapshot", {}).items():
            proposal = self._candidate_edit(path, content, observation)
            if proposal:
                key = f"{proposal.args.get('path')}::{proposal.args.get('old_text')}::{proposal.args.get('new_text')}"
                if key not in self._attempted_edits:
                    self._attempted_edits.add(key)
                    return proposal

        if observation.get("diff") and not observation.get("last_test_passed"):
            return ActionProposal("run_tests", {"command": observation["test_command"]}, "Validate the current candidate patch.")

        if source_files:
            return ActionProposal("inspect_file", {"path": source_files[0]}, "Inspect source because no edit candidate was found.")
        return ActionProposal("final_answer", {}, "No source file is available.")

    def _candidate_edit(self, path: str, content: str, observation: dict[str, Any]) -> ActionProposal | None:
        issue_and_output = f"{observation.get('issue', '')}\n{observation.get('last_test_output', '')}".lower()
        if ("off-by-one" in issue_and_output or "inclusive" in issue_and_output or "upper bound" in issue_and_output) and "range(1, n)" in content:
            return ActionProposal("edit_file", {"path": path, "old_text": "range(1, n)", "new_text": "range(1, n + 1)"}, "Make the upper bound inclusive.")
        if ("off-by-one" in issue_and_output or "inclusive" in issue_and_output or "upper bound" in issue_and_output) and "i < n" in content:
            return ActionProposal("edit_file", {"path": path, "old_text": "i < n", "new_text": "i <= n"}, "Make the JavaScript loop upper bound inclusive.")

        if ("division by zero" in issue_and_output or "empty" in issue_and_output) and "return sum(values) / len(values)" in content:
            return ActionProposal(
                "edit_file",
                {"path": path, "old_text": "return sum(values) / len(values)", "new_text": "if not values:\n        return 0.0\n    return sum(values) / len(values)"},
                "Guard empty input before division.",
            )
        if ("division by zero" in issue_and_output or "empty" in issue_and_output) and "return values.reduce((total, value) => total + value, 0) / values.length;" in content:
            return ActionProposal(
                "edit_file",
                {
                    "path": path,
                    "old_text": "return values.reduce((total, value) => total + value, 0) / values.length;",
                    "new_text": "if (values.length === 0) return 0;\n  return values.reduce((total, value) => total + value, 0) / values.length;",
                },
                "Guard empty arrays before averaging.",
            )

        if ("descending" in issue_and_output or "highest" in issue_and_output or "lowest" in issue_and_output) and re.search(r"sorted\(([^)]*)\)\[:k\]", content):
            return ActionProposal("edit_file", {"path": path, "old_text": "sorted(scores)[:k]", "new_text": "sorted(scores, reverse=True)[:k]"}, "Sort scores descending before slicing.")
        if ("descending" in issue_and_output or "highest" in issue_and_output or "lowest" in issue_and_output) and "sort((a, b) => a - b)" in content:
            return ActionProposal("edit_file", {"path": path, "old_text": "sort((a, b) => a - b)", "new_text": "sort((a, b) => b - a)"}, "Sort numeric scores descending.")

        if ("strip" in issue_and_output or "whitespace" in issue_and_output or "normalize" in issue_and_output) and "return name.lower()" in content:
            return ActionProposal("edit_file", {"path": path, "old_text": "return name.lower()", "new_text": "return name.strip().lower()"}, "Strip whitespace before lowercasing.")
        if ("strip" in issue_and_output or "whitespace" in issue_and_output or "normalize" in issue_and_output) and "return name.toLowerCase();" in content:
            return ActionProposal("edit_file", {"path": path, "old_text": "return name.toLowerCase();", "new_text": "return name.trim().toLowerCase();"}, "Trim whitespace before lowercasing.")
        if ("case-insensitive" in issue_and_output or "case insensitive" in issue_and_output) and "return text.includes(keyword);" in content:
            return ActionProposal(
                "edit_file",
                {"path": path, "old_text": "return text.includes(keyword);", "new_text": "return text.toLowerCase().includes(keyword.toLowerCase());"},
                "Normalize both operands before keyword matching.",
            )

        if ("empty" in issue_and_output or "none" in issue_and_output) and "return max(values)" in content:
            return ActionProposal("edit_file", {"path": path, "old_text": "return max(values)", "new_text": "if not values:\n        return None\n    return max(values)"}, "Guard empty input before max().")
        if ("empty" in issue_and_output or "null" in issue_and_output) and "return Math.max(...values);" in content:
            return ActionProposal("edit_file", {"path": path, "old_text": "return Math.max(...values);", "new_text": "if (values.length === 0) return null;\n  return Math.max(...values);"}, "Guard empty arrays before Math.max.")

        if ("fibonacci" in issue_and_output or "dynamic programming" in issue_and_output or "transition" in issue_and_output) and "dp[-1] + dp[-1]" in content:
            return ActionProposal("edit_file", {"path": path, "old_text": "dp[-1] + dp[-1]", "new_text": "dp[-1] + dp[-2]"}, "Use the previous two DP states.")

        if ("count" in issue_and_output or "duplicate" in issue_and_output) and "counts[word] = 1;" in content:
            return ActionProposal("edit_file", {"path": path, "old_text": "counts[word] = 1;", "new_text": "counts[word] = (counts[word] || 0) + 1;"}, "Increment existing JavaScript counts instead of resetting.")
        if ("count" in issue_and_output or "duplicate" in issue_and_output) and "counts[word] = 1" in content:
            return ActionProposal("edit_file", {"path": path, "old_text": "counts[word] = 1", "new_text": "counts[word] = counts.get(word, 0) + 1"}, "Increment existing counts instead of resetting.")

        if ("valueerror" in issue_and_output or "default" in issue_and_output or "invalid" in issue_and_output) and "return int(text)" in content:
            return ActionProposal(
                "edit_file",
                {"path": path, "old_text": "return int(text)", "new_text": "try:\n        return int(text)\n    except ValueError:\n        return default"},
                "Catch ValueError and return the default.",
            )
        if ("invalid" in issue_and_output or "default" in issue_and_output or "nan" in issue_and_output) and "return Number.parseInt(text, 10);" in content:
            return ActionProposal("edit_file", {"path": path, "old_text": "return Number.parseInt(text, 10);", "new_text": "const value = Number.parseInt(text, 10);\n  return Number.isNaN(value) ? defaultValue : value;"}, "Return default when parseInt yields NaN.")

        if ("age 18" in issue_and_output or "adult" in issue_and_output or "boundary" in issue_and_output) and "return age > 18" in content:
            return ActionProposal("edit_file", {"path": path, "old_text": "return age > 18", "new_text": "return age >= 18"}, "Include the adult age boundary.")

        if ("final element" in issue_and_output or "last item" in issue_and_output or "lastitem" in issue_and_output) and "return values[0]" in content:
            replacement = "return values[-1]" if path.endswith(".py") else "return values[values.length - 1];"
            old_text = "return values[0];" if "return values[0];" in content else "return values[0]"
            return ActionProposal("edit_file", {"path": path, "old_text": old_text, "new_text": replacement}, "Return the final element instead of the first.")

        if "/ len(" in content and "if not" not in content and "ZeroDivisionError" in observation.get("last_test_output", ""):
            old_line = next((line.strip() for line in content.splitlines() if "/ len(" in line), "")
            if old_line:
                return ActionProposal("edit_file", {"path": path, "old_text": old_line, "new_text": "if not values:\n        return 0.0\n    " + old_line}, "Apply generic zero-division guard.")
        return None


class LLMPolicy(Policy):
    """Optional LLM-backed policy that returns auditable tool actions."""

    TOOL_SCHEMA = {
        "action": "one of inspect_file, search_code, edit_file, run_tests, get_diff, revert_last_edit, final_answer",
        "args": "JSON object matching the selected tool",
        "rationale": "short reason for the action",
    }

    def propose_action(self, observation: dict[str, Any], memory: dict[str, Any] | None = None, config: dict[str, Any] | None = None) -> ActionProposal:
        config = config or {}
        prompt = self.build_prompt(observation, memory or {}, config)
        llm_config = config.get("llm", {})
        provider = llm_config.get("provider", "openai")
        if provider == "local":
            return self._call_local(prompt, llm_config)
        if provider == "openai":
            return self._call_openai(prompt, llm_config)
        return ActionProposal("final_answer", {}, f"Unsupported LLM provider: {provider}")

    def build_prompt(self, observation: dict[str, Any], memory: dict[str, Any], config: dict[str, Any]) -> str:
        """Build a compact tool-action prompt for an LLM."""

        payload = {
            "task_id": observation.get("task_id"),
            "issue": observation.get("issue"),
            "source_snapshot": observation.get("source_snapshot"),
            "last_test_output": observation.get("last_test_output"),
            "current_diff": observation.get("diff"),
            "tool_schema": self.TOOL_SCHEMA,
            "budget": {"max_steps": config.get("agent", {}).get("max_steps")},
            "memory": memory,
        }
        return (
            "You are a code repair policy. Return only JSON with keys action, args, rationale. "
            "Do not edit files directly; choose one tool action.\n"
            + json.dumps(payload, ensure_ascii=False)
        )

    def _call_openai(self, prompt: str, llm_config: dict[str, Any]) -> ActionProposal:
        api_key = os.environ.get(llm_config.get("api_key_env", "OPENAI_API_KEY"), "")
        if not api_key:
            return ActionProposal("final_answer", {}, "OPENAI_API_KEY is not set; LLMPolicy produced a safe no-op.")
        body = {
            "model": llm_config.get("model", "gpt-4.1-mini"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": llm_config.get("temperature", 0.0),
            "max_tokens": llm_config.get("max_tokens", 800),
        }
        request = urllib.request.Request(
            llm_config.get("endpoint", "https://api.openai.com/v1/chat/completions"),
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            return self._parse_action(content)
        except (urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
            return ActionProposal("final_answer", {}, f"LLM request failed safely: {exc}")

    def _call_local(self, prompt: str, llm_config: dict[str, Any]) -> ActionProposal:
        endpoint = llm_config.get("endpoint")
        if not endpoint:
            return ActionProposal("final_answer", {}, "Local LLM endpoint is not configured; LLMPolicy produced a safe no-op.")
        if llm_config.get("api_type") == "openai_compatible" or str(endpoint).endswith("/v1/chat/completions"):
            body = {
                "model": llm_config.get("model", "local-code-model"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": llm_config.get("temperature", 0.0),
                "max_tokens": llm_config.get("max_tokens", 800),
            }
        else:
            body = {"prompt": prompt, "temperature": llm_config.get("temperature", 0.0), "max_tokens": llm_config.get("max_tokens", 800)}
        request = urllib.request.Request(endpoint, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
            if "choices" in data:
                content = data["choices"][0]["message"]["content"]
            else:
                content = data.get("content") or data.get("response") or data.get("text") or json.dumps(data)
            return self._parse_action(content)
        except (urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
            return ActionProposal("final_answer", {}, f"Local LLM request failed safely: {exc}")

    def _parse_action(self, content: str) -> ActionProposal:
        try:
            start = content.index("{")
            end = content.rindex("}") + 1
            data = json.loads(content[start:end])
            action = data.get("action", "final_answer")
            args = data.get("args", {})
            rationale = data.get("rationale", "LLM generated tool action.")
            if not isinstance(args, dict):
                args = {}
            return ActionProposal(action, args, rationale)
        except (ValueError, json.JSONDecodeError):
            return ActionProposal("final_answer", {}, "LLM output was not valid tool JSON.")


def build_policy(config: dict[str, Any] | None = None) -> Policy:
    """Construct a policy from config."""

    policy_type = (config or {}).get("policy", {}).get("type", "rule_based")
    if policy_type == "llm":
        return LLMPolicy()
    return RuleBasedPolicy()


class TrainablePolicy(Policy):
    """Reserved interface for trainable RL or distillation policies."""

    def propose_action(self, observation: dict[str, Any], memory: dict[str, Any] | None = None, config: dict[str, Any] | None = None) -> ActionProposal:
        raise NotImplementedError("TrainablePolicy is a placeholder for RL/OPD/DPO updates.")
