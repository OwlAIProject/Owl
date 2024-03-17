# pylint: disable=C0115
"""
Application configuration module.

This module defines various Pydantic models for representing different sections of the
application's configuration. The `Configuration` class loads configurations from a
YAML file and provides functionality to override loaded values with environment variables.
"""

from typing import Any, Self

from pydantic import BaseModel
from ruamel.yaml import YAML

from owl.core.utils.environment import apply_env_overrides, export_config_to_env


class UserConfiguration(BaseModel):
    name: str
    client_token: str
    voice_sample_filepath: str | None = None


class WebClientApiConfiguration(BaseModel):
    base_url: str
    port: int | None


class WebClientConfiguration(BaseModel):
    base_url: str
    port: int | None
    environment: str | None
    api: WebClientApiConfiguration


class LLMConfiguration(BaseModel):
    model: str
    base_url: str
    port: int | None
    api_key: str | None


class DatabaseConfiguration(BaseModel):
    url: str


class CapturesConfiguration(BaseModel):
    directory: str


class VADConfiguration(BaseModel):
    directory: str


class StreamingWhisperConfiguration(BaseModel):
    host: str
    port: int
    model: str
    language: str
    silero_sensitivity: float
    webrtc_sensitivity: int
    post_speech_silence_duration: float


class StreamingTranscriptionConfiguration(BaseModel):
    provider: str


class DeepgramConfiguration(BaseModel):
    api_key: str
    model: str
    language: str


class AsyncWhisperConfiguration(BaseModel):
    host: str
    port: int
    hf_token: str
    device: str
    compute_type: str
    batch_size: int
    model: str
    verification_threshold: float
    verification_model_source: str
    verification_model_directory: str


class AsyncTranscriptionConfiguration(BaseModel):
    provider: str


# TODO: Will be replaced by parameters for the actual endpointing service
class ConversationEndpointingConfiguration(BaseModel):
    timeout_seconds: int
    min_utterances: int


class NotificationConfiguration(BaseModel):
    apn_team_id: str | None


class UDPConfiguration(BaseModel):
    enabled: bool
    host: str | None
    port: int | None


class GoogleMapsConfiguration(BaseModel):
    api_key: str | None


class BingConfiguration(BaseModel):
    subscription_key: str | None


class PromptConfiguration(BaseModel):
    suggest_links_system_message: str
    summarization_system_message: str
    short_summarization_system_message: str


class Configuration(BaseModel):
    """
    Configuration for the Owl application.
    """

    user: UserConfiguration
    web: WebClientConfiguration
    llm: LLMConfiguration
    database: DatabaseConfiguration
    captures: CapturesConfiguration
    vad: VADConfiguration
    streaming_whisper: StreamingWhisperConfiguration
    streaming_transcription: StreamingTranscriptionConfiguration
    deepgram: DeepgramConfiguration
    async_whisper: AsyncWhisperConfiguration
    async_transcription: AsyncTranscriptionConfiguration
    conversation_endpointing: ConversationEndpointingConfiguration
    notification: NotificationConfiguration
    udp: UDPConfiguration
    bing: BingConfiguration
    prompt: PromptConfiguration

    @classmethod
    def load_config_yaml(cls, config_filepath: str) -> "Configuration":
        """
        Load configuration from YAML file and apply environment variable overrides.
        """
        yaml = YAML()
        with open(config_filepath, "r", encoding="utf-8") as f:
            config_data: Any = yaml.load(f)

        data: dict[Any, Any] = apply_env_overrides(config_data)
        config: Self = cls(**data)
        export_config_to_env(data)
        return config
