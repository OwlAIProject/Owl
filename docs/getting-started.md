# Getting Started

This guide will walk you through the quickest way to get your Owl project up and running.

## Prerequisites

Before you start, make sure you have the following installed:

- [FFmpeg](https://ffmpeg.org/download.html)
- [Git](https://git-scm.com/downloads)
- [Node.js 18+](https://nodejs.org/en/download)
- [Ollama](https://ollama.com/) (Optional. Used for local LLMs)
- [Poetry](https://python-poetry.org/docs/#installation)
- [Python 3.11+](https://www.python.org/downloads/)

## Setup

1. Clone the Owl repository, install dependencies and activate your virtual environment:

```bash
git clone https://github.com/OwlAIProject/Owl.git
cd Owl
poetry install
poetry shell
```

2. Install configuration files:

Run the `owl setup` command and follow the prompts to create configuration files in the project's root directory.

```bash
owl setup
```

3. Run server:

Start the server using the following command:

```bash
owl serve --web
```

You can now access your Owl server at `http://localhost:3000`. Note, you'll need to proceed with the next steps below before you can use Owl's web interface.

## Next steps

To further configure your Owl project, see the [Server Configuration](server-configuration.md) guide.
