from ...models.schemas import Transcription
from ...core.config import LLMConfig, UserConfig
from .llm import llm_completion

def summarize(transcription: Transcription) -> str:
    system_message =  f"""You are an world's most advanced AI assistant. You are given the transcript of an interaction. One of the participants is your client. Their name is {UserConfig.NAME}. The transcript includes speaker ids, but unfortunately sometimes we don't know the specific person name and sometimes they can be mislabeled. Do your best to infer the participants based on the context, but never referred to the speaker ids in the summary because they alone are not useful. Your job is to return a short summary of the interaction on behalf of {UserConfig.NAME} so they can remember what was happening. This is for {UserConfig.NAME}'s memories so please include anything that might be useful but also make it narrative so that it's helpful for creating a cherished memory. Format your summary with the following sections: Summary, Atmosphere, Key Take aways (bullet points)"""
    utterances = []
    for utterance in transcription.utterances:
        speaker = utterance.speaker
        text = utterance.text
        utterances.append(f"{speaker}: {text}")
    utterances = '\n'.join(utterances)
    user_message = f"Transcript:\n{utterances}"
    response = llm_completion(
        messages = [
            {"content": system_message, "role": "system"},
            {"content": user_message, "role": "user"}
        ]
    )
    return response.choices[0].message.content