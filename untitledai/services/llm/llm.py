from ...core.config import LLMConfig
from litellm import completion

def llm_completion(messages, model_override=None):
    model = model_override if model_override else LLMConfig.MODEL

    llm_params = {
        "model": model,
        "messages": messages
    }
    if hasattr(LLMConfig, 'API_BASE_URL'):
        llm_params["api_base"] = LLMConfig.API_BASE_URL
    if hasattr(LLMConfig, 'API_KEY'):
        llm_params["api_key"] = LLMConfig.API_KEY
        
    return completion(**llm_params)