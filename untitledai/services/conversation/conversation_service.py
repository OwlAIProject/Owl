from ..stt.asynchronous.abstract_async_transcription_service import AbstractAsyncTranscriptionService
from ..conversation.transcript_summarizer import TranscriptionSummarizer  
from ...database.crud import create_transcription, create_conversation, find_most_common_location 
from ...database.database import Database
from ...core.config import Configuration
from ...models.schemas import Transcription, Conversation
from ...files import CaptureFile
import asyncio
import os
import time
from datetime import timezone
from pydub import AudioSegment
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ConversationService:
    def __init__(self, config: Configuration, database: Database, transcription_service: AbstractAsyncTranscriptionService):
        self.config = config
        self.database = database
        self.transcription_service = transcription_service
        self.summarizer = TranscriptionSummarizer(config)
   
    async def process_conversation_from_audio(self, capture_file: CaptureFile, voice_sample_filepath: str = None, speaker_name: str = None):
        logger.info(f"Processing capture from audio file: {capture_file.filepath}...")

        # Measure audio duration using Pydub
        audio = AudioSegment.from_file(capture_file.filepath)
        audio_duration = len(audio) / 1000.0  # Duration in seconds

        # Start transcription timer
        start_time = time.time()

        transcription = await self.transcription_service.transcribe_audio(capture_file.filepath, voice_sample_filepath, speaker_name)
        transcription.model = self.config.llm.model
        transcription.file_name = os.path.basename(capture_file.filepath)
        transcription.duration = audio_duration
        transcription.source_device = capture_file.device_type.value
        transcription.transcription_time = time.time() - start_time  # Transcription time
        logger.info(f"Transcription complete in {transcription.transcription_time:.2f} seconds")
        logger.info(f"Transcription: {transcription.utterances}")
                
        # Conversation start and end time
        conversation_start_time = capture_file.timestamp
        conversation_end_time = conversation_start_time + timedelta(seconds=audio_duration)

        start_time = time.time()
        summary_text = await self.summarizer.summarize(transcription)
        logger.info(f"Summarization complete in {time.time() - start_time:.2f} seconds")
        logger.info(f"Summary generated: {summary_text}")
        with next(self.database.get_db()) as db:
            try:
                most_common_location = find_most_common_location(db, conversation_start_time, conversation_end_time)
                if most_common_location:
                    logger.info(f"Identified conversation primary location: {most_common_location}")
                saved_transcription = create_transcription(db, transcription)
                conversation = Conversation(
                    summary=summary_text, 
                    start_time=conversation_start_time, 
                    transcriptions=[saved_transcription],
                    primary_location_id=most_common_location.id if most_common_location else None
                )
                saved_conversation = create_conversation(db, conversation)

            except Exception as e:
                logging.error(f"Error in database operations: {e}")
        return saved_transcription, saved_conversation