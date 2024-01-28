#
# cli.py
#
# Program entry points.
#

import time
import asyncio
import click
from rich.console import Console
from pydantic_yaml import parse_yaml_raw_as
from ..services.stt.asynchronous.async_transcription_service_factory import AsyncTranscriptionServiceFactory
from ..services.conversation.transcript_summarizer import TranscriptionSummarizer

import uvicorn

from .config import Configuration


####################################################################################################
# Config File Parsing
####################################################################################################

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


####################################################################################################
# Help (no args)
####################################################################################################

@click.group()
def cli():
    """UntitledAI CLI tool."""
    pass


###################################################################################################
# Transcribe File
###################################################################################################


@cli.command()
@click.argument('main_audio_filepath', type=click.Path(exists=True))
@add_options(_config_options)
@click.option('--voice_sample_filepath', type=click.Path(exists=True), help='Path to the voice sample file')
@click.option('--speaker_name', help='Name of the speaker')
def transcribe(config: Configuration, main_audio_filepath: str, voice_sample_filepath: str, speaker_name: str):
    """Transcribe an audio file."""
    console = Console()

    console.log("[bold green]Loading transcription service...")
    start_time = time.time()

    transcription_service = AsyncTranscriptionServiceFactory.get_service(config)

    end_time = time.time()
    console.log(f"[bold green]Transcription service loaded! Time taken: {end_time - start_time:.2f} seconds")

    console.log("[cyan]Transcribing audio...")

    transcription = asyncio.run(
        transcription_service.transcribe_audio(
            main_audio_filepath, voice_sample_filepath, speaker_name
        )
    )

    console.print(transcription.utterances, style="bold yellow")
    console.log(f"[bold green]Transcription complete! Time taken: {time.time() - start_time:.2f} seconds")



###################################################################################################
# Summarize File
###################################################################################################

@cli.command()
@click.argument('main_audio_filepath', type=click.Path(exists=True))
@add_options(_config_options)
@click.option('--voice_sample_filepath', type=click.Path(exists=True), help='Path to the voice sample file')
@click.option('--speaker_name', help='Name of the speaker')
def summarize(config: Configuration, main_audio_filepath: str, voice_sample_filepath: str, speaker_name: str):
    """Transcribe and summarize an audio file."""
    from .. import prompts
    console = Console()

    console.log("[bold green]Loading transcription service...")
    start_time = time.time()

    transcription_service = AsyncTranscriptionServiceFactory.get_service(config)

    end_time = time.time()
    console.log(f"[bold green]Transcription service loaded! Time taken: {end_time - start_time:.2f} seconds")

    console.log("[cyan]Transcribing audio...")

    transcription = asyncio.run(
        transcription_service.transcribe_audio(
            main_audio_filepath, voice_sample_filepath, speaker_name
        )
    )

    console.print(transcription.utterances, style="bold yellow")
    console.log(f"[bold green]Transcription complete! Time taken: {time.time() - start_time:.2f} seconds")
    summarizer = TranscriptionSummarizer(config)
    summary = asyncio.run(
        summarizer.summarize(transcription)
    )

    console.print(summary, style="bold yellow")
    console.log("[bold green]Summarization complete!")


###################################################################################################
# Send Audio
###################################################################################################

@cli.command()
@click.option("--file", required=True, help="Audio file to send.")
@click.option("--host", default="127.0.0.1", help="Address to send to.")
@click.option('--port', default=8000, help="Port to use.")
def upload(file: str, host: str, port: int):
    print(f"Upload {file} to {host}:{port}")
    from datetime import datetime, timezone
    import os
    import requests
    import uuid

    with open(file, "rb") as fp:
        file_contents = fp.read()
    
    capture_uuid = uuid.uuid1().hex

    data = {
         "capture_uuid": capture_uuid,
         "timestamp": datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S.%f")[:-3],
         "device_type": "unknown"
    }
    
    files = {
        "file": (os.path.basename(file), file_contents)
    }
    
    response = requests.post(url=f"http://{host}:{port}/capture/upload_chunk", files=files, data=data)
    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.content}")
    else:
        response = requests.post(url=f"http://{host}:{port}/capture/process_capture", data={ "capture_uuid": capture_uuid })
        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.content}")
        print(response.content)


####################################################################################################
# Server
####################################################################################################

@cli.command()
@add_options(_config_options)
@click.option('--host', default='127.0.0.1', help='The interface to bind to.')
@click.option('--port', default=8000, help='The port to bind to.')
def serve(config: Configuration, host, port):
    """Start the server."""
    from .. import server
    console = Console()
    console.log(f"[bold green]Starting server at http://{host}:{port}...")
    app = server.create_server_app(config=config)
    uvicorn.run(app, host=host, port=port, log_level="info", ws_ping_interval=None, ws_ping_timeout=None)

if __name__ == '__main__':
    cli()
