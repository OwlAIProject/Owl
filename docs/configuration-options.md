# Configuration Options

This document provides an overview of `owl` configuration options.

> **Environment Variables**:
>
> In most cases, environment variables are optional. To learn more about their usage, see the [Environment Variables](environment-variables.md) document.

## Configurations

### User Configuration

Mapping node: `user`

`name` and `client_token` are generated automatically during the `owl setup` process.

| Option                  | Description                   | Environment Variable             | Required | Default |
| ----------------------- | ----------------------------- | -------------------------------- | -------- | ------- |
| `name`                  | User identifier               | `OWL_USER_NAME`                  | Yes      |         |
| `client_token`          | Application-wide secret token | `OWL_USER_CLIENT_TOKEN`          | Yes      |         |
| `voice_sample_filepath` | Voice sample file path        | `OWL_USER_VOICE_SAMPLE_FILEPATH` | No       |         |

Example:

```yaml
user:
  name: Owl
  client_token: '88nzaZ2bhk6E3Lg0whJYg6vUiyNN-fQeA8kMnW519LQ'
  voice_sample_filepath:
```

### Web Configuration

Mapping nodes: `web` and `web.api`

| Option         | Description  | Environment Variable   | Required | Default            |
| -------------- | ------------ | ---------------------- | -------- | ------------------ |
| `base_url`     | Base URL     | `OWL_WEB_BASE_URL`     | Yes      | `http://localhost` |
| `port`         | Port         | `OWL_WEB_PORT`         | No       | `3000`             |
| `environment`  | Environment  | `OWL_WEB_ENVIRONMENT`  | No       | `development`      |
| `api.base_url` | API base URL | `OWL_WEB_API_BASE_URL` | Yes      | `http://localhost` |
| `api.port`     | API port     | `OWL_WEB_API_PORT`     | No       | `8000`             |

Example:

```yaml
web:
  base_url: http://localhost
  port: 3000
  environment: development
  api:
    base_url: http://localhost
    port: 8000
```

### LLM Configuration

Mapping node: `llm`

| Option     | Description  | Environment Variable | Required | Default                   |
| ---------- | ------------ | -------------------- | -------- | ------------------------- |
| `model`    | Model name   | `OWL_LLM_MODEL`      | Yes      | `ollama/mistral:instruct` |
| `base_url` | API base URL | `OWL_LLM_BASE_URL`   | No       | `http://localhost`        |
| `port`     | API port     | `OWL_LLM_PORT`       | No       | `11434`                   |
| `api_key`  | API key      | `OWL_LLM_API_KEY`    | No       |                           |

Example:

```yaml
llm:
  model: ollama/mistral:instruct
  base_url: http://localhost
  port: 11434
  api_key:
```

### Async Transcription Configuration

Mapping node: `async_transcription`

| Option     | Description | Environment Variable               | Required | Default   |
| ---------- | ----------- | ---------------------------------- | -------- | --------- |
| `provider` | Provider    | `OWL_ASYNC_TRANSCRIPTION_PROVIDER` | Yes      | `whisper` |

Example:

```yaml
async_transcription:
  provider: 'whisper'
```

### Streaming Transcription Configuration

Mapping node: `streaming_transcription`

| Option     | Description | Environment Variable                   | Required | Default   |
| ---------- | ----------- | -------------------------------------- | -------- | --------- |
| `provider` | Provider    | `OWL_STREAMING_TRANSCRIPTION_PROVIDER` | Yes      | `whisper` |

Example:

```yaml
streaming_transcription:
  provider: 'whisper'
```

### Deepgram Configuration

Mapping node: `deepgram`

| Option     | Description | Environment Variable    | Required | Default  |
| ---------- | ----------- | ----------------------- | -------- | -------- |
| `api_key`  | API key     | `OWL_DEEPGRAM_API_KEY`  | Yes      |          |
| `model`    | Model       | `OWL_DEEPGRAM_MODEL`    | Yes      | `nova-2` |
| `language` | Language    | `OWL_DEEPGRAM_LANGUAGE` | Yes      | `en-US`  |

Example:

```yaml
deepgram:
  api_key:
  model: 'nova-2'
  language: 'en-US'
```

### Async Whisper Configuration

Mapping node: `async_whisper`

| Option                         | Description                       | Environment Variable                             | Required | Default                                   |
| ------------------------------ | --------------------------------- | ------------------------------------------------ | -------- | ----------------------------------------- |
| `host`                         | Hostname                          | `OWL_ASYNC_WHISPER_HOST`                         | Yes      | `127.0.0.1`                               |
| `port`                         | Port                              | `OWL_ASYNC_WHISPER_PORT`                         | Yes      | `8010`                                    |
| `hf_token`                     | Hugging Face token                | `OWL_ASYNC_WHISPER_HF_TOKEN`                     | Yes      |                                           |
| `device`                       | Device                            | `OWL_ASYNC_WHISPER_DEVICE`                       | Yes      | `cpu`                                     |
| `compute_type`                 | Compute type                      | `OWL_ASYNC_WHISPER_COMPUTE_TYPE`                 | Yes      | `int8`                                    |
| `batch_size`                   | Batch size                        | `OWL_ASYNC_WHISPER_BATCH_SIZE`                   | Yes      | `16`                                      |
| `model`                        | Model                             | `OWL_ASYNC_WHISPER_MODEL`                        | Yes      | `tiny`                                    |
| `verification_threshold`       | Verification threshold            | `OWL_ASYNC_WHISPER_VERIFICATION_THRESHOLD`       | Yes      | `0.1`                                     |
| `verification_model_source`    | Verification model source         | `OWL_ASYNC_WHISPER_VERIFICATION_MODEL_SOURCE`    | Yes      | `speechbrain/spkrec-ecapa-voxceleb`       |
| `verification_model_directory` | Verification model save directory | `OWL_ASYNC_WHISPER_VERIFICATION_MODEL_DIRECTORY` | Yes      | `pretrained_models/spkrec-ecapa-voxceleb` |

Example:

```yaml
async_whisper:
  host: '127.0.0.1'
  port: 8010
  hf_token:
  device: cpu
  compute_type: int8
  batch_size: 16
  model: tiny
  verification_threshold: 0.1
  verification_model_source: speechbrain/spkrec-ecapa-voxceleb
  verification_model_directory: pretrained_models/spkrec-ecapa-voxceleb
```

### Streaming Whisper Configuration

Mapping node: `streaming_whisper`

| Option                         | Description                  | Environment Variable                                 | Required | Default     |
| ------------------------------ | ---------------------------- | ---------------------------------------------------- | -------- | ----------- |
| `host`                         | Hostname                     | `OWL_STREAMING_WHISPER_HOST`                         | Yes      | `127.0.0.1` |
| `port`                         | Port                         | `OWL_STREAMING_WHISPER_PORT`                         | Yes      | `8009`      |
| `model`                        | Model                        | `OWL_STREAMING_WHISPER_MODEL`                        | Yes      | `small`     |
| `language`                     | Default language             | `OWL_STREAMING_WHISPER_LANGUAGE`                     | Yes      | `en`        |
| `silero_sensitivity`           | Silero sensitivity           | `OWL_STREAMING_WHISPER_SILERO_SENSITIVITY`           | Yes      | `0.4`       |
| `webrtc_sensitivity`           | WebRTC sensitivity           | `OWL_STREAMING_WHISPER_WEBRTC_SENSITIVITY`           | Yes      | `2`         |
| `post_speech_silence_duration` | Post-speech silence duration | `OWL_STREAMING_WHISPER_POST_SPEECH_SILENCE_DURATION` | Yes      | `0.5`       |

Example:

```yaml
streaming_whisper:
  host: '127.0.0.1'
  port: 8009
  model: 'small'
  language: 'en'
  silero_sensitivity: 0.4
  webrtc_sensitivity: 2
  post_speech_silence_duration: 0.5
```

### Database Configuration

Mapping node: `database`

| Option | Description  | Environment Variable | Required | Default                  |
| ------ | ------------ | -------------------- | -------- | ------------------------ |
| `url`  | Database URL | `OWL_DATABASE_URL`   | Yes      | `sqlite:///./db.sqlite3` |

Example:

```yaml
database:
  url: sqlite:///./db.sqlite3
```

### Captures Configuration

Mapping node: `captures`

| Option      | Description                         | Environment Variable     | Required | Default    |
| ----------- | ----------------------------------- | ------------------------ | -------- | ---------- |
| `directory` | Directory where captures are stored | `OWL_CAPTURES_DIRECTORY` | Yes      | `captures` |

Example:

```yaml
captures:
  directory: captures
```

### VAD Configuration

Mapping node: `vad`

| Option      | Description                          | Environment Variable | Required | Default                 |
| ----------- | ------------------------------------ | -------------------- | -------- | ----------------------- |
| `directory` | Directory where VAD model are stored | `OWL_VAD_DIRECTORY`  | Yes      | `pretrained_models/vad` |

Example:

```yaml
vad:
  directory: pretrained_models/vad
```

### Conversation Endpointing Configuration

Mapping node: `conversation_endpointing`

| Option            | Description                  | Environment Variable                           | Required | Default |
| ----------------- | ---------------------------- | ---------------------------------------------- | -------- | ------- |
| `timeout_seconds` | Timeout in seconds           | `OWL_CONVERSATION_ENDPOINTING_TIMEOUT_SECONDS` | Yes      | `300`   |
| `min_utterances`  | Minimum number of utterances | `OWL_CONVERSATION_ENDPOINTING_MIN_UTTERANCES`  | Yes      | `2`     |

Example:

```yaml
conversation_endpointing:
  timeout_seconds: 300
  min_utterances: 2
```

### Notification Configuration

Mapping node: `notification`

| Option        | Description | Environment Variable           | Required | Default |
| ------------- | ----------- | ------------------------------ | -------- | ------- |
| `apn_team_id` | APN Team ID | `OWL_NOTIFICATION_APN_TEAM_ID` | No       |         |

Example:

```yaml
notification:
  apn_team_id:
```

### UDP Configuration

Mapping node: `udp`

| Option    | Description | Environment Variable | Required | Default   |
| --------- | ----------- | -------------------- | -------- | --------- |
| `enabled` | Enabled     | `OWL_UDP_ENABLED`    | Yes      | `false`   |
| `host`    | Host        | `OWL_UDP_HOST`       | No       | `0.0.0.0` |
| `port`    | Port        | `OWL_UDP_PORT`       | No       | `8001`    |

Example:

```yaml
udp:
  enabled: false
  host: 0.0.0.0x
  port: 8001
```

### Google Maps Configuration

Mapping node: `google_maps`

| Option    | Description | Environment Variable      | Required | Default |
| --------- | ----------- | ------------------------- | -------- | ------- |
| `api_key` | API key     | `OWL_GOOGLE_MAPS_API_KEY` | No       |         |

Example:

```yaml
google_maps:
  api_key:
```

### Bing Configuration

Mapping node: `bing`

| Option             | Description      | Environment Variable        | Required | Default |
| ------------------ | ---------------- | --------------------------- | -------- | ------- |
| `subscription_key` | Subscription key | `OWL_BING_SUBSCRIPTION_KEY` | No       |         |

Example:

```yaml
bing:
  subscription_key:
```

### Prompt Configuration

Mapping node: `prompt`

To view the full default text, see the `.config/sample-config.yaml` file.

| Option                               | Description                        | Environment Variable                            | Required | Default |
| ------------------------------------ | ---------------------------------- | ----------------------------------------------- | -------- | ------- |
| `suggest_links_system_message`       | Suggest links message prompt       | `OWL_PROMPT_SUGGEST_LINKS_SYSTEM_MESSAGE`       | Yes      | `...`   |
| `summarization_system_message`       | Summarization message prompt       | `OWL_PROMPT_SUMMARIZATION_SYSTEM_MESSAGE`       | Yes      | `...`   |
| `short_summarization_system_message` | Short summarization message prompt | `OWL_PROMPT_SHORT_SUMMARIZATION_SYSTEM_MESSAGE` | Yes      | `...`   |

Example:

```yaml
prompts:
  suggest_links_system_message: `...`
  summarization_system_message: '...'
  short_summarization_system_message: '...'
```
