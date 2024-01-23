from ...models.schemas import Transcription
from ...services.llm.llm_service import LLMService
from ...core.config import Configuration

class TranscriptionSummarizer:
    def __init__(self, config: Configuration):
        self.config = config
        self._llm_service = LLMService(config.llm)

    async def summarize(self, transcription: Transcription) -> str:
        system_message = f"""You are an world's most advanced AI assistant. You are given the transcript of an interaction. One of the participants is your client. Their name is {self.config.user.name}. The transcript includes speaker ids, but unfortunately sometimes we don't know the specific person name and sometimes they can be mislabeled. Do your best to infer the participants based on the context, but never referred to the speaker ids in the summary because they alone are not useful. Your job is to return a short summary of the interaction on behalf of {self.config.user.name} so they can remember what was happening. This is for {self.config.user.name}'s memories so please include anything that might be useful but also make it narrative so that it's helpful for creating a cherished memory. Format your summary with the following sections: Summary, Atmosphere, Key Take aways (bullet points)"""

        utterances = [f"{utterance.speaker}: {utterance.text}" for utterance in transcription.utterances]
        user_message = "Transcript:\n" + "\n".join(utterances)

        response = await self._llm_service.async_llm_completion(
            messages=[
                {"content": system_message, "role": "system"},
                {"content": user_message, "role": "user"}
            ]
        )
        
        return response.choices[0].message.content
