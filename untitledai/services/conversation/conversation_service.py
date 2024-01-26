from ..stt.asynchronous.abstract_async_transcription_service import AbstractAsyncTranscriptionService
from ..conversation.transcript_summarizer import TranscriptionSummarizer  
from ...database.crud import create_transcription, create_conversation, find_most_common_location 
from ...database.database import Database
from ...core.config import Configuration
from ...models.schemas import Transcription, Conversation
from ...files import CaptureSessionFile
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
        
        # Parse the timestamp for start_time
        conversation_start_time = datetime.now()  # Default value
        if len(parts) > 0:
            timestamp_str = parts[0]
            try:
                conversation_start_time = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                conversation_start_time = conversation_start_time.replace(tzinfo=timezone.utc)

                logger.info(f"Conversation start parsed from file name: {conversation_start_time}")
            except ValueError:
                logger.error("Failed to parse timestamp from file name, using current time.")
        conversation_end_time = conversation_start_time + timedelta(seconds=audio_duration)

  
        # Parse the device name
        device_name = parts[1].split('.')[0] if len(parts) >= 2 else "Unknown"
        transcription.source_device = device_name
        transcription.source_device = device_name

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
    
    async def NEW_process_conversation_from_audio(self, session_file: CaptureSessionFile, voice_sample_filepath: str = None, speaker_name: str = None):
        logger.info(f"Processing session from audio file: {session_file.filepath}...")

        # Measure audio duration using Pydub
        audio = AudioSegment.from_file(session_file.filepath)
        audio_duration = len(audio) / 1000.0  # Duration in seconds

        # Start transcription timer
        start_time = time.time()

        transcription = await self.transcription_service.transcribe_audio(session_file.filepath, voice_sample_filepath, speaker_name)
        transcription.model = self.config.llm.model
        transcription.file_name = os.path.basename(session_file.filepath)
        transcription.duration = audio_duration
        transcription.source_device = session_file.device_type.value
        transcription.transcription_time = time.time() - start_time  # Transcription time
        logger.info(f"Transcription complete in {transcription.transcription_time:.2f} seconds")
        logger.info(f"Transcription: {transcription.utterances}")
                
        # Conversation start and end time
        conversation_start_time = session_file.timestamp
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