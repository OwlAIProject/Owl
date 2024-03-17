# Environment Variables

`owl` supports environment variables through a `.env` file in the root directory. Environment variables override and extend configuration options in the `config.yaml` file. They allow for per-environment configuration (e.g., development, test, production) and may also be used within custom functions or prompts.

## Prerequisites

If you haven't already, make sure you've completed the steps in the [Getting Started](getting-started.md) guide.

## Overriding `config.yaml` Settings

To override a setting from `config.yaml`, modify the corresponding environment variable in your `.env` file. For example, to override the `async_whisper` section's `hf_token` setting, modify the `OWL_ASYNC_WHISPER_HF_TOKEN` environment variable in your `.env` file:

```
OWL_ASYNC_WHISPER_HF_TOKEN=your_hugging_face_token
```

The value specified in the `.env` file will take precedence over the value in `config.yaml`.

> **Note**:
>
> Empty environment variables will unset the corresponding setting in `config.yaml`.

## Naming Convention

Environment variable names follow a specific naming convention based on the structure of the `config.yaml` file. The convention consists of three parts:

```
OWL_SECTION_KEY
```

- `OWL`: The prefix to denote the environment variable is part of the `owl` project.
- `SECTION`: The name of the section (mapping node) in the YAML file.
- `KEY`: The key of the scalar node within the section.

**Example #1:**

```yaml
async_whisper:
  hf_token: your_hugging_face_token
```

In this example, the corresponding environment variable would be:

```
OWL_ASYNC_WHISPER_HF_TOKEN
```

**Example #2:**

```yaml
web:
  base_url: http://localhost
  port: 3000
  environment: development
  backend:
    base_url: http://localhost
    port: 8000
```

In this example, the corresponding environment variables would be:

```
OWL_WEB_BASE_URL
OWL_WEB_PORT
OWL_WEB_ENVIRONMENT
OWL_WEB_BACKEND_BASE_URL
OWL_WEB_BACKEND_PORT
```
