from buggy_code import top_scores

def test_visible():
    assert top_scores([1, 3, 2], 2) == [3, 2]
