from buggy_code import is_adult

def test_hidden():
    assert is_adult(17) is False
    assert is_adult(21) is True
