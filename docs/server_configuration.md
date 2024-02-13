# Always-on Perceptive AI

[<< Home](../README.md)

## Server Configuration

The minimal steps necessary to configure the server are listed here.

### 1. Create config.yaml in Project Root Directory

Copy `sample_config.yaml` to the root of the source tree, from where the server is run, and rename
it to `config.yaml`, which is what the server looks for by default. This can be overridden with the
`--config` option.

### 2. Obtain a Hugging Face API Token

- Register a [Hugging Face](https://huggingface.co) account and obtain a token (these are found under "Access Tokens" in "Settings"). This is needed for the SpeechBrain speaker verification model. Place this in the `transcription` section of `config.yaml`; for example:

```
transcription:
  hf_token: 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
  device: cuda
  compute_type: int8
  batch_size: 16
  model: tiny
  verification_threshold: 0.1
  verification_model_source: speechbrain/spkrec-ecapa-voxceleb
  verification_model_savedir: pretrained_models/spkrec-ecapa-voxceleb
```

- `transcription` also configures local transcription via Whisper if enabled.

### 3. Configure LLM

- [LiteLLM](https://litellm.ai/) is used as an interface to LLMs for summarization, etc. The `llm` section allows local (e.g., Ollama) or remote (e.g., OpenAI) LLMs to be specified.
- OpenAI's GPT-4 is the easiest to get up and running. [Sign up for a developer account](https://platform.openai.com/), deposit some funds for usage (we recommend beginning with ~$10), and obtain an API key. Paste that into `config.yaml`.

```
llm:
  model: gpt-4-1106-preview
  api_base_url:
  api_key: sk-a1BCDEfGhI2JKlMNOPqRS3TuvwXY4ZaBCdEFghIJK5lmnO67
```

### 4. Configure User

- Set your name so the AI knows who you are and choose a secret token (a string of any length) to prevent others from accessing conversations on your server. The token will also be entered into display client applications that access the server.

```
user:
  name: "Kramer"
  client_token: 123XYZ_this_is_my_secret_token
```

### 5. Obtain a Deepgram API Key

- Deepgram is an online transcription service that features speaker diarization and other features. It is easy to set up, inexpensive, and new accounts are provided an ample amount of credits that should last for a long time. [Sign up for an account](https://deepgram.com/), obtain an API key, and paste it into `config.yaml`.

```
deepgram:
  api_key: "a1b2cd34ef56g7hi9012j34klmn56789012o34p5"
  model: "nova-2"
  language: "en-US"
```

- The `nova-2` model is recommended. Be aware that it has a limited number of supported languages.
- Users requiring absolute control and privacy may elect to switch away from Deepgram but it is nevertheless the easiest way to get up and running initially.

### 6. Configure Streaming and Asynchronous Transcription

- Streaming transcription is used for real-time transcription of speech to support assistant-in-the-loop use cases. Completed conversations are always transcribed using asynchronous transcription.
- Set both to use Deepgram to get up and running quickly.

```
streaming_transcription:
  provider: "deepgram"

async_transcription:
  provider: "deepgram"
```

[<< Home](../README.md)