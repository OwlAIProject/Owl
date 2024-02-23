from fastapi import FastAPI, HTTPException
import asyncio
import uvicorn
from typing import Optional, List
import av
from pydub import AudioSegment
import whisperx
from speechbrain.pretrained import SpeakerRecognition
import logging
import os
from multiprocessing import Process
from tempfile import NamedTemporaryFile
from pydantic import BaseModel
from typing import Optional
from .....core.config import AsyncWhisperConfiguration

# Whisper server models
class WhisperWord(BaseModel):
    word: str
    start: float
    end: float
    score: float
    speaker: Optional[str] = None   

class WhisperUtterance(BaseModel):
    start: Optional[float]
    end: Optional[float]
    text: Optional[str]
    speaker: Optional[str]
    words: List[WhisperWord]

class TranscriptionRequest(BaseModel):
    main_audio_file_path: str
    speaker_name: Optional[str] = None
    voice_sample_filepath: Optional[str] = None

class TranscriptionResponse(BaseModel):
    utterances: List[WhisperUtterance] = []

logger = logging.getLogger(__name__)

class AsyncWhisperTranscriptionServer:
    def __init__(self, config: AsyncWhisperConfiguration):
        self._config = config
        self.app = FastAPI()
        self._transcription_model, self._diarize_model, self._verification_model, self._alignment_model, self._alignment_metadata = self._load_models()
        self._setup_routes()

    def _load_models(self):
        logger.info(f"Transcription model: {self._config.model} | Device: {self._config.device} | Compute type: {self._config.compute_type} | Batch size: {self._config.batch_size} | Verification model source: {self._config.verification_model_source} | Verification model savedir: {self._config.verification_model_savedir} | Verification threshold: {self._config.verification_threshold} | HF token: {self._config.hf_token}")
        transcription_model = whisperx.load_model(self._config.model, self._config.device, compute_type=self._config.compute_type)

        diarize_model = whisperx.DiarizationPipeline(model_name='pyannote/speaker-diarization@2.1', use_auth_token=self._config.hf_token, device=self._config.device)
        verification_model = SpeakerRecognition.from_hparams(source=self._config.verification_model_source, savedir=self._config.verification_model_savedir, run_opts={"device": self._config.device})
        alignment_model, alignment_metadata = whisperx.load_align_model(language_code="en", device=self._config.device)
        return transcription_model, diarize_model, verification_model, alignment_model, alignment_metadata

    def _setup_routes(self):
        # Main endpoint takes a file path and returns a transcription response
        #
        # Example usage:
        # curl -X POST http://127.0.0.1:8010/transcribe/ \
        #      -H "Content-Type: application/json" \
        #      -d '{
        #            "main_audio_file_path": "some_file.aac"
        #          }'

        @self.app.post("/transcribe/", response_model=TranscriptionResponse)
        async def transcribe(request: TranscriptionRequest):
            try:
                transcription_result = await self._transcribe_audio(request.main_audio_file_path, request.voice_sample_filepath, request.speaker_name)
                return transcription_result
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

    async def _transcribe_audio(self, main_audio_filepath, voice_sample_filepath=None, speaker_name=None):
        if not os.path.exists(main_audio_filepath):
            raise FileNotFoundError("Main audio file not found")
        logger.info(f"Transcribing audio file: {main_audio_filepath}")

        # Transcription
        audio = whisperx.load_audio(main_audio_filepath)
        result = self._transcription_model.transcribe(audio, batch_size=self._config.batch_size)
        initial_transcription = result["segments"]
        logger.info(f"Initial transcription complete. Total segments: {len(initial_transcription)}")

        # Align whisper output
        result = whisperx.align(initial_transcription, self._alignment_model, self._alignment_metadata, audio, device=self._config.device, return_char_alignments=False)
        logger.info(f"Transcription alignment complete.")

        # Speaker diarization
        try:
            diarize_segments = self._diarize_model(audio)
            logger.info(f"Speaker diarization complete. Total segments: {len(diarize_segments)}")
            result = whisperx.assign_word_speakers(diarize_segments, result)
        except Exception as e:
            logger.info(f"Error occurred during assigning word speakers: {str(e)}")
        logger.info(f"Speaker assignment complete.")
        final_transcription_data = result["segments"]
        logger.info(f"Transcription complete. Total segments: {len(final_transcription_data)}")

        # Speaker verification (if voice sample file path provided) and adjust speaker labels
        if voice_sample_filepath:
            if not os.path.exists(voice_sample_filepath):
                raise FileNotFoundError("Voice sample file not found")
            temp_voice_sample_filepath = voice_sample_filepath
            if not voice_sample_filepath.endswith('.wav'):
                temp_voice_sample_filepath = self._convert_to_wav(voice_sample_filepath)
            full_audio = AudioSegment.from_file(main_audio_filepath)
            for segment in final_transcription_data:
                # Extract the segment directly from the full audio loaded in memory
                start_ms = segment.get("start") * 1000  
                end_ms = segment.get("end") * 1000  
                segment_audio = full_audio[start_ms:end_ms]
        
                with NamedTemporaryFile(suffix=".wav", delete=True) as temp_segment:
                    segment_audio.export(temp_segment.name, format='wav')
                    score, _ = self._compare_with_voice_sample(temp_voice_sample_filepath, temp_segment.name)
                    if score > self._config.verification_threshold:
                        segment["speaker"] = speaker_name 
        utterances = []
        for segment in final_transcription_data:
            words_list = []
            for word in segment.get("words", []):
                word_obj = WhisperWord(
                    word=word.get("word", ""),
                    start=word.get("start", -1),
                    end=word.get("end", -1),
                    score=word.get("score", -1),
                    speaker=word.get("speaker")
                )
                words_list.append(word_obj)

            speaker_label = segment.get("speaker", "Unknown Speaker")
            utterance = WhisperUtterance(
                start=segment.get("start"),
                end=segment.get("end"),
                text=segment.get("text", ""),
                words=words_list,
                speaker=speaker_label
            )
            utterances.append(utterance)
        final_transcription = TranscriptionResponse(utterances=utterances)

        logger.info(f"Returning transcription data as JSON: {final_transcription} {final_transcription.json()}")
        return final_transcription
       
    def _convert_to_wav(self, input_filepath):
        temp_wav_file = NamedTemporaryFile(suffix='.wav', delete=False)
        output_filepath = temp_wav_file.name
        temp_wav_file.close()

        input_container = av.open(input_filepath)
        output_container = av.open(output_filepath, 'w')
        stream = input_container.streams.audio[0]
        output_stream = output_container.add_stream('pcm_s16le', rate=stream.rate)
        for frame in input_container.decode(stream):
            output_container.mux(output_stream.encode(frame))
        output_container.close()
        input_container.close()

        return output_filepath

    def _compare_with_voice_sample(self, voice_sample_path, filepath):
        score, prediction = self._verification_model.verify_files(voice_sample_path, filepath)
        return score, prediction
    
    def start(self):
        uvicorn.run(self.app, host=self._config.host, port=self._config.port, log_level="info")

def start_async_transcription_server_process(config: AsyncWhisperConfiguration):
    asyncio.run(AsyncWhisperTranscriptionServer(config=config).start())

def start_async_transcription_server(config: AsyncWhisperConfiguration):
    process = Process(target=start_async_transcription_server_process, args=(config,))
    process.start()
    return process