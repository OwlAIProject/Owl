#
# llm.py
#
# LLM class: LLM abstraction layer. Performs LLM requests using a particular local or remote model.
#
from litellm import completion, acompletion
from ...core.config import LLMConfiguration
import logging

class LLMService:
    def __init__(self, config: LLMConfiguration):
        self._config = config
        self._model = config.model

    def llm_completion(self, messages, stream=False):
        logging.info(f"LLM completion request for model {self._model}...")
        llm_params = {
            "model": self._model,
            "messages": messages,
            "stream": stream
        }

        if self._config.api_base_url:
            llm_params["api_base"] = self._config.api_base_url
        if self._config.api_key:
            llm_params["api_key"] = self._config.api_key

        return completion(**llm_params)

    async def async_llm_completion(self, messages):
        logging.info(f"LLM completion request for model {self._model}...")
        llm_params = {
            "model": self._model,
            "messages": messages
        }

        if self._config.api_base_url:
            llm_params["api_base"] = self._config.api_base_url
        if self._config.api_key:
            llm_params["api_key"] = self._config.api_key

        return await acompletion(**llm_params)

