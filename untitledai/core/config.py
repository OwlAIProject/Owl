from pydantic import BaseModel
import yaml
import os
from typing import Optional

class TranscriptionConfiguration(BaseModel):
    hf_token: str
    device: str
    compute_type: str
    batch_size: int
    model: str
    verification_threshold: float
    verification_model_source: str
    verification_model_savedir: str

class LLMConfiguration(BaseModel):
    model: str
    api_base_url: str | None
    api_key: str | None

class CapturesConfiguration(BaseModel):
    capture_dir: str

class UserConfiguration(BaseModel):
    name: str
    client_token: str
    voice_sample_filepath: Optional[str] = None

class DeepgramConfiguration(BaseModel):
    api_key: str
    model: str
    language: str

class StreamingTranscriptionConfiguration(BaseModel):
    provider: str
    
class AsyncTranscriptionConfiguration(BaseModel):
    provider: str
    
class DatabaseConfiguration(BaseModel):
    url: str

class VADConfiguration(BaseModel):
    vad_model_savedir: str

# Temporary! To be replaced by the parameters for the actual endpointing service
class ConversationEndpointingConfiguration(BaseModel):
    timeout_interval: int
    min_utterances: int # The minimum number of utterances required to trigger an endpoint

class NotificationConfiguration(BaseModel):
    apn_team_id: str | None

class Configuration(BaseModel):

    @classmethod
    def load_config_yaml(cls, config_file_path: str) -> 'Configuration':
        """
        Load configuration from YAML file and apply environment variable overrides.
        """
        with open(config_file_path, 'r') as stream:
            config_data = yaml.safe_load(stream)

        # Apply environment variable overrides
        for section, section_config in config_data.items():
            for key, val in section_config.items():
                env_var = os.environ.get(f"UNTITLEDAI_{section.upper()}_{key.upper()}")
                if env_var:
                    config_data[section][key] = env_var

        return cls(**config_data)

    
    transcription: TranscriptionConfiguration
    llm: LLMConfiguration
    captures: CapturesConfiguration
    vad: VADConfiguration
    deepgram: DeepgramConfiguration
    streaming_transcription: StreamingTranscriptionConfiguration
    async_transcription: AsyncTranscriptionConfiguration
    user: UserConfiguration
    database: DatabaseConfiguration
    conversation_endpointing: ConversationEndpointingConfiguration
    notification: NotificationConfiguration