#
# whisper_transcription_service.py
#
# Local Whisper model for audio transcription with diarization and speaker identification.
#

import os
from tempfile import NamedTemporaryFile

import av
import whisperx
from pydub import AudioSegment
from speechbrain.pretrained import SpeakerRecognition

from ...core.config import TranscriptionConfiguration
from ...core.utils.suppress_output import suppress_output
from ...models.schemas import Word, Utterance, Transcription


class WhisperTranscriptionService:
    def __init__(self, config: TranscriptionConfiguration):
        self._config = config
        self._transcription_model, self._diarize_model, self._verification_model = self._load_models(config)
    
    def transcribe_audio(self, main_audio_filepath: str, voice_sample_filepath: str = None, speaker_name: str = None) -> Transcription:
        if not os.path.exists(main_audio_filepath):
            raise FileNotFoundError("Main audio file not found")

        # Transcription
        audio = whisperx.load_audio(main_audio_filepath)
        result = self._transcription_model.transcribe(audio, batch_size=self._config.batch_size)
        initial_transcription = result["segments"]

        # Align whisper output
        model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=self._config.device)
        result = whisperx.align(initial_transcription, model_a, metadata, audio, device=self._config.device, return_char_alignments=False)
    
        # Speaker diarization
        diarize_segments = self._diarize_model(audio)
        result = whisperx.assign_word_speakers(diarize_segments, result)
        final_transcription_data = result["segments"]

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

        # Speaker verification (if voice sample file path provided)
        if voice_sample_filepath:
            # Ensure voice sample file exists
            if not os.path.exists(voice_sample_filepath):
                raise FileNotFoundError("Voice sample file not found")
            temp_voice_sample_filepath = voice_sample_filepath
            if not voice_sample_filepath.endswith('.wav'):
                temp_voice_sample_filepath = self._convert_to_wav(voice_sample_filepath)

            for utterance in final_transcription.utterances:
                for word in utterance.words:
                    segment_audio = AudioSegment.from_file(main_audio_filepath)[word.start * 1000: word.end * 1000]
                    with NamedTemporaryFile(suffix=".wav", delete=True) as temp_segment:
                        segment_audio.export(temp_segment.name, format='wav')
                        score, _ = self._compare_with_voice_sample(temp_voice_sample_filepath, temp_segment.name)
                        if score > self._config.verification_threshold:
                            word.speaker = speaker_name if speaker_name else 'Verified Speaker'

        return final_transcription
    
    @staticmethod
    def _load_models(config: TranscriptionConfiguration):
        with suppress_output():
            # WhisperX has noisy warnings but they don't matter
            transcription_model = whisperx.load_model(config.model, config.device, compute_type=config.compute_type)
        diarize_model = whisperx.DiarizationPipeline(use_auth_token=config.hf_token, device=config.device)
        verification_model = SpeakerRecognition.from_hparams(source=config.verification_model_source, savedir=config.verification_model_savedir, run_opts={"device": config.device})
        return transcription_model, diarize_model, verification_model

    def _convert_to_wav(self, input_filepath: str) -> str:
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

    def _compare_with_voice_sample(self, voice_sample_path: str, file_path: str):
        score, prediction = self._verification_model.verify_files(voice_sample_path, file_path)
        return score, prediction