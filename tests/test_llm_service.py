# pylint: disable=W0212,C0116,W0621
"""
Tests for the LLMService class.
"""

from typing import Any

import pytest
from litellm.utils import ModelResponse

from owl.core.config import Configuration
from owl.services.llm.llm_service import LLMService

CONFIG_FILE = ".config/sample-config.yaml"


@pytest.fixture
def config() -> Configuration:
    return Configuration.load_config_yaml(CONFIG_FILE)


@pytest.fixture
def llm_service(config) -> LLMService:
    return LLMService(config.llm)


@pytest.fixture
def mock_data() -> dict[str, Any]:
    # When `mock_response` is included, litellm will return a response object
    # without calling the LLM's api.
    # See, https://litellm.vercel.app/docs/completion/mock_requests
    content = "test content"
    return {
        "messages": [
            {"content": content, "role": "system"},
            {"content": content, "role": "user"},
        ],
        "mock_response": content,
    }


def test_llm_service_initialization(config, llm_service) -> None:
    assert llm_service._config == config.llm
    expected_api_base: str = f"{config.llm.base_url}:{config.llm.port}"
    assert llm_service._params["model"] == "ollama/mistral:instruct"
    assert llm_service._params["api_base"] == expected_api_base
    assert llm_service._params["api_key"] == config.llm.api_key


def test_llm_completion(llm_service, mock_data) -> None:
    mock_data["stream"] = False
    response: ModelResponse = llm_service.llm_completion(**mock_data)
    assert isinstance(response, ModelResponse)


@pytest.mark.asyncio
async def test_async_llm_completion(llm_service, mock_data) -> None:
    response: ModelResponse = await llm_service.async_llm_completion(**mock_data)
    assert isinstance(response, ModelResponse)
