from ...models.schemas import Transcription
from ...services.llm.llm_service import LLMService
from ...core.config import Configuration
from ...prompts import summarization_system_message, short_summarization_system_message, suggest_links_system_message

class TranscriptionSummarizer:
    def __init__(self, config: Configuration):
        self._config = config
        self._llm_service = LLMService(config.llm)

    async def summarize(self, transcription: Transcription) -> str:
        system_message = summarization_system_message(config=self._config)

        utterances = [f"{utterance.speaker}: {utterance.text}" for utterance in transcription.utterances]
        user_message = "Transcript:\n" + "\n".join(utterances)

        response = await self._llm_service.async_llm_completion(
            messages=[
                {"content": system_message, "role": "system"},
                {"content": user_message, "role": "user"}
            ]
        )
        
        return response.choices[0].message.content
    
    async def short_summarize(self, transcription: Transcription) -> str:
        system_message = short_summarization_system_message(config=self._config)

        utterances = [f"{utterance.speaker}: {utterance.text}" for utterance in transcription.utterances]
        user_message = "Transcript:\n" + "\n".join(utterances)

        response = await self._llm_service.async_llm_completion(
            messages=[
                {"content": system_message, "role": "system"},
                {"content": user_message, "role": "user"}
            ]
        )
        
        return response.choices[0].message.content
    
    async def get_query_from_summary(self, summary: str) -> str:
        system_message = suggest_links_system_message(config=self._config)

        response = await self._llm_service.async_llm_completion(
            messages=[
                {"content": system_message, "role": "system"},
                {"content": summary, "role": "user"}
            ]
        )
        
        return response.choices[0].message.content