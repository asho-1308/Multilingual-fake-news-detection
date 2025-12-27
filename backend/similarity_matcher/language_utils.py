def detect_language(text):
    if not text:
        return "en"
    sinhala_count = sum(1 for ch in text if '\u0D80' <= ch <= '\u0DFF')
    tamil_count = sum(1 for ch in text if '\u0B80' <= ch <= '\u0BFF')
    if sinhala_count > tamil_count and sinhala_count > 0:
        return "si"
    if tamil_count > sinhala_count and tamil_count > 0:
        return "ta"
    return "en"

def detect_language_safe(text):
    try:
        return detect_language(text)
    except Exception:
        return "en"
