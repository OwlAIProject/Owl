# Owl - Always-on Wearable AI Setup Guide

[<< Home](../README.md)

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- Python (version 3.11 or newer)
- Node.js (version 18 or newer)
- Poetry
- FFmpeg
- Ollama (optional, for local-only mode)

## Model Agreements

Owl uses PyAnnote for diarization. Please visit Hugging Face and accept the terms for the following models:

- [PyAnnote Segmentation Model](https://huggingface.co/pyannote/segmentation)
- [PyAnnote Speaker Diarization Model](https://huggingface.co/pyannote/speaker-diarization)

## Setup Instructions

1. **Clone Repository**

   Clone the Owl repository from GitHub:

   ```
   git clone https://github.com/OwlAIProject/Owl.git
   cd Owl
   ```

2. **Install Dependencies**

   Install required OS dependencies

   ```
   # on Ubuntu or Debian
   sudo apt install portaudio19-dev python3-pyaudio

   # on Mac Os
   brew install portaudio
   ```

   Use Poetry to install the required dependencies:

   ```
   poetry install
   ```

3. **Activate environment**
   Activate virtual env created with poetry

   ```
   poetry shell

   ```

4. **Set Environment Variables**

   For details on customizing application behavior by setting environment variables, see the [Environment Variables](../docs/environment-variables.md) document.

5. **Start the Server**

   Launch the Owl server:

   ```
   owl serve --web
   ```

   You can now access the web interface at `http://localhost:3000`. Start testing captures with a microphone or Bluetooth devices. You can also build the iOS app and test captures via the Apple Watch or Bluetooth devices through your iPhone.

## Using Commercial Models

If you prefer using commercial models for transcription and summarization, set up the following environment variables instead of the PyAnnote setup:

- For Deepgram:

  ```
  export OWL_STREAMING_TRANSCRIPTION_PROVIDER=deepgram
  export OWL_ASYNC_TRANSCRIPTION_PROVIDER=deepgram
  export OWL_DEEPGRAM_API_KEY=<your_api_key>
  ```

- For GPT-4 Turbo:
  ```
  export OWL_LLM_MODEL=gpt-4-turbo-preview
  export OWL_LLM_BASE_URL=https://api.openai.com/v1
  export OWL_LLM_API_KEY=<your_api_key>
  ```

[<< Home](../README.md)
