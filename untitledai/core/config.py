class TranscriptionConfig:
    HF_AUTH_TOKEN = "hugging_face_token"
    # DEVICE = "cuda"
    # COMPUTE_TYPE = "float16"
    DEVICE = "cpu" # for local
    COMPUTE_TYPE = "int8" # for local
    BATCH_SIZE = 16 # might need to be lowered for local if you don't have enough memory
    MODEL_NAME = "large-v2" # this is slow local but better accuracy
    VERIFICATION_THRESHOLD = 0.1
    VERIFICATION_MODEL_SOURCE = "speechbrain/spkrec-ecapa-voxceleb"
    VERIFICATION_MODEL_SAVEDIR = "pretrained_models/spkrec-ecapa-voxceleb"

class LLMConfig:
    # API_KEY = "sk-" 
    # MODEL = "gpt-3.5-turbo"
    # MODEL = "gpt-4"

    MODEL = "ollama/llama2"
    API_BASE_URL = "http://localhost:11434" 

class UserConfig:
    NAME = "Bob"