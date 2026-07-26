import os

from app.api.services.gemini_provider import (
    analyze_receipt_image as analyze_receipt_image_gemini
)

from app.api.services.openai_provider import (
    analyze_receipt_image_openai
)

AI_PROVIDER = os.getenv(
    "AI_PROVIDER",
    "gemini"
)

def _is_quota_error(e: Exception) -> bool:
    msg = str(e).lower()
    return "429" in msg or "quota" in msg or "rate limit" in msg or "resource_exhausted" in msg

def analyze_receipt_image(
    image_bytes: bytes,
    mime_type: str
):

    if AI_PROVIDER == "openai":
        primary = lambda: analyze_receipt_image_openai(image_bytes, mime_type)
        fallback = lambda: analyze_receipt_image_gemini(image_bytes, mime_type)
    else:
        primary = lambda: analyze_receipt_image_gemini(image_bytes, mime_type)
        fallback = lambda: analyze_receipt_image_openai(image_bytes, mime_type)

    try:
        return primary()
    except Exception as e:
        if _is_quota_error(e):
            print(f"Quota excedida en provider principal, usando fallback: {e}")
            try:
                return fallback()
            except Exception as e2:
                if _is_quota_error(e2):
                    print(f"Fallback también excedió cuota: {e2}")
                raise
        raise