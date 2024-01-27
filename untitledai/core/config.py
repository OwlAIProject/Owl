from pydantic import BaseModel

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

# Temporary! To be replaced by the parameters for the actual endpointing service
class ConversationEndpointingConfiguration(BaseModel):
    timeout_interval: int
    min_utterances: int # The minimum number of utterances required to trigger an endpoint

class NotificationConfiguration(BaseModel):
    apn_team_id: str | None

class Configuration(BaseModel):
    transcription: TranscriptionConfiguration
    llm: LLMConfiguration
    captures: CapturesConfiguration
    deepgram: DeepgramConfiguration
    streaming_transcription: StreamingTranscriptionConfiguration
    async_transcription: AsyncTranscriptionConfiguration
    user: UserConfiguration
    database: DatabaseConfiguration
    conversation_endpointing: ConversationEndpointingConfiguration
    notification: NotificationConfiguration