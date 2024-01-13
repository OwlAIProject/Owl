from ..transcription.whisper_transcription_service import transcribe_audio
from ..llm.session import summarize
import asyncio

async def process_session_from_audio(capture_filepath, voice_sample_filepath=None, speaker_name=None):
    transcription = transcribe_audio(capture_filepath, voice_sample_filepath, speaker_name)
    summary = summarize(transcription)
    print(summary)
    return summary