"""
LLM abstraction layer.
"""

import logging
from typing import Any

from litellm import acompletion, completion
from litellm.utils import CustomStreamWrapper, ModelResponse

from owl.core.config import LLMConfiguration

logger: logging.Logger = logging.getLogger(__name__)


class LLMService:
    """A service class for performing LLM completions."""

    def __init__(self, config: LLMConfiguration) -> None:
        """
        Initialize the LLMService with the given configuration.
        """
        self._config: LLMConfiguration = config
        self._params: dict[str, Any] = {
            "model": config.model,
            "api_base": f"{config.base_url}{f':{config.port}' if config.port else ''}",
            "api_key": config.api_key,
        }

    def _prepare_request(
        self, messages: Any, stream: bool = False, **kwargs
    ) -> dict[str, Any]:
        """
        Prepare the parameters for the LLM completion request.
        """
        logger.info("LLM completion request for model %s...", self._params["model"])
        params: dict[str, Any] = self._params.copy()
        params.update({"messages": messages, "stream": stream, **kwargs})
        return params

    def llm_completion(
        self, messages: Any, stream: bool = False, **kwargs
    ) -> ModelResponse | CustomStreamWrapper:
        """
        Perform an LLM completion request.
        """
        request: dict[str, Any] = self._prepare_request(messages, stream, **kwargs)
        return completion(**request)

    async def async_llm_completion(self, messages: Any, **kwargs) -> Any:
        """
        Perform an asynchronous LLM completion request.
        """
        request: dict[str, Any] = self._prepare_request(messages, **kwargs)
        return await acompletion(**request)
