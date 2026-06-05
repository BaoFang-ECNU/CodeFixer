"""Lightweight self-evolution loop from trajectories to policy artifacts."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from agent.memory import Memory
from training.dpo_data import export_dpo_pairs
from training.opd import export_opd_records


class SelfEvolutionTrainer:
    """Summarize trajectories and export memory, DPO, and OPD artifacts."""

    def __init__(self, memory: Memory | None = None):
        self.memory = memory or Memory()

    def evolve(self, trajectories: list[dict[str, Any]], output_dir: str | Path = "training", logs_dir: str | Path = "logs") -> dict[str, Any]:
        output_dir = Path(output_dir)
        logs_dir = Path(logs_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)

        successes = [t for t in trajectories if t.get("success")]
        failures = [t for t in trajectories if not t.get("success")]
        action_counter: Counter[str] = Counter()
        rationale_counter: Counter[str] = Counter()
        failure_reasons: Counter[str] = Counter()

        for traj in trajectories:
            last_action = ""
            for step in traj.get("steps", []):
                action = step.get("action", "")
                last_action = action
                action_counter[action] += 1
                rationale = step.get("action_args", {}).get("rationale", "")
                if rationale:
                    rationale_counter[rationale] += 1
            self.memory.update_pattern(last_action or "unknown", bool(traj.get("success")))
            if not traj.get("success"):
                reason = self._failure_reason(traj)
                failure_reasons[reason] += 1
                self.memory.add_failure_reason(reason)

        dpo_pairs = self._make_dpo_pairs(successes, failures)
        opd_records = self._make_opd_records(successes)
        evolved_policy = {
            "preferred_actions": [name for name, _ in action_counter.most_common()],
            "learned_bug_patterns": [name for name, _ in rationale_counter.most_common(10)],
            "num_success": len(successes),
            "num_failure": len(failures),
            "memory": self.memory.to_dict(),
        }

        (output_dir / "evolved_policy.json").write_text(json.dumps(evolved_policy, indent=2, ensure_ascii=False), encoding="utf-8")
        export_dpo_pairs(dpo_pairs, output_dir / "dpo_data.jsonl")
        export_opd_records(opd_records, output_dir / "opd_distill.jsonl")
        summary = self._summary_markdown(evolved_policy, failure_reasons)
        (logs_dir / "evolution_summary.md").write_text(summary, encoding="utf-8")
        return evolved_policy

    @staticmethod
    def rank_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Rank best-of-N candidate patches by reward and safety."""

        return sorted(
            candidates,
            key=lambda item: (
                item.get("reward", 0.0),
                -item.get("unsafe_edits", 0),
                -item.get("patch_size", 0),
                -item.get("tool_calls", 0),
            ),
            reverse=True,
        )

    @staticmethod
    def _failure_reason(traj: dict[str, Any]) -> str:
        steps = traj.get("steps", [])
        if not steps:
            return "empty_trajectory"
        last = steps[-1]
        if "timeout" in last.get("test_output", "").lower():
            return "timeout"
        if last.get("observation", {}).get("unsafe_edits", 0):
            return "unsafe_edit"
        if not last.get("patch_diff"):
            return "no_patch_generated"
        return "tests_still_failing"

    @staticmethod
    def _make_dpo_pairs(successes: list[dict[str, Any]], failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
        pairs: list[dict[str, Any]] = []
        for success, failure in zip(successes, failures):
            chosen = success.get("steps", [{}])[-1]
            rejected = failure.get("steps", [{}])[-1]
            pairs.append(
                {
                    "prompt": chosen.get("observation", {}).get("issue", ""),
                    "chosen": chosen.get("action_args", {}),
                    "rejected": rejected.get("action_args", {}),
                    "chosen_reward": chosen.get("reward", 0),
                    "rejected_reward": rejected.get("reward", 0),
                }
            )
        if not pairs:
            for success in successes:
                edit_steps = [step for step in success.get("steps", []) if step.get("action") == "edit_file"]
                if not edit_steps:
                    continue
                chosen = edit_steps[-1]
                first = success.get("steps", [{}])[0]
                pairs.append(
                    {
                        "prompt": chosen.get("observation", {}).get("issue", ""),
                        "chosen": chosen.get("action_args", {}),
                        "rejected": {"action": "no_op", "rationale": "No patch was generated from the initial failing observation."},
                        "chosen_reward": chosen.get("reward", 0),
                        "rejected_reward": first.get("reward", 0),
                    }
                )
        return pairs

    @staticmethod
    def _make_opd_records(successes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for traj in successes:
            for step in traj.get("steps", []):
                if step.get("action") == "edit_file":
                    records.append(
                        {
                            "observation": step.get("observation", {}),
                            "teacher_action": {"action": step.get("action"), "args": step.get("action_args", {})},
                            "reward": step.get("reward", 0),
                            "rationale": step.get("action_args", {}).get("rationale", "Successful edit from on-policy rollout."),
                        }
                    )
        return records

    @staticmethod
    def _summary_markdown(evolved_policy: dict[str, Any], failure_reasons: Counter[str]) -> str:
        lines = [
            "# Evolution Summary",
            "",
            f"- Successful trajectories: {evolved_policy['num_success']}",
            f"- Failed trajectories: {evolved_policy['num_failure']}",
            f"- Preferred actions: {', '.join(evolved_policy['preferred_actions']) or 'none'}",
            f"- Learned bug patterns: {', '.join(evolved_policy['learned_bug_patterns']) or 'none'}",
            "",
            "## Failure Reasons",
        ]
        if failure_reasons:
            lines.extend(f"- {reason}: {count}" for reason, count in failure_reasons.items())
        else:
            lines.append("- none")
        return "\n".join(lines) + "\n"
