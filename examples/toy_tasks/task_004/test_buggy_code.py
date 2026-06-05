from buggy_code import normalize_username


def test_normalize_strips_and_lowers():
    assert normalize_username(" Alice ") == "alice"
    assert normalize_username("\tBOB\n") == "bob"

