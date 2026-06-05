from env.test_runner import TestResult
from training.reward import RewardModel


def test_reward_positive_for_passing_result():
    result = TestResult(command="pytest", returncode=0, stdout="", stderr="", duration_sec=0.1)
    reward = RewardModel({"pass_visible_tests": 1.0}).score(result, patch_size=1, tool_calls=1, unsafe_edits=0)
    assert reward.total > 0
    assert reward.passed

