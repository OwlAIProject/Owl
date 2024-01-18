import time
import os
import sys

import contextlib
import click
from rich.console import Console
from pydantic_yaml import parse_yaml_raw_as
import uvicorn

from .config import Configuration


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

def load_config_yaml(ctx, param, value) -> Configuration:
    return parse_yaml_raw_as(Configuration, value)

def add_options(options):
    def _add_options(func):
        for option in reversed(options):
            func = option(func)
        return func
    return _add_options

_config_options = [
    click.option("--config", default="untitledai/config.yaml", help="Configuration file", type=click.File(mode="r"), callback=load_config_yaml)
]

@click.group()
def cli():
    """UntitledAI CLI tool."""
    pass

@cli.command()
@click.argument('main_audio_filepath', type=click.Path(exists=True))
@add_options(_config_options)
@click.option('--voice_sample_filepath', type=click.Path(exists=True), help='Path to the voice sample file')
@click.option('--speaker_name', help='Name of the speaker')
def transcribe(config: Configuration, main_audio_filepath: str, voice_sample_filepath: str, speaker_name: str):
    """Transcribe an audio file."""
    console = Console()

    # Model loading
    console.log("[bold green]Loading models...")
    start_time = time.time()
    with suppress_output(): # WhisperX has noisy warnings but they don't matter
        from ..services.transcription.whisper_transcription_service import WhisperTranscriptionService
    end_time = time.time()
    console.log(f"[bold green]Models loaded successfully! Time taken: {end_time - start_time:.2f} seconds")

    # Transcription
    start_transcription_time = time.time()
    console.log("[cyan]Transcribing audio...")

    transcription = WhisperTranscriptionService(config=config.transcription).transcribe_audio(main_audio_filepath, voice_sample_filepath, speaker_name)

    end_transcription_time = time.time()

    console.print(transcription, style="bold yellow")
    console.log(f"[bold green]Transcription complete! Time taken: {end_transcription_time - start_transcription_time:.2f} seconds")

@cli.command()
@click.argument('main_audio_filepath', type=click.Path(exists=True))
@add_options(_config_options)
@click.option('--voice_sample_filepath', type=click.Path(exists=True), help='Path to the voice sample file')
@click.option('--speaker_name', help='Name of the speaker')
def summarize(config: Configuration, main_audio_filepath: str, voice_sample_filepath: str, speaker_name: str):
    """Transcribe and summarize an audio file."""
    from ..services.llm import LLM
    from .. import prompts
    console = Console()

    # Model loading
    console.log("[bold green]Loading models...")
    start_time = time.time()
    with suppress_output():
        from ..services.transcription.whisper_transcription_service import WhisperTranscriptionService
    end_time = time.time()
    console.log(f"[bold green]Models loaded successfully! Time taken: {end_time - start_time:.2f} seconds")

    # Transcription
    start_transcription_time = time.time()
    console.log("[cyan]Transcribing audio...")

    transcription = WhisperTranscriptionService(config=config.transcription).transcribe_audio(main_audio_filepath, voice_sample_filepath, speaker_name)

    end_transcription_time = time.time()

    console.print(transcription, style="bold yellow")
    console.log(f"[bold green]Transcription complete! Time taken: {end_transcription_time - start_transcription_time:.2f} seconds")

    console.log("[bold green]Summarizing transcription...")

    summary = LLM(config=config.llm).summarize(
        transcription=transcription,
        system_message=prompts.summarization_system_message(config=config.user)
    )

    console.print(summary, style="bold yellow")
    console.log("[bold green]Summarization complete!")


@cli.command()
@click.option('--host', default='127.0.0.1', help='The interface to bind to.')
@click.option('--port', default=8000, help='The port to bind to.')
def serve(host, port):
    """Start the server."""
    from ..server.main import app
    console = Console()
    console.log(f"[bold green]Starting server at http://{host}:{port}...")
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == '__main__':
    cli()
