#
# cli.py
#
# Program entry points.
#

import asyncio
from datetime import datetime, timezone
import os
import requests
import time
import uuid

import click
from rich.console import Console

from ..services.stt.asynchronous.async_transcription_service_factory import AsyncTranscriptionServiceFactory
from ..services.conversation.transcript_summarizer import TranscriptionSummarizer

import uvicorn

from .config import Configuration


####################################################################################################
# Config File Parsing
####################################################################################################

def load_config_yaml(ctx, param, value) -> Configuration:
    return Configuration.load_config_yaml(value.name)

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
@click.option("--timestamp", help="Timestamp in YYYYmmdd-HHMMSS.fff format. If not specified, will use current time.")
@click.option("--device-type", help="Capture device type otherwise 'unknown'.")
@click.option("--host", default="127.0.0.1", help="Address to send to.")
@click.option('--port', default=8000, help="Port to use.")
def upload(file: str, timestamp: datetime | None, device_type: str | None, host: str, port: int):
    # Load file
    with open(file, "rb") as fp:
        file_contents = fp.read()

    # Create valid capture UUID
    capture_uuid = uuid.uuid1().hex

    # Timestamp
    if timestamp is not None:
        try:
           timestamp = datetime.strptime(timestamp, "%Y%m%d-%H%M%S.%f")
        except:
           raise ValueError("'timestamp' string does not conform to YYYYmmdd-HHMMSS.fff format")
    else:
        timestamp = datetime.now(timezone.utc)

    # Upload
    data = {
         "capture_uuid": capture_uuid,
         "timestamp": timestamp.strftime("%Y%m%d-%H%M%S.%f")[:-3],
         "device_type": device_type if device_type else "unknown"
    }
    files = {
        "file": (os.path.basename(file), file_contents)
    }
    response = requests.post(url=f"http://{host}:{port}/capture/upload_chunk", files=files, data=data)
    
    # If successful, request processing
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
