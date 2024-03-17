import atexit
import os
import platform
import re
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import List
import logging

import httpx

VERSION = "0.2"
CURRENT_TUNNELS: List["Tunnel"] = []

machine = platform.machine()
if machine == "x86_64":
    machine = "amd64"

BINARY_REMOTE_NAME = f"frpc_{platform.system().lower()}_{machine.lower()}"
EXTENSION = ".exe" if os.name == "nt" else ""
BINARY_URL = f"https://cdn-media.huggingface.co/frpc-gradio-{VERSION}/{BINARY_REMOTE_NAME}{EXTENSION}"

BINARY_FILENAME = f"{BINARY_REMOTE_NAME}_v{VERSION}"
BINARY_FOLDER = Path(__file__).parent
BINARY_PATH = f"{BINARY_FOLDER / BINARY_FILENAME}"

TUNNEL_TIMEOUT_SECONDS = 30
TUNNEL_ERROR_MESSAGE = (
    "Could not create share URL. "
    "Please check the appended log from frpc for more information:"
)

logger = logging.getLogger(__name__)

class Tunnel:
    def __init__(self, remote_host, remote_port, local_host, local_port, share_token) -> None:
        self.proc = None
        self.url = None
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.local_host = local_host
        self.local_port = local_port
        self.share_token = share_token
    @staticmethod
    def download_binary():
        if not Path(BINARY_PATH).exists():
            resp = httpx.get(BINARY_URL, timeout=30)

            if resp.status_code == 403:
                raise OSError(
                    f"Cannot set up a share link as this platform is incompatible. Please "
                    f"create a GitHub issue with information about your platform: {platform.uname()}"
                )
            resp.raise_for_status()

            # Save file data to local copy
            with open(BINARY_PATH, "wb") as file:
                file.write(resp.content)
            st = os.stat(BINARY_PATH)
            os.chmod(BINARY_PATH, st.st_mode | stat.S_IEXEC)

    def start_tunnel(self) -> str:
        self.download_binary()
        self.url = self._start_tunnel(BINARY_PATH)
        return self.url
    
    def kill(self):
        if self.proc is not None:
            logger.info(f"Killing tunnel {self.local_host}:{self.local_port} <> {self.url}")
            self.proc.terminate()
            self.proc = None
    
    def _start_tunnel(self, binary: str) -> str:
        CURRENT_TUNNELS.append(self)
        command = [
            binary,
            "http",
            "-n",
            self.share_token,
            "-l",
            str(self.local_port),
            "-i",
            self.local_host,
            "--uc",
            "--sd",
            "random",
            "--ue",
            "--server_addr",
            f"{self.remote_host}:{self.remote_port}",
            "--disable_log_color"
        ]
        self.proc = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        atexit.register(self.kill)
        return self._read_url_from_tunnel_stream()
    
    def _read_url_from_tunnel_stream(self) -> str:
        start_timestamp = time.time()

        log = []
        url = ""

        def _raise_tunnel_error():
            log_text = "\n".join(log)
            logger.error(log_text)
            raise ValueError(f"{TUNNEL_ERROR_MESSAGE}\n{log_text}")
        
        while url == "":
            if time.time() - start_timestamp >= TUNNEL_TIMEOUT_SECONDS:
                _raise_tunnel_error()

            assert self.proc is not None
            if self.proc.stdout is None:
                continue

            line = self.proc.stdout.readline()
            line = line.decode("utf-8")

            if line == "":
                continue

            log.append(line.strip())

            if "start proxy success" in line:
                result = re.search("start proxy success: (.+)\n", line)
                if result is None:
                    _raise_tunnel_error()
                else:
                    url = result.group(1)
            elif "login to server failed" in line:
                _raise_tunnel_error()
        return url