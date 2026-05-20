import requests

def detect_and_translate(text, source_language, target_language):
    if not text or not text.strip():
        return text
    if source_language == target_language:
        return text

    # Try Google Translate unofficial API first
    translated = _google_translate(text, source_language, target_language)
    if translated and translated.strip() != text.strip():
        return translated

    # Fallback to MyMemory
    translated = _mymemory_translate(text, source_language, target_language)
    if translated and translated.strip() != text.strip():
        return translated

    return text


def _google_translate(text, source, target):
    try:
        response = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": source,
                "tl": target,
                "dt": "t",
                "q": text[:500],
            },
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            translated = "".join(
                part[0] for part in data[0] if part[0]
            )
            if translated:
                return translated
    except Exception:
        pass
    return None


def _mymemory_translate(text, source, target):
    try:
        response = requests.get(
            "https://api.mymemory.translated.net/get",
            params={
                "q": text[:500],
                "langpair": f"{source}|{target}",
                "de": "linguaduo@translation.com",
            },
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('responseStatus') == 200:
                translated = data['responseData']['translatedText']
                if 'MYMEMORY WARNING' not in translated:
                    return translated
    except Exception:
        pass
    return None


def get_or_create_translation(message, target_language):
    from .models import Translation
    source_language = message.original_language or 'en'
    if source_language == target_language:
        return message.original_text

    # Delete bad cached translation (same as original)
    existing = Translation.objects.filter(
        message=message, language=target_language
    ).first()
    if existing:
        if existing.translated_text.strip() == message.original_text.strip():
            existing.delete()
        else:
            return existing.translated_text

    translated = detect_and_translate(
        message.original_text, source_language, target_language
    )

    Translation.objects.update_or_create(
        message=message,
        language=target_language,
        defaults={'translated_text': translated}
    )
    return translated
