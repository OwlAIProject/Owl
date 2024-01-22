from ..services import WhisperTranscriptionService, LLMService

async def process_session_from_audio(
    transcription_service: WhisperTranscriptionService,
    llm_service: LLMService,
    capture_filepath: str,
    voice_sample_filepath: str = None,
    speaker_name: str = None
):
    transcription = transcription_service.transcribe_audio(capture_filepath, voice_sample_filepath, speaker_name)
    summary = llm_service.summarize(transcription)
    print(summary)
    return summary