from agent.diagnosis_agent import DiagnosisAgent


def test_diagnosis_agent_detects_dp_transition():
    diagnosis = DiagnosisAgent().run(
        {
            "issue": "Fibonacci dynamic programming transition is wrong.",
            "source_snapshot": {"buggy_code.py": "dp.append(dp[-1] + dp[-1])"},
            "last_test_output": "",
        }
    )
    assert diagnosis["bug_type"] == "dynamic_programming_transition"
    assert diagnosis["confidence"] > 0.4

