#
# llm.py
#
# LLM class: LLM abstraction layer. Performs LLM requests using a particular local or remote model.
#

from litellm import completion

from ...core.config import LLMConfiguration
from ...models.schemas import Transcription


class LLMService:
    def __init__(self, config: LLMConfiguration, model_override: str = None):
        self._config = config
        self._model = model_override if model_override else config.model
    
    def summarize(self, transcription: Transcription, system_message: str) -> str:
        utterances = []
        for utterance in transcription.utterances:
            speaker = utterance.speaker
            text = utterance.text
            utterances.append(f"{speaker}: {text}")
        utterances = '\n'.join(utterances)
        user_message = f"Transcript:\n{utterances}"
        response = self._completion(
            messages = [
                {"content": system_message, "role": "system"},
                {"content": user_message, "role": "user"}
            ]
        )
        return response.choices[0].message.content

    def _completion(self, messages):
        llm_params = {
            "model": self._model,
            "messages": messages
        }
        if self._config.api_base_url:
            llm_params["api_base"] = self._config.api_base_url
        if self._config.api_key:
            llm_params["api_key"] = self._config.api_key          
        return completion(**llm_params)