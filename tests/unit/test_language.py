from splitmind_ai.app.language import detect_response_language, normalize_response_language


def test_normalize_response_language_accepts_common_aliases():
    assert normalize_response_language("English") == "en"
    assert normalize_response_language("ja-JP") == "ja"
    assert normalize_response_language("auto") is None


def test_detect_response_language_prefers_explicit_request_over_script():
    assert detect_response_language("英語で答えてください") == "en"
    assert detect_response_language("Please respond in Japanese.") == "ja"


def test_detect_response_language_uses_message_script_when_no_override():
    assert detect_response_language("How are you today?") == "en"
    assert detect_response_language("今日は元気？") == "ja"


def test_detect_response_language_respects_explicit_override():
    assert detect_response_language("今日は元気？", "en") == "en"
