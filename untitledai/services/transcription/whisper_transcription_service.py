import os
import av
from ...core.config import TranscriptionConfig
from ...models.schemas import Word, Utterance, Transcription
from tempfile import NamedTemporaryFile
import whisperx
from pydub import AudioSegment
from speechbrain.pretrained import SpeakerRecognition

tc = TranscriptionConfig

def load_models():
    transcription_model = whisperx.load_model(tc.MODEL_NAME, tc.DEVICE, compute_type=tc.COMPUTE_TYPE)
    diarize_model = whisperx.DiarizationPipeline(use_auth_token=tc.HF_AUTH_TOKEN, device=tc.DEVICE)
    verification_model = SpeakerRecognition.from_hparams(source=tc.VERIFICATION_MODEL_SOURCE, savedir=tc.VERIFICATION_MODEL_SAVEDIR, run_opts={"device": tc.DEVICE})
    return transcription_model, diarize_model, verification_model

transcription_model, diarize_model, verification_model = load_models()

def convert_to_wav(input_filepath):
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

def compare_with_voice_sample(voice_sample_path, file_path):
    score, prediction = verification_model.verify_files(voice_sample_path, file_path)
    return score, prediction

def transcribe_audio(main_audio_filepath, voice_sample_filepath=None, speaker_name=None):
    if not os.path.exists(main_audio_filepath):
        raise FileNotFoundError("Main audio file not found")

    # Transcription
    audio = whisperx.load_audio(main_audio_filepath)
    result = transcription_model.transcribe(audio, batch_size=tc.BATCH_SIZE)
    initial_transcription = result["segments"]

    # Align whisper output
    model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=tc.DEVICE)
    result = whisperx.align(initial_transcription, model_a, metadata, audio, device=tc.DEVICE, return_char_alignments=False)
  
    # Speaker diarization
    diarize_segments = diarize_model(audio)
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
            temp_voice_sample_filepath = convert_to_wav(voice_sample_filepath)

        for utterance in final_transcription.utterances:
            for word in utterance.words:
                segment_audio = AudioSegment.from_file(main_audio_filepath)[word.start * 1000: word.end * 1000]
                with NamedTemporaryFile(suffix=".wav", delete=True) as temp_segment:
                    segment_audio.export(temp_segment.name, format='wav')
                    score, _ = compare_with_voice_sample(temp_voice_sample_filepath, temp_segment.name)
                    if score > tc.VERIFICATION_THRESHOLD:
                        word.speaker = speaker_name if speaker_name else 'Verified Speaker'

    return final_transcription