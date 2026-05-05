from __future__ import annotations

from typing import Sequence

from scrybe_api.config import Settings
from scrybe_api.schemas.common import ImageRecord

try:
    from openai import AsyncOpenAI
except ModuleNotFoundError:
    AsyncOpenAI = None


class OpenAIEnricher:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: AsyncOpenAI | None = None

    def is_configured(self) -> bool:
        return bool(self.settings.openai_api_key and AsyncOpenAI is not None)

    def _client_or_none(self) -> AsyncOpenAI | None:
        if not self.is_configured():
            return None
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
            )
        return self._client

    async def caption_images(self, images: Sequence[ImageRecord]) -> list[ImageRecord]:
        client = self._client_or_none()
        if client is None or not images:
            return list(images)

        updated: list[ImageRecord] = []
        for image in images:
            response = await client.responses.create(
                model=self.settings.openai_model,
                input=f"Provide a concise caption for this image URL for markdown alt text: {image.url}",
            )
            caption = getattr(response, "output_text", "") or image.alt_text or "Image"
            updated.append(
                ImageRecord(url=image.url, alt_text=image.alt_text, caption=caption.strip())
            )
        return updated

    async def summarize(self, markdown: str) -> str | None:
        client = self._client_or_none()
        if client is None or not markdown.strip():
            return None
        response = await client.responses.create(
            model=self.settings.openai_model,
            input=(
                "Summarize the following document into concise structured bullets for an LLM."
                f"\n\n{markdown[:12000]}"
            ),
        )
        return getattr(response, "output_text", None)
