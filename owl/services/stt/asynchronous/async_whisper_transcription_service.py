import httpx
from .abstract_async_transcription_service import AbstractAsyncTranscriptionService
from ....models.schemas import Transcription, Utterance, Word
from .async_whisper.async_whisper_transcription_server import TranscriptionResponse
import logging

logger = logging.getLogger(__name__)

class AsyncWhisperTranscriptionService(AbstractAsyncTranscriptionService):
    def __init__(self, config):
        self._config = config
        self.http_client = httpx.AsyncClient(timeout=None) 

    async def transcribe_audio(self, main_audio_filepath, voice_sample_filepath=None, speaker_name=None):
        payload = {
            "main_audio_file_path": main_audio_filepath,
            "speaker_name": speaker_name,
            "voice_sample_filepath": voice_sample_filepath
        }
        
        url = f"http://{self._config.host}:{self._config.port}/transcribe/"
        
        try:
            logger.info(f"Sending request to local async whisper server at {url}...")
            response = await self.http_client.post(url, json=payload)
            response.raise_for_status()
            response_string = response.text 
            logger.info(f"Received response from local async whisper server: {response_string}")
            transcript_response = TranscriptionResponse.model_validate_json(response_string)
            utterances = []
            logger.info(f"Transcription response: {transcript_response}")
            for whisper_utterance in transcript_response.utterances:
                utterance = Utterance(
                    start=whisper_utterance.start,
                    end=whisper_utterance.end,
                    text=whisper_utterance.text,
                    speaker=whisper_utterance.speaker,
                )
                
                utterance.words = [ 
                    Word(
                        word=whisper_word.word,
                        start=whisper_word.start,
                        end=whisper_word.end,
                        score=whisper_word.score,
                        speaker=whisper_word.speaker,
                    ) for whisper_word in whisper_utterance.words
                ]
                utterances.append(utterance)
                
            transcript = Transcription(utterances=utterances)
            transcript.model = "whisper"
            logger.info(f"Transcription response: {transcript}")
            return transcript
        
        except httpx.HTTPStatusError as e:
            logger.error(f"Error response {e.response.status_code} while requesting {e.request.url!r}.")
        except httpx.RequestError as e:
            logger.error(f"An error occurred while requesting {e.request.url!r}.")
        except Exception as e:
            logger.error(f"An unexpected error occurred while requesting {url}: {e}")