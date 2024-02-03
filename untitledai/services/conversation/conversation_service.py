from ..stt.asynchronous.abstract_async_transcription_service import AbstractAsyncTranscriptionService
from ..conversation.transcript_summarizer import TranscriptionSummarizer  

from ...database.crud import create_transcription, create_conversation, find_most_common_location, create_capture_file_ref, create_segmented_capture_file,get_capture_file_ref  
from ...database.database import Database
from ...core.config import Configuration
from ...models.schemas import Transcription, Conversation, CaptureFileRef, SegmentedCaptureFile, TranscriptionRead, ConversationRead
from ...files import CaptureFile, CaptureSegmentFile
import asyncio
import os
import time
from datetime import timezone
from pydub import AudioSegment
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ConversationService:
    def __init__(self, config: Configuration, database: Database, transcription_service: AbstractAsyncTranscriptionService, notification_service):
        self._config = config
        self._database = database
        self._transcription_service = transcription_service
        self._notification_service = notification_service
        self._summarizer = TranscriptionSummarizer(config)
   
    async def process_conversation_from_audio(self, capture_file: CaptureFile, segment_file: CaptureSegmentFile, voice_sample_filepath: str = None, speaker_name: str = None):
        logger.info(f"Processing capture from audio file: {segment_file.filepath}...")

        # Segment audio and duration
        audio = AudioSegment.from_file(segment_file.filepath)
        audio_duration = len(audio) / 1000.0  # Duration in seconds

        # Total capture audio duration
        capture_audio = AudioSegment.from_file(capture_file.filepath)
        capture_audio_duration = len(capture_audio) / 1000.0  # Duration in seconds

        # Start transcription timer
        start_time = time.time()

        transcription = await self._transcription_service.transcribe_audio(segment_file.filepath, voice_sample_filepath, speaker_name)
        transcription.model = self._config.llm.model
        transcription.transcription_time = time.time() - start_time  # Transcription time
        logger.info(f"Transcription complete in {transcription.transcription_time:.2f} seconds")
        logger.info(f"Transcription: {transcription.utterances}")
        if not transcription.utterances:
            logger.info("No utterances found in the transcription. Skipping conversation processing.")
            return None, None  

        # Conversation start and end time
        conversation_start_time = segment_file.timestamp
        conversation_end_time = conversation_start_time + timedelta(seconds=audio_duration)

        start_time = time.time()
        summary_text = await self._summarizer.summarize(transcription)
        logger.info(f"Summarization complete in {time.time() - start_time:.2f} seconds")
        logger.info(f"Summary generated: {summary_text}")
        with next(self._database.get_db()) as db:
            try:
                # Create and save capture file reference if not exists or update duration if exists
                saved_capture_file_ref = get_capture_file_ref(db, capture_file.capture_uuid)
                if not saved_capture_file_ref:
                    saved_capture_file_ref = create_capture_file_ref(db, CaptureFileRef(
                        capture_uuid=capture_file.capture_uuid,
                        file_path=capture_file.filepath,
                        duration=capture_audio_duration,
                        device_type=capture_file.device_type.value,
                        start_time=capture_file.timestamp
                    )) 
                else:
                    saved_capture_file_ref.duration = capture_audio_duration

                # Create and save segmented capture file
                saved_segmented_capture = create_segmented_capture_file(db,SegmentedCaptureFile(
                    segment_path=segment_file.filepath,
                    source_capture_id=saved_capture_file_ref.id,
                    duration=audio_duration,
                ))

                transcription.segmented_capture_id = saved_segmented_capture.id
                saved_transcription = create_transcription(db, transcription)
    
                # Create and save conversation
                most_common_location = find_most_common_location(db, conversation_start_time, conversation_end_time, capture_file.capture_uuid)
                if most_common_location:
                    logger.info(f"Identified conversation primary location: {most_common_location}")

                conversation = create_conversation(db, Conversation(
                    summary=summary_text, 
                    start_time=conversation_start_time,
                    transcriptions=[saved_transcription],
                    primary_location_id=most_common_location.id if most_common_location else None
                )) 

                # Link transcription to conversation
                saved_transcription.conversation_id = conversation.id
                
                # Save files for easy debugging and inspection
                transcription_data = TranscriptionRead.from_orm(saved_transcription)
                conversation_data = ConversationRead.from_orm(conversation)

                transcription_json = transcription_data.model_dump_json(indent=2)
                conversation_json = conversation_data.model_dump_json(indent=2)

                with open(segment_file.get_transcription_filepath(), 'w') as file:
                    file.write(transcription_json)

                with open(segment_file.get_conversation_filepath(), 'w') as file:
                    file.write(conversation_json)
                    
                summary_snippet = summary_text[:100] + (summary_text[100:] and '...')
                await self._notification_service.send_notification("New Conversation", summary_snippet, "new_conversation", payload=conversation_json)
                
                db.commit()
                return transcription, conversation
            except Exception as e:
                logger.error(f"Error in database operations: {e}")
        
