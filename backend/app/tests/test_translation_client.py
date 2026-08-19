from unittest.mock import MagicMock

from app.integrations.translation_client import RealTranslationClient, _PassthroughTranslationClient


async def test_passthrough_returns_text_unchanged() -> None:
    client = _PassthroughTranslationClient()

    result = await client.translate("Turn left at the platform.", "ar")

    assert result == "Turn left at the platform."


async def test_real_client_calls_sdk_with_target_language_and_parent_resource() -> None:
    fake_sdk = MagicMock()
    fake_translation = MagicMock()
    fake_translation.translated_text = "פנה שמאלה בפלטפורמה."
    fake_sdk.translate_text.return_value = MagicMock(translations=[fake_translation])
    client = RealTranslationClient("argus-demo", sdk_client=fake_sdk)

    result = await client.translate("Turn left at the platform.", "he")

    assert result == "פנה שמאלה בפלטפורמה."
    fake_sdk.translate_text.assert_called_once_with(
        request={
            "parent": "projects/argus-demo/locations/global",
            "contents": ["Turn left at the platform."],
            "mime_type": "text/plain",
            "target_language_code": "he",
        }
    )
