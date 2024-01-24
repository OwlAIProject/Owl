from ..stt.asynchronous.abstract_async_transcription_service import AbstractAsyncTranscriptionService
from ..conversation.transcript_summarizer import TranscriptionSummarizer  
from ...database.crud import create_transcription, create_conversation 
from ...database.database import Database
from ...core.config import Configuration
from ...models.schemas import Transcription, Conversation
import asyncio
import os
import time
from pydub import AudioSegment
import logging

logger = logging.getLogger(__name__)

class ConversationService:
    def __init__(self, config: Configuration, database: Database, transcription_service: AbstractAsyncTranscriptionService):
        self.config = config
        self.database = database
        self.transcription_service = transcription_service
        self.summarizer = TranscriptionSummarizer(config)

    async def process_conversation_from_audio(self, capture_filepath, voice_sample_filepath=None, speaker_name=None):
        logger.info("Processing session from audio...")

        # Measure audio duration using Pydub
        audio = AudioSegment.from_file(capture_filepath)
        audio_duration = len(audio) / 1000.0  # Duration in seconds

        # Start transcription timer
        start_time = time.time()

        transcription = await self.transcription_service.transcribe_audio(capture_filepath, voice_sample_filepath, speaker_name)

        transcription.model = self.config.llm.model
        transcription.file_name = capture_filepath
        transcription.duration = audio_duration
        transcription.transcription_time = time.time() - start_time  # Transcription time
        logger.info(f"Transcription complete in {transcription.transcription_time:.2f} seconds")
        logger.info(f"Transcription: {transcription.utterances}")
        # should we explicitly pass the device or infer from filename convention?
        file_name = os.path.basename(capture_filepath)
        parts = file_name.split('_')
        if len(parts) >= 2:
            device_name = parts[1].split('.')[0] 
        else:
            device_name = "Unknown"
        transcription.source_device = device_name

        start_time = time.time()
        summary_text = await self.summarizer.summarize(transcription)
        logger.info(f"Summarization complete in {time.time() - start_time:.2f} seconds")
        logger.info(f"Summary generated: {summary_text}")
        with next(self.database.get_db()) as db:
            try:
                saved_transcription = create_transcription(db, transcription)
                conversation = Conversation(summary=summary_text, transcriptions=[saved_transcription])
                saved_conversation = create_conversation(db, conversation)

            except Exception as e:
                logging.error(f"Error in database operations: {e}")
        return saved_transcription, saved_conversation