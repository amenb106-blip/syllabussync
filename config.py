import os


def api_key():
    return os.environ.get("GEMINI_API_KEY", "")


def ai_enabled():
    return os.environ.get("SYLLABUS_AI") == "1" and bool(api_key())


def model():
    return os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")


def max_input_chars():
    try:
        return int(os.environ.get("MAX_INPUT_CHARS", ""))
    except ValueError:
        return 15000
