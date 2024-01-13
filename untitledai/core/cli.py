import click
from rich.console import Console
import time
import os
import sys
import contextlib

@contextlib.contextmanager
def suppress_output():
    # Redirect stdout and stderr to /dev/null
    with open(os.devnull, 'w') as devnull:
        original_stdout, original_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = devnull, devnull
        try:
            yield
        finally:
            # Restore stdout and stderr
            sys.stdout, sys.stderr = original_stdout, original_stderr

@click.group()
def cli():
    """UntitledAI CLI tool."""
    pass

@cli.command()
@click.argument('main_audio_filepath', type=click.Path(exists=True))
@click.option('--voice_sample_filepath', type=click.Path(exists=True), help='Path to the voice sample file')
@click.option('--speaker_name', help='Name of the speaker')
def transcribe(main_audio_filepath, voice_sample_filepath, speaker_name):
    """Transcribe an audio file."""
    console = Console()

    # Model loading
    console.log("[bold green]Loading models...")
    start_time = time.time()
    with suppress_output(): # WhisperX has noisy warnings but they don't matter
        from ..services.transcription.whisper_transcription_service import transcribe_audio
    end_time = time.time()
    console.log(f"[bold green]Models loaded successfully! Time taken: {end_time - start_time:.2f} seconds")

    # Transcription
    start_transcription_time = time.time()
    console.log("[cyan]Transcribing audio...")

    transcription = transcribe_audio(main_audio_filepath, voice_sample_filepath, speaker_name)

    end_transcription_time = time.time()

    console.print(transcription, style="bold yellow")
    console.log(f"[bold green]Transcription complete! Time taken: {end_transcription_time - start_transcription_time:.2f} seconds")

@cli.command()
@click.argument('main_audio_filepath', type=click.Path(exists=True))
@click.option('--voice_sample_filepath', type=click.Path(exists=True), help='Path to the voice sample file')
@click.option('--speaker_name', help='Name of the speaker')
def summarize(main_audio_filepath, voice_sample_filepath, speaker_name):
    """Transcribe and summarize an audio file."""
    from ..services.llm.session import summarize
    console = Console()

    # Model loading
    console.log("[bold green]Loading models...")
    start_time = time.time()
    with suppress_output():
        from ..services.transcription.whisper_transcription_service import transcribe_audio
    end_time = time.time()
    console.log(f"[bold green]Models loaded successfully! Time taken: {end_time - start_time:.2f} seconds")

    # Transcription
    start_transcription_time = time.time()
    console.log("[cyan]Transcribing audio...")

    transcription = transcribe_audio(main_audio_filepath, voice_sample_filepath, speaker_name)

    end_transcription_time = time.time()

    console.print(transcription, style="bold yellow")
    console.log(f"[bold green]Transcription complete! Time taken: {end_transcription_time - start_transcription_time:.2f} seconds")

    console.log("[bold green]Summarizing transcription...")

    summary = summarize(transcription)

    console.print(summary, style="bold yellow")
    console.log("[bold green]Summarization complete!")

if __name__ == '__main__':
    cli()
