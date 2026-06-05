from buggy_code import top_scores


def test_top_scores_descending():
    assert top_scores([10, 30, 20, 40], 2) == [40, 30]


def test_top_scores_zero_k():
    assert top_scores([1, 2, 3], 0) == []

