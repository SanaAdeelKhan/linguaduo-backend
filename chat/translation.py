import requests
from django.conf import settings


def detect_and_translate(text, target_language):
    """Translate text to target language using LibreTranslate."""
    if not text or not text.strip():
        return text

    try:
        response = requests.post(
            f"{settings.LIBRETRANSLATE_URL}/translate",
            json={
                "q": text,
                "source": "auto",
                "target": target_language,
                "format": "text"
            },
            timeout=5
        )
        if response.status_code == 200:
            return response.json().get("translatedText", text)
    except Exception:
        pass
    return text


def get_or_create_translation(message, target_language):
    """Get cached translation or create new one."""
    from .models import Translation

    if message.original_language == target_language:
        return message.original_text

    translation, created = Translation.objects.get_or_create(
        message=message,
        language=target_language,
        defaults={
            'translated_text': detect_and_translate(
                message.original_text,
                target_language
            )
        }
    )
    return translation.translated_text
