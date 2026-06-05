from training.policy import LLMPolicy, RuleBasedPolicy


def test_llm_policy_without_key_returns_legal_action():
    proposal = LLMPolicy().propose_action(
        {"task_id": "t", "issue": "x", "source_snapshot": {}, "test_command": "python -m pytest"},
        {},
        {"llm": {"provider": "openai", "api_key_env": "MISSING_CODEFIXER_TEST_KEY"}},
    )
    assert proposal.action in {"inspect_file", "search_code", "edit_file", "run_tests", "get_diff", "revert_last_edit", "final_answer"}


def test_rule_policy_handles_string_normalization():
    proposal = RuleBasedPolicy().propose_action(
        {
            "task_id": "task_004",
            "issue": "strip whitespace and normalize lowercase",
            "source_snapshot": {"buggy_code.py": "def normalize_username(name):\n    return name.lower()\n"},
            "source_files": ["buggy_code.py"],
            "test_command": "python -m pytest",
            "last_test_output": "AssertionError",
            "diff": "",
        },
        {},
        {"agent": {"use_test_feedback": True}},
    )
    assert proposal.action == "edit_file"
    assert "strip" in proposal.args["new_text"]

