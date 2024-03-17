from typing import Any

from ...core.config import Configuration
from ...models.schemas import Transcription
from ...services.llm.llm_service import LLMService


class TranscriptionSummarizer:
    def __init__(self, config: Configuration) -> None:
        self._config: Configuration = config
        self._llm_service = LLMService(config.llm)

        self._suggest_links_system_message: str = (
            self._config.prompt.suggest_links_system_message.format(config=self._config)
        )
        self._summarization_system_message: str = (
            self._config.prompt.summarization_system_message.format(config=self._config)
        )
        self._short_summarization_system_message: str = (
            self._config.prompt.short_summarization_system_message.format(
                config=self._config
            )
        )

    async def summarize(self, transcription: Transcription) -> str:
        utterances: list[str] = [
            f"{utterance.speaker}: {utterance.text}"
            for utterance in transcription.utterances
        ]
        user_message: str = "Transcript:\n" + "\n".join(utterances)
        response: Any = await self._llm_service.async_llm_completion(
            messages=[
                {"content": self._summarization_system_message, "role": "system"},
                {"content": user_message, "role": "user"},
            ]
        )
        return response.choices[0].message.content

    async def short_summarize(self, transcription: Transcription) -> str:
        utterances: list[str] = [
            f"{utterance.speaker}: {utterance.text}"
            for utterance in transcription.utterances
        ]
        user_message: str = "Transcript:\n" + "\n".join(utterances)
        response: Any = await self._llm_service.async_llm_completion(
            messages=[
                {"content": self._short_summarization_system_message, "role": "system"},
                {"content": user_message, "role": "user"},
            ]
        )
        return response.choices[0].message.content

    async def get_query_from_summary(self, summary: str) -> str:
        response: Any = await self._llm_service.async_llm_completion(
            messages=[
                {"content": self._suggest_links_system_message, "role": "system"},
                {"content": summary, "role": "user"},
            ]
        )
        return response.choices[0].message.content
