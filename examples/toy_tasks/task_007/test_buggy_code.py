from buggy_code import count_words


def test_count_words_duplicates():
    assert count_words(["a", "b", "a", "c", "b", "a"]) == {"a": 3, "b": 2, "c": 1}


def test_count_words_empty():
    assert count_words([]) == {}

