import os
import time
from pydub import AudioSegment
from datetime import datetime, timedelta
import logging

from ..stt.asynchronous.abstract_async_transcription_service import AbstractAsyncTranscriptionService
from ..conversation.transcript_summarizer import TranscriptionSummarizer  
from ...database.crud import create_transcription, create_conversation, find_most_common_location, create_capture_file_segment_file_ref, update_conversation_state, get_conversation_by_conversation_uuid, get_capturing_conversation_by_capture_uuid 
from ...database.database import Database
from ...core.config import Configuration
from ...models.schemas import Transcription, Conversation, ConversationState, Capture, CaptureSegment, TranscriptionRead, ConversationRead, SuggestedLink
from ...files import CaptureDirectory

logger = logging.getLogger(__name__)

class ConversationService:
    def __init__(self, config: Configuration, database: Database, transcription_service: AbstractAsyncTranscriptionService, notification_service, bing_search_service=None):
        self._config = config
        self._database = database
        self._transcription_service = transcription_service
        self._notification_service = notification_service
        self._summarizer = TranscriptionSummarizer(config)
        self._bing_search_service = bing_search_service

    async def create_conversation(self, conversation_uuid: str, start_time: datetime, capture_file: Capture) -> Conversation:
        with next(self._database.get_db()) as db:
            # Create segment file
            segment_file = CaptureSegment(
                conversation_uuid=conversation_uuid,
                start_time=start_time,
                filepath=CaptureDirectory(config=self._config).get_capture_segment_filepath(capture_file=capture_file, conversation_uuid=conversation_uuid, timestamp=start_time),
                source_capture_id=capture_file.id   # database IDs to link segments to their parent captures
            )
            saved_segment_file = create_capture_file_segment_file_ref(db=db, capture_file_segment_file=segment_file)

            # Transcription object
            realtime_transcript = Transcription(
                    realtime=True,
                    model=self._config.streaming_transcription.provider,
                    file_name=saved_segment_file.filepath,
                    utterances=[],
                    transcription_time=saved_segment_file.start_time.timestamp(),
            )

            # Conversation object, enter into database
            conversation = Conversation(
                conversation_uuid=saved_segment_file.conversation_uuid,
                capture_segment_file=saved_segment_file,
                device_type=capture_file.device_type,
                start_time=saved_segment_file.start_time,
                end_time=None,
                transcriptions=[realtime_transcript]
            )
            saved_conversation = create_conversation(db=db, conversation=conversation)
 
            await self._notification_service.send_notification("New Conversation", "New conversation detected.", "new_conversation", payload=ConversationRead.from_orm(conversation).model_dump_json(indent=2))
            return saved_conversation
        
    def get_conversation(self, conversation_uuid: str) -> Conversation | None:
        with next(self._database.get_db()) as db:
            return get_conversation_by_conversation_uuid(db, conversation_uuid)
        
    def get_capturing_conversation(self, capture_uuid: str) -> Conversation | None:
        with next(self._database.get_db()) as db:
            return get_capturing_conversation_by_capture_uuid(db, capture_uuid)
        
    async def fail_processing_and_capturing_conversations(self):
        with next(self._database.get_db()) as db:
            conversations_to_update = db.query(Conversation).filter(Conversation.state.in_([ConversationState.CAPTURING, ConversationState.PROCESSING])).all()
            for conversation in conversations_to_update:
                conversation.state = ConversationState.FAILED_PROCESSING
                await self._notification_service.send_notification("Conversation Failure", "A conversation failed to process.", "update_conversation", payload=ConversationRead.from_orm(conversation).model_dump_json(indent=2))
            db.commit()

    async def process_conversation_from_audio(self, conversation_uuid: str, voice_sample_filepath: str = None, speaker_name: str = None):
        try:
            with next(self._database.get_db()) as db:
                conversation = get_conversation_by_conversation_uuid(db, conversation_uuid)
                update_conversation_state(db, conversation.id, ConversationState.PROCESSING)
                conversation.state = ConversationState.PROCESSING
                await self._notification_service.send_notification("Conversation Processing", "A conversation has begun processing.", "update_conversation", payload=ConversationRead.from_orm(conversation).model_dump_json(indent=2))

                logger.info(f"Processing conversation...")
                # Segment audio and duration
                audio = AudioSegment.from_file(conversation.capture_segment_file.filepath)
                audio_duration = len(audio) / 1000.0  # Duration in seconds

                # Total capture audio duration
                capture_audio = AudioSegment.from_file(conversation.capture_segment_file.source_capture.filepath)
                capture_audio_duration = len(capture_audio) / 1000.0  # Duration in seconds

                # Conversation start and end time
                conversation_start_time = conversation.capture_segment_file.start_time
                conversation_end_time = conversation_start_time + timedelta(seconds=audio_duration)

                # Start transcription timer
                start_time = time.time()

                transcription = await self._transcription_service.transcribe_audio(conversation.capture_segment_file.filepath, voice_sample_filepath, speaker_name)
                transcription.transcription_time = time.time() - start_time  # Transcription time
                logger.info(f"Transcription complete in {transcription.transcription_time:.2f} seconds")
                logger.info(f"Transcription: {transcription.utterances}")
                if not transcription.utterances:
                    logger.info("No utterances found in the transcription. Skipping conversation processing.")
                    deleted_data = ConversationRead.from_orm(conversation)
                    db.delete(conversation)
                    db.commit()
                    serialized_payload = deleted_data.json() 
                    await self._notification_service.send_notification("Empty Conversation", "An empty conversation was deleted", "delete_conversation", payload=serialized_payload)
                    return None, None  

                for utterance in transcription.utterances:
                    utterance.spoken_at = conversation_start_time + timedelta(seconds=utterance.start)

                start_time = time.time()
                conversation.summarization_model = self._config.llm.model
                summary_text = await self._summarizer.summarize(transcription)
                logger.info(f"Summarization complete in {time.time() - start_time:.2f} seconds")
                logger.info(f"Summary generated: {summary_text}")


                start_time = time.time()
                short_summary_text = await self._summarizer.short_summarize(transcription)
                logger.info(f"Short summarization complete in {time.time() - start_time:.2f} seconds")
                logger.info(f"Short summary generated: {short_summary_text}")

                # Update durations
                conversation.capture_segment_file.source_capture.duration = capture_audio_duration
                conversation.capture_segment_file.duration = audio_duration

                saved_transcription = create_transcription(db, transcription)

                # Create and save conversation
                most_common_location = find_most_common_location(db, conversation_start_time, conversation_end_time, conversation.capture_segment_file.source_capture.capture_uuid)
                if most_common_location:
                    logger.info(f"Identified conversation primary location: {most_common_location}")

                suggested_links = []
                if self._bing_search_service:
                    query = await self._summarizer.get_query_from_summary(summary_text)
                    logger.info(f"Searching for suggested links: {query}")
                    bing_results = await self._bing_search_service.search(query)
                    for result in bing_results.webPages.value:
                        suggested_links.append(SuggestedLink(url=str(result.url)))

                conversation.end_time = conversation_end_time
                conversation.summary = summary_text
                conversation.short_summary = short_summary_text
                conversation.start_time = conversation_start_time
                conversation.transcriptions.append(saved_transcription)
                conversation.primary_location_id = most_common_location.id if most_common_location else None
                conversation.suggested_links = suggested_links
        
                # Link transcription to conversation
                saved_transcription.conversation_id = conversation.id
                conversation.state = ConversationState.COMPLETED

                # Save files for easy debugging and inspection
                transcription_data = TranscriptionRead.from_orm(saved_transcription)
                conversation_data = ConversationRead.from_orm(conversation)

                transcription_json = transcription_data.model_dump_json(indent=2)
                conversation_json = conversation_data.model_dump_json(indent=2)
                
                transcription_json_filepath = CaptureDirectory(config=self._config).get_transcription_filepath(segment_file=conversation.capture_segment_file)
                with open(transcription_json_filepath, 'w') as file:
                    file.write(transcription_json)

                conversation_json_filepath = CaptureDirectory(config=self._config).get_conversation_filepath(segment_file=conversation.capture_segment_file)
                with open(conversation_json_filepath, 'w') as file:
                    file.write(conversation_json)
                    
                summary_snippet = summary_text[:100] + (summary_text[100:] and '...')
                await self._notification_service.send_notification("New Conversation Summary", summary_snippet, "update_conversation", payload=conversation_json)
                
                db.commit()
            
        except Exception as e:
            logger.error(f"Error processing conversation: {e}")
            if conversation_uuid is not None and conversation:
                update_conversation_state(db, conversation.id, ConversationState.FAILED_PROCESSING)
            raise e  
        finally:
            db.commit() 
        return transcription, conversation
