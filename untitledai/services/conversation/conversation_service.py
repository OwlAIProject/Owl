from ..stt.asynchronous.abstract_async_transcription_service import AbstractAsyncTranscriptionService
from ..conversation.transcript_summarizer import TranscriptionSummarizer  

from ...database.crud import create_transcription, create_conversation, find_most_common_location, create_capture_file_ref, create_segmented_capture_file,get_capture_file_ref  
from ...database.database import Database
from ...core.config import Configuration
from ...models.schemas import Transcription, Conversation, CaptureFileRef, SegmentedCaptureFile, TranscriptionRead, ConversationRead
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
    def __init__(self, config: Configuration, database: Database, transcription_service: AbstractAsyncTranscriptionService, notification_service):
        self.config = config
        self.database = database
        self.transcription_service = transcription_service
        self.notification_service = notification_service
        self.summarizer = TranscriptionSummarizer(config)
   
    async def process_conversation_from_audio(self, capture_file: CaptureFile, segment_file_path: str = None, voice_sample_filepath: str = None, speaker_name: str = None):
        if not segment_file_path:
            segment_file_path = capture_file.filepath
        logger.info(f"Processing capture from audio file: {segment_file_path}...")

        # Measure audio duration using Pydub
        audio = AudioSegment.from_file(segment_file_path)
        audio_duration = len(audio) / 1000.0  # Duration in seconds

        capture_audio = AudioSegment.from_file(capture_file.filepath)
        capture_audio_duration = len(capture_audio) / 1000.0  # Duration in seconds

        # Start transcription timer
        start_time = time.time()

        transcription = await self.transcription_service.transcribe_audio(segment_file_path, voice_sample_filepath, speaker_name)
        transcription.model = self.config.llm.model
        transcription.transcription_time = time.time() - start_time  # Transcription time
        logger.info(f"Transcription complete in {transcription.transcription_time:.2f} seconds")
        logger.info(f"Transcription: {transcription.utterances}")
                
        # Conversation start and end time
        conversation_start_time = capture_file.timestamp  #  todo: add offset
        conversation_end_time = conversation_start_time + timedelta(seconds=audio_duration)

        start_time = time.time()
        summary_text = await self.summarizer.summarize(transcription)
        logger.info(f"Summarization complete in {time.time() - start_time:.2f} seconds")
        logger.info(f"Summary generated: {summary_text}")
        with next(self.database.get_db()) as db:
            try:
                # Create and save capture file reference
                saved_capture_file_ref = get_capture_file_ref(db, capture_file.capture_uuid)
                if not saved_capture_file_ref:
                    saved_capture_file_ref = create_capture_file_ref(db, CaptureFileRef(
                        capture_uuid=capture_file.capture_uuid,
                        file_path=capture_file.filepath,
                        duration=capture_audio_duration,
                        device_type=capture_file.device_type.value,
                        start_time=capture_file.timestamp
                    )) 

                # Create and save segmented capture file
                saved_segmented_capture = create_segmented_capture_file(db,SegmentedCaptureFile(
                    segment_path=segment_file_path,
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
                
                # Save files for easy debugging
                # TODO file paths
                segment_file_base_name = os.path.splitext(os.path.basename(segment_file_path))[0]
                transcription_data = TranscriptionRead.from_orm(saved_transcription)
                conversation_data = ConversationRead.from_orm(conversation)

                transcription_json = transcription_data.model_dump_json(indent=2)
                conversation_json = conversation_data.model_dump_json(indent=2)

                capture_file_directory = os.path.dirname(capture_file.filepath)
                transcription_file_path = os.path.join(capture_file_directory, f"{segment_file_base_name}_transcription.json")
                conversation_file_path = os.path.join(capture_file_directory, f"{segment_file_base_name}_conversation.json")

                with open(transcription_file_path, 'w') as file:
                    file.write(transcription_json)

                with open(conversation_file_path, 'w') as file:
                    file.write(conversation_json)
                    
                summary_snippet = summary_text[:100] + (summary_text[100:] and '...')
                await self.notification_service.send_notification("New Conversation", summary_snippet, "new_conversation", payload=conversation_json)
                
                db.commit()
                return transcription, conversation
            except Exception as e:
                logger.error(f"Error in database operations: {e}")
        
