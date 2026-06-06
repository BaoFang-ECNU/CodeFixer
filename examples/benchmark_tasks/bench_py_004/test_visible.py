from buggy_code import normalize_username

def test_visible():
    assert normalize_username(' Alice ') == 'alice'
