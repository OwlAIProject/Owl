# Server Configuration

This guide will walk you through the configuration options within your `config.yaml` file.

## Prerequisites

If you haven't already, make sure you've completed the steps in the [Getting Started](getting-started.md) guide.

## 1. User configuration

Set your `name` and `client_token`. `name` identifies who you are within the Owl project. `client_token` is an authorization token used throughout the Owl project. These values are inserted automatically during the `owl setup` process.

```yaml
user:
  name: Owl
  client_token: qkirJuCHF9lKK1DvwZ2LmYSPTTFe9rR5mmJU6kp5o2M
```

> **Token Generation**:
>
> Easily generate a 32-byte (256-bit) cryptographically secure random string with this command:
>
> ```bash
> python -c 'import secrets; print(secrets.token_urlsafe(32))'
> ```

## 2. Web server configuration

Set your web server's frontend and api `base_url` and `port` values. You can also specify the environment (e.g., `development`, `production`).

```yaml
web:
  base_url: http://localhost
  port: 3000
  environment: development
  api:
    base_url: http://localhost
    port: 8000
```

> **Important**
>
> These defaults are not secure and **must** be changed in a production environment.

## 3. LLM configuration

Specify the LLM model you want to use. Owl interfaces with LLMs through [LiteLLM](https://litellm.ai/), which lets you easily use either local or remote LLMs. For a full list of LLM providers, see the [LiteLLM Providers](https://litellm.ai/providers) documentation.

### Using a local LLM

To use a local LLM, follow these steps:

1. Install [Ollama](https://github.com/ollama/ollama) and download your desired local LLM.
2. Set the `llm` section's `model` value to the chosen model.

```yaml
llm:
  model: ollama/mistral:instruct
  base_url: http://localhost
  port: 11434
  api_key:
```

### Using a remote LLM

To use a remote LLM, set the `llm` section's `model` and `key` values to your desired LLM and provider.

```yaml
llm:
  model: gpt-4
  base_url: http://localhost
  port: 11434
  api_key: <your-openai-api-key>
```

## 4. Transcription configuration

To configure speech-to-text transcription, choose a provider for both asynchronous and streaming transcription. [Deepgram](https://deepgram.com/) is recommended for ease of use. Whisper is also supported but requires additional setup.

Set your `async_transcription` and `streaming_transcription` provider to either `deepgram` or `whisper`.

```yaml
async_transcription:
  provider: deepgram

streaming_transcription:
  provider: deepgram
```

### Using Deepgram

To use Deepgram, follow these steps:

1. Create a [Deepgram](https://deepgram.com/) account to obtain an API key.
2. Configure the `deepgram` section by setting an `api_key`, `model` and `language`.

```yaml
deepgram:
  api_key: <your-deepgram-api-key>
  model: nova-2
  language: en-US
```

### Using Whisper

To use Whisper, follow these steps:

1. Create a [Hugging Face](https://huggingface.co/) account to obtain an API token. Add your Hugging Face API token to `async_whisper.hf_token`.
2. Accept the terms for the [PyAnnote Segmentation Model](https://huggingface.co/pyannote/segmentation) and [PyAnnote Speaker Diarization Model](https://huggingface.co/pyannote/speaker-diarization) on Hugging Face.

- [PyAnnote Segmentation Model](https://huggingface.co/pyannote/segmentation)
- [PyAnnote Speaker Diarization Model](https://huggingface.co/pyannote/speaker-diarization)

3. Optionally, adjust configurations for the `async_whisper` and `streaming_whisper` sections.

```yaml
async_whisper:
  host: localhost
  port: 8010
  hf_token: <your-hf-token>
  device: cpu
  compute_type: int8
  batch_size: 16
  model: tiny
  verification_threshold: 0.1
  verification_model_source: speechbrain/spkrec-ecapa-voxceleb
  verification_model_directory: .models/spkrec-ecapa-voxceleb

streaming_whisper:
  host: localhost
  port: 8009
  model: small
  language: en
  silero_sensitivity: 0.4
  webrtc_sensitivity: 2
  post_speech_silence_duration: 0.5
```

## 5. Optional configuration

### Prompt configuration

Owl uses LLM prompts for link suggestions and summarization. You can modify these prompts by changing the `prompts` section. See your generated `config.yaml` or `.config/sample-config.yaml` file for the default prompt values.

```yaml
prompt:
  suggest_links_system_message: '...'
  summarization_system_message: '...'
  short_summarization_system_message: '...'
```

## 6. Run server

Start the server using the following command:

```bash
owl serve --web
```

You can now access and use your Owl server at `http://localhost:3000`.

## Next steps

Your Owl server is now configured and ready to use. From here, you can setup an Owl capture device, learn more about Owl's configuration options or explore environment variables support.

1. View [Owl capture device](clients/) setup guides
2. Read more about Owl's [configuration options](configuration-options.md)
3. Learn about Owl's support for [environment variables](environment-variables.md)
