"""
Defines helper methods useful for creating tunnels.
"""
OWL_SHARE_SERVER_ADDRESS = "live.owlai.dev:7000"
from .tunneling import Tunnel
import secrets

def setup_tunnel(
    local_host: str, local_port: int
) -> str:
    share_server_address = OWL_SHARE_SERVER_ADDRESS
    remote_host, remote_port = share_server_address.split(":")
    remote_port = int(remote_port)

    try:
        tunnel = Tunnel(remote_host, remote_port, local_host, local_port, secrets.token_urlsafe(32))
        address = tunnel.start_tunnel()
        return address
    except Exception as e:
        raise RuntimeError(str(e)) from e
