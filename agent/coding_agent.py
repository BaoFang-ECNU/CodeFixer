"""CodingAgent that repairs tasks through environment tools."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from agent.base import AgentResult, BaseAgent
from agent.memory import Memory
from agent.tools import ToolRegistry
from env.code_env import CodeRepairEnv
from training.policy import Policy, RuleBasedPolicy
from training.reward import RewardModel
from training.trajectory import Trajectory, TrajectoryStep, utc_now


class CodingAgent(BaseAgent):
    """A minimal tool-using code repair agent."""

    def __init__(self, policy: Policy | None = None, reward_model: RewardModel | None = None, memory: Memory | None = None, max_steps: int = 6):
        self.policy = policy or RuleBasedPolicy()
        self.reward_model = reward_model or RewardModel()
        self.memory = memory or Memory()
        self.max_steps = max_steps

    def run(self, env: CodeRepairEnv, trajectory_path: str | Path | None = None, config: dict[str, Any] | None = None) -> AgentResult:
        started = time.perf_counter()
        observation = env.reset()
        tools = ToolRegistry(env)
        trajectory = Trajectory(env.task.task_id)
        previous_failed = True
        final_answer = ""
        timed_out = False
        first_pass_step: int | None = None
        initial_test_output = ""
        final_test_output = ""
        config = config or {}

        for step_id in range(1, self.max_steps + 1):
            if config.get("_diagnosis"):
                observation["diagnosis"] = config["_diagnosis"]
                observation["bug_type_hint"] = config["_diagnosis"].get("bug_type", observation.get("bug_type_hint", ""))
            memory_payload = self.memory.to_dict() if config.get("agent", {}).get("use_memory", True) else {}
            proposal = self.policy.propose_action(observation, memory_payload, config)
            tool_output = tools.execute(proposal.action, proposal.args)

            if proposal.action == "edit_file":
                observation = env.observe()
                test_result = env.run_tests()
            elif proposal.action == "run_tests":
                test_result = tool_output
                observation = env.observe()
            elif proposal.action == "final_answer":
                test_result = env.last_test_result
                final_answer = str(tool_output)
                observation = env.observe()
            else:
                test_result = env.last_test_result
                observation = env.observe()

            timed_out = bool(timed_out or (test_result and test_result.timed_out))
            if test_result and not initial_test_output:
                initial_test_output = test_result.output
            if test_result:
                final_test_output = test_result.output
            reward = self.reward_model.score(
                test_result=test_result,
                patch_size=env.patch_size(),
                tool_calls=env.tool_calls,
                unsafe_edits=env.unsafe_edits,
                previous_failed=previous_failed,
            )
            done = bool(test_result and test_result.passed)
            if done and first_pass_step is None:
                first_pass_step = step_id
            if test_result:
                previous_failed = not test_result.passed

            trajectory.add(
                TrajectoryStep(
                    task_id=env.task.task_id,
                    step_id=step_id,
                    observation=observation,
                    action=proposal.action,
                    action_args={**proposal.args, "rationale": proposal.rationale},
                    test_output=test_result.output if test_result else str(tool_output),
                    reward=reward.total,
                    done=done,
                    patch_diff=env.get_diff(count_tool=False),
                    timestamp=utc_now(),
                )
            )
            if done:
                final_answer = env.final_answer()
                break

        if trajectory_path:
            trajectory.save_jsonl(trajectory_path, append=True)

        patch_diff = env.get_diff(count_tool=False)
        hidden_result = env.run_hidden_tests()
        runtime = time.perf_counter() - started
        system_version = config.get("system_version", config.get("evaluation", {}).get("system_version", "feedback"))
        return AgentResult(
            task_id=env.task.task_id,
            success=trajectory.success,
            visible_success=trajectory.success,
            hidden_success=hidden_result.passed if hidden_result else None,
            final_answer=final_answer or env.final_answer(),
            patch_diff=patch_diff,
            reward=trajectory.total_reward,
            steps=len(trajectory.steps),
            tool_calls=env.tool_calls,
            test_runs=env.test_runs,
            runtime_sec=runtime,
            patch_size=env.patch_size(),
            patch_diff_lines=sum(1 for line in patch_diff.splitlines() if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))),
            patch_file_count=self._patch_file_count(patch_diff),
            unsafe_edits=env.unsafe_edits,
            timed_out=timed_out,
            failure_reason=self._failure_reason(trajectory.success, timed_out, env.unsafe_edits, patch_diff, final_test_output),
            first_pass_step=first_pass_step,
            initial_test_output=initial_test_output,
            final_test_output=final_test_output,
            memory_enabled=bool(config.get("agent", {}).get("use_memory", True)),
            test_feedback_enabled=bool(config.get("agent", {}).get("use_test_feedback", True)),
            system_version=system_version,
            bug_type=env.task.bug_type,
            language=env.task.language,
            project_source=env.task.project_source,
            diagnosis=config.get("_diagnosis"),
            critic_report=config.get("_critic_report"),
            trajectory=trajectory.to_dict(),
        )

    @staticmethod
    def _failure_reason(success: bool, timed_out: bool, unsafe_edits: int, patch_diff: str, final_test_output: str) -> str:
        if success:
            return "passed"
        if timed_out:
            return "timeout"
        if unsafe_edits:
            return "unsafe_edit"
        if not patch_diff:
            return "no_patch_generated"
        if "ModuleNotFoundError" in final_test_output:
            return "dependency_missing"
        return "tests_still_failing"

    @staticmethod
    def _patch_file_count(patch_diff: str) -> int:
        return sum(1 for line in patch_diff.splitlines() if line.startswith("+++ b/"))
