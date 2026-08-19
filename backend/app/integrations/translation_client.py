from typing import Any, Protocol

from starlette.concurrency import run_in_threadpool


class TranslationClient(Protocol):
    async def translate(self, text: str, target_language: str) -> str: ...


class RealTranslationClient:
    """The genuine `google-cloud-translate` v3 SDK behind the
    TranslationClient interface — not a mock, the real client, just
    swappable so tests use a fake instead (same pattern RealStorageClient
    and RealTwilioClient already established). `sdk_client` is injectable
    for tests; unset in production, where it's the real
    `translate.TranslationServiceClient()`. Wiring the *real* call (as
    opposed to this class existing) is deferred to the pre-demo checklist,
    same as every other real-external-service integration in this project —
    see get_translation_client_factory() in ws/session.py."""

    def __init__(self, project_id: str, *, sdk_client: Any | None = None) -> None:
        self._parent = f"projects/{project_id}/locations/global"
        if sdk_client is not None:
            self._client = sdk_client
        else:
            from google.cloud import translate

            self._client = translate.TranslationServiceClient()

    async def translate(self, text: str, target_language: str) -> str:
        response = await run_in_threadpool(
            self._client.translate_text,
            request={
                "parent": self._parent,
                "contents": [text],
                "mime_type": "text/plain",
                "target_language_code": target_language,
            },
        )
        return response.translations[0].translated_text


class _PassthroughTranslationClient:
    """The honest default until RealTranslationClient is wired in (pre-demo
    checklist) — returns text unchanged rather than crashing or guessing at
    a translation, same convention as _NoOpAudioClassifier's "nothing
    concerning heard." The language-preference pipeline (Tasks 3-7) runs
    end-to-end with this in place; swapping in the real client via
    get_translation_client_factory() is the only change needed to make it
    actually translate."""

    async def translate(self, text: str, target_language: str) -> str:
        return text
