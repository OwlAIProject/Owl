from .abstract_async_transcription_service import AbstractAsyncTranscriptionService
from typing import Optional
import asyncio
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    PrerecordedOptions,
    FileSource,
)
import logging
from ....models.schemas import Transcription, Utterance, Word

logger = logging.getLogger(__name__)

class AsyncDeepgramTranscriptionService(AbstractAsyncTranscriptionService):
    def __init__(self, config):
        self.config = config
        self.deepgram_client = DeepgramClient(api_key=config.api_key)

    async def transcribe_audio(self, main_audio_filepath, voice_sample_filepath=None, speaker_name=None) -> Transcription:
        with open(main_audio_filepath, 'rb') as audio:
            audio_data = audio.read()
        logger.info(f"Transcribing audio file: {main_audio_filepath}")    
        response = await self._transcribe_with_deepgram(audio_data)

        return self._convert_to_transcription_model(response, main_audio_filepath)

    async def _transcribe_with_deepgram(self, audio: bytes) -> dict:
        payload: FileSource = {
            "buffer": audio,
        }

        options = PrerecordedOptions(
            model=self.config.model,
            smart_format=True,
            utterances=True,
            punctuate=True,
            diarize=True,
        )

        def synchronous_transcribe():
            return self.deepgram_client.listen.prerecorded.v("1").transcribe_file(payload, options)

        try:
            logger.info("Transcribing with Deepgram...")
            response = await asyncio.get_event_loop().run_in_executor(None, synchronous_transcribe)
            logger.info("Deepgram transcription complete.")
            return response
        except Exception as e:
            logger.error(f"An error occurred during transcription: {e}")
            raise

    def _convert_to_transcription_model(self, response, file_name: str) -> Transcription:
        logger.info("Converting Deepgram response to Transcription model...")

        try:
            duration = response.metadata.duration if response.metadata else 0

            transcription = Transcription(
                model='Deepgram',
                file_name=file_name,
                duration=duration,
                utterances=[]
            )

            if hasattr(response, 'results') and hasattr(response.results, 'utterances'):
                for utterance in response.results.utterances:
                    new_utterance = Utterance(
                        start=utterance.start,
                        end=utterance.end,
                        text=utterance.transcript,
                        speaker=utterance.speaker,
                        words=[]
                    )

                    for word in utterance.words:
                        new_word = Word(
                            word=word.word,
                            start=word.start,
                            end=word.end,
                            score=word.confidence,
                            speaker=new_utterance.speaker
                        )
                        new_utterance.words.append(new_word)

                    transcription.utterances.append(new_utterance)

            logger.info("Conversion complete. Transcription object created.")
            return transcription
        except Exception as e:
            logger.error(f"An error occurred during model conversion: {e}")
            raise