"""Tool facade around CodeRepairEnv."""

from __future__ import annotations

from env.code_env import CodeRepairEnv


class ToolRegistry:
    """Dispatch named tool actions to environment methods."""

    def __init__(self, env: CodeRepairEnv):
        self.env = env

    def execute(self, action: str, args: dict):
        if action == "inspect_file":
            return self.env.inspect_file(**args)
        if action == "search_code":
            return self.env.search_code(**args)
        if action == "edit_file":
            return self.env.edit_file(**args)
        if action == "run_tests":
            return self.env.run_tests(**args)
        if action == "get_diff":
            return self.env.get_diff(**args)
        if action == "revert_last_edit":
            return self.env.revert_last_edit()
        if action == "final_answer":
            return self.env.final_answer()
        raise ValueError(f"unknown action: {action}")

