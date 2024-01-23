import ray

from .abstract_async_transcription_service import AbstractAsyncTranscriptionService
from ....models.schemas import Word, Utterance, Transcription
import os
import av
from tempfile import NamedTemporaryFile
import whisperx
import asyncio
from pydub import AudioSegment
from speechbrain.pretrained import SpeakerRecognition


@ray.remote(max_concurrency=10) 
class WhisperTranscriptionActor:
    def __init__(self, config):
            self.config = config
            self.transcription_model, self.diarize_model, self.verification_model = self.load_models(config)

    def load_models(self, config):
        print(f"Transcription model: {config.model}")
        transcription_model = whisperx.load_model(config.model, config.device, compute_type=config.    compute_type)
        diarize_model = whisperx.DiarizationPipeline(use_auth_token=config.hf_token, device=config.device)
        verification_model = SpeakerRecognition.from_hparams(source=config.verification_model_source, savedir=config.verification_model_savedir, run_opts={"device": config.device})
        return transcription_model, diarize_model, verification_model
    
    def convert_to_wav(self, input_filepath):
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

    def compare_with_voice_sample(self, voice_sample_path, file_path):
        score, prediction = self.verification_model.verify_files(voice_sample_path, file_path)
        return score, prediction
    
    async def transcribe_audio(self, main_audio_filepath, voice_sample_filepath=None, speaker_name=None):
        if not os.path.exists(main_audio_filepath):
            raise FileNotFoundError("Main audio file not found")
        print(f"Transcribing audio file: {main_audio_filepath}")
        # Transcription
        audio = whisperx.load_audio(main_audio_filepath)
        result = self.transcription_model.transcribe(audio, batch_size=self.config.batch_size)
        initial_transcription = result["segments"]
        print(f"Initial transcription complete. Total segments: {len(initial_transcription)}")

        # Align whisper output
        model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=self.config.device)
        result = whisperx.align(initial_transcription, model_a, metadata, audio, device=self.config.device, return_char_alignments=False)
    
        # Speaker diarization
        diarize_segments = self.diarize_model(audio)
        result = whisperx.assign_word_speakers(diarize_segments, result)
        final_transcription_data = result["segments"]
        print(f"Transcription complete. Total segments: {len(final_transcription_data)}")
        # Convert transcription data to Pydantic models
        utterances = []
        for segment in final_transcription_data:
            words_list = []
            for word in segment.get("words", []):
                word_obj = Word(
                    word=word.get("word", ""),
                    start=word.get("start"),
                    end=word.get("end"),
                    score=word.get("score"),
                    speaker=word.get("speaker")
                )
                words_list.append(word_obj)

            speaker_label = speaker_name if speaker_name and voice_sample_filepath else segment.get("speaker", "Unknown Speaker")
            utterance = Utterance(
                start=segment.get("start"),
                end=segment.get("end"),
                text=segment.get("text", ""),
                words=words_list,
                speaker=speaker_label
            )
            utterances.append(utterance)

        final_transcription = Transcription(utterances=utterances)
        print("Transcription converted to Pydantic model.")
        # Speaker verification (if voice sample file path provided)
        if voice_sample_filepath:
            # Ensure voice sample file exists
            if not os.path.exists(voice_sample_filepath):
                raise FileNotFoundError("Voice sample file not found")
            temp_voice_sample_filepath = voice_sample_filepath
            if not voice_sample_filepath.endswith('.wav'):
                temp_voice_sample_filepath = self.convert_to_wav(voice_sample_filepath)

            for utterance in final_transcription.utterances:
                for word in utterance.words:
                    segment_audio = AudioSegment.from_file(main_audio_filepath)[word.start * 1000: word.end * 1000]
                    with NamedTemporaryFile(suffix=".wav", delete=True) as temp_segment:
                        segment_audio.export(temp_segment.name, format='wav')
                        score, _ = self.compare_with_voice_sample(temp_voice_sample_filepath, temp_segment.name)
                        if score > self.config.verification_threshold:
                            word.speaker = speaker_name if speaker_name else 'Verified Speaker'

        return final_transcription

class AsyncWhisperTranscriptionService(AbstractAsyncTranscriptionService):
    def __init__(self, config):
        self.actor = WhisperTranscriptionActor.options(max_concurrency=10).remote(config)  # Set concurrency here

    async def transcribe_audio(self, main_audio_filepath, voice_sample_filepath=None, speaker_name=None):
        return await self.actor.transcribe_audio.remote(main_audio_filepath, voice_sample_filepath, speaker_name)
