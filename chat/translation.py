import requests

SUPPORTED_LANGUAGES = [
    'en', 'ar', 'fr', 'de', 'es', 'it', 'pt', 'ru',
    'zh', 'ja', 'ko', 'tr', 'ur', 'hi', 'bn'
]

def detect_and_translate(text, source_language, target_language):
    if not text or not text.strip():
        return text
    if target_language not in SUPPORTED_LANGUAGES:
        return text
    if source_language == target_language:
        return text
    try:
        response = requests.get(
            "https://api.mymemory.translated.net/get",
            params={
                "q": text[:500],
                "langpair": f"{source_language}|{target_language}",
            },
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('responseStatus') == 200:
                return data['responseData']['translatedText']
    except Exception:
        pass
    return text

def get_or_create_translation(message, target_language):
    from .models import Translation

    source_language = message.original_language or 'en'

    if source_language == target_language:
        return message.original_text

    translation, created = Translation.objects.get_or_create(
        message=message,
        language=target_language,
        defaults={
            'translated_text': detect_and_translate(
                message.original_text,
                source_language,
                target_language
            )
        }
    )
    return translation.translated_text
