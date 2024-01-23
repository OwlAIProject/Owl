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

class Configuration(BaseModel):
    transcription: TranscriptionConfiguration
    llm: LLMConfiguration
    captures: CapturesConfiguration
    deepgram: DeepgramConfiguration
    streaming_transcription: StreamingTranscriptionConfiguration
    async_transcription: AsyncTranscriptionConfiguration
    user: UserConfiguration
    database: DatabaseConfiguration