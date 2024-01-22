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
    api_base_url: str
    api_key: str

class CapturesConfiguration(BaseModel):
    capture_dir: str

class UserConfiguration(BaseModel):
    name: str

class Configuration(BaseModel):
    transcription: TranscriptionConfiguration
    llm: LLMConfiguration
    captures: CapturesConfiguration
    user: UserConfiguration