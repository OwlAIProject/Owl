# Owl - Always-on Wearable AI Setup Guide

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- Docker
- Docker Compose

## Model Agreements

Owl uses PyAnnote for diarization. Please visit Hugging Face and accept the terms for the following models:
- [PyAnnote Segmentation Model](https://huggingface.co/pyannote/segmentation)
- [PyAnnote Speaker Diarization Model](https://huggingface.co/pyannote/speaker-diarization)

## Setup Instructions

1. **Environment Variables**

   Set your Hugging Face token as an environment variable:
   ```
   export OWL_ASYNC_WHISPER_HF_TOKEN=<your_hugging_face_token>
   ```

2. **Clone Repository**

   Clone the Owl repository from GitHub:
   ```
   git clone https://github.com/OwlAIProject/Owl.git
   cd Owl
   ```

3. **Launch Containers**

   Launched the API and Web containers:
   ```
    docker compose up
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
  export OWL_LLM_API_BASE_URL=https://api.openai.com/v1
  export OWL_LLM_API_KEY=<your_api_key>
  ```
  
**Note for Mac Users:**

If you're using Docker on a Mac, you may need to adjust the Docker settings to allocate more RAM to ensure optimal performance, especially when running local models. Docker's default settings might not provide sufficient RAM.

Additionally, running local models directly on Docker for Mac might result in slower performance compared to native environments. This is due to the overhead associated with Docker's virtualization on macOS.

For optimal performance on a Mac, consider following the specific instructions provided [here](./macos_and_linux_setup.md). 

[<< Back to Home](../README.md)
