from buggy_code import normalize_username

def test_hidden():
    assert normalize_username('\tBOB\n') == 'bob'
