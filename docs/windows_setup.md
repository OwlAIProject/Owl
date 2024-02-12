# Always-on Perceptive AI

[<< Home](../README.md)

## Windows Setup

To install the server, first clone the git repository to a directory on disk and then perform these steps:

- [Anaconda](https://www.anaconda.com/download) is the recommended way to manage your Python environment. Install it first.
- Open an Anaconda Command Prompt and create a new Python 3.11 environment named `ai` with this command: `conda create -n ai python=3.11`
- Switch to the environment: `conda activate ai`
- In the root of the source tree, where `requirements-windows.txt` is, install the required packages: `pip install -r requirements-windows.txt`
- Test that you can run the server by issuing this command from the root directory, which will print usage instructions: `python -m untitledai.core.cli --help`

Once installed, you will need to also [configure the server](./server_configuration.md) (API tokens, etc.)

To run the server:

- Open up an Anaconda Command Prompt and switch to the `ai` environment, if you have not already done so: `conda activate ai`
- Start the server with the `serve` command and make sure to specify the host as `0.0.0.0` so it is accessible remotely: `python -m untitledai.core.cli server --host=0.0.0.0`. By default, the configuration in `config.yaml` is used, but this may be overridden with the `--config` option.

[<< Home](../README.md)
