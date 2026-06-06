from buggy_code import top_scores

def test_hidden():
    assert top_scores([10, 40, 20, 30], 3) == [40, 30, 20]
