import os
from owl.services.transcription.whisper_transcription_service import transcribe_audio

def test_transcribe_audio():
    test_dir = os.path.dirname(os.path.abspath(__file__))

    main_audio_filepath = os.path.join(test_dir, "data/audio/test_session.wav")
    speaker_verification_audio_path = os.path.join(test_dir, "data/audio/test_speaker.m4a")

    transcription_result = transcribe_audio(main_audio_filepath, speaker_verification_audio_path, "Bob")

    assert transcription_result is not None

    expected_transcriptions = [
        "Just testing now.",
        "Just testing now.",
        "That's all I'm doing."
    ]
    for idx, utterance in enumerate(transcription_result.utterances):
        expected_text = expected_transcriptions[idx]
        assert utterance.speaker == "Bob", f"Failed assertion at utterance {idx + 1}: Speaker mismatch."
        assert utterance.text.lstrip() == expected_text, f"Failed assertion at utterance {idx + 1}: Text mismatch."

