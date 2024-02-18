from deepgram import (
    DeepgramClient,
    PrerecordedOptions,
    FileSource,
)
import httpx
import logging

from .abstract_async_transcription_service import AbstractAsyncTranscriptionService
from ....models.schemas import Transcription, Utterance, Word

logger = logging.getLogger(__name__)

class AsyncDeepgramTranscriptionService(AbstractAsyncTranscriptionService):
    def __init__(self, config):
        self._config = config
        self._deepgram_client = DeepgramClient(api_key=config.api_key)

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
            model=self._config.model,
            smart_format=True,
            utterances=True,
            punctuate=True,
            diarize=True,
        )

        # Default timeout of 10 seconds to connect, 10 minutes for upload/download. We can also try
        # Timeout(None, connect=10) for no timeout at all but this is risky. Better to eventually
        # turn this into a proper retry loop.
        timeout = httpx.Timeout(600.0, connect=10.0)

        try:
            logger.info("Transcribing with Deepgram...")
            response = await self._deepgram_client.listen.asyncprerecorded.v("1").transcribe_file(source=payload, options=options, timeout=timeout)
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