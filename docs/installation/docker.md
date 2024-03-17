# Docker Installation

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

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

3. Launch Docker container

```bash
docker compose up
```

You can now access your Owl server at `http://localhost:3000`. Note, you'll need to proceed with the next steps below before you can use Owl's web interface.

## Next steps

To further configure your Owl project, see the [Server Configuration](../server-configuration.md) guide.
