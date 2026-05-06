"""SSH transport implementation built on Paramiko."""

from __future__ import annotations

import time

from ..exceptions import AuthenticationError, ConnectionError, DependencyMissingError
from .base import BaseTransport

try:
    import paramiko
except ImportError as exc:  # pragma: no cover - depends on runtime environment
    paramiko = None
    _PARAMIKO_IMPORT_ERROR = exc
else:
    _PARAMIKO_IMPORT_ERROR = None


class SSHTransport(BaseTransport):
    """SSH transport using an interactive shell channel."""

    def __init__(self, config, vendor_profile) -> None:
        super().__init__(config, vendor_profile)
        self._client = None
        self._channel = None

    def connect(self) -> None:
        if paramiko is None:
            raise DependencyMissingError(
                "SSH transport requires 'paramiko'. Install project dependencies first."
            ) from _PARAMIKO_IMPORT_ERROR

        self.close()
        client = paramiko.SSHClient()
        if self.config.strict_host_key:
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
        else:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            connect_kwargs = {
                "hostname": self.config.host,
                "port": self.config.resolved_port(),
                "username": self.config.username,
                "password": self.config.password,
                "key_filename": self.config.key_filename,
                "timeout": self.config.connect_timeout,
                "banner_timeout": self.config.banner_timeout,
                "auth_timeout": self.config.auth_timeout,
                "allow_agent": self.config.allow_agent,
                "look_for_keys": self.config.look_for_keys,
            }

            transport_factory = self._build_transport_factory()
            if transport_factory is not None:
                connect_kwargs["transport_factory"] = transport_factory

            client.connect(
                **connect_kwargs,
            )
            channel = client.invoke_shell(width=200, height=2000)
            channel.settimeout(self.config.read_timeout)
        except paramiko.AuthenticationException as exc:
            client.close()
            raise AuthenticationError(f"SSH authentication failed for {self.config.host}.") from exc
        except paramiko.SSHException as exc:
            client.close()
            raise ConnectionError(self._build_ssh_exception_message(exc)) from exc
        except Exception as exc:  # pragma: no cover - depends on network conditions
            client.close()
            raise ConnectionError(
                f"Failed to establish SSH connection to {self.config.host}:{self.config.resolved_port()}."
            ) from exc

        self._client = client
        self._channel = channel

    def close(self) -> None:
        if self._channel is not None:
            try:
                self._channel.close()
            finally:
                self._channel = None

        if self._client is not None:
            try:
                self._client.close()
            finally:
                self._client = None

    def is_alive(self) -> bool:
        return bool(
            self._client is not None
            and self._channel is not None
            and not self._channel.closed
            and self._channel.active
        )

    def write(self, data: str) -> None:
        self.ensure_alive()
        assert self._channel is not None
        self._channel.sendall(data.encode(self.config.encoding))

    def read(self, timeout: float | None = None) -> str:
        self.ensure_alive()
        assert self._channel is not None

        deadline = time.monotonic() + (timeout if timeout is not None else self.config.read_timeout)
        chunks = bytearray()

        while time.monotonic() < deadline:
            if self._channel.recv_ready():
                data = self._channel.recv(self.config.buffer_size)
                if not data:
                    break
                chunks.extend(data)
                if not self._channel.recv_ready():
                    break
            else:
                time.sleep(0.05)

        return chunks.decode(self.config.encoding, errors="ignore")

    def _build_transport_factory(self):
        if self.config.ssh_strict_kex is None and self.config.ssh_local_version is None:
            return None

        strict_kex = self.config.ssh_strict_kex
        local_version = self.config.ssh_local_version

        def transport_factory(sock, *args, **kwargs):
            if strict_kex is not None:
                kwargs["strict_kex"] = strict_kex
            transport = paramiko.Transport(sock, *args, **kwargs)
            if local_version is not None:
                transport.local_version = local_version
            return transport

        return transport_factory

    def _build_ssh_exception_message(self, exc: Exception) -> str:
        base_message = (
            f"Failed to establish SSH connection to {self.config.host}:{self.config.resolved_port()}. "
            f"Paramiko reported: {exc}"
        )
        detail = str(exc)

        if "Error reading SSH protocol banner" in detail:
            return (
                f"{base_message}. The remote side closed the TCP session before a valid SSH banner "
                "was received. This usually means one of the following: the target port is not really "
                "providing SSH, the device dropped the connection early, or the device is responding too "
                "slowly. Try increasing banner_timeout, probing port 22 with '--probe-ssh-banner', or "
                "trying Telnet if this switch only has Telnet enabled."
            )

        lowered = detail.lower()
        if "incompatible ssh peer" in lowered or "no acceptable" in lowered:
            return (
                f"{base_message}. The device replied, but SSH algorithm negotiation failed. "
                "This is the stage where old KEX/cipher compatibility usually matters. "
                "Try '--disable-ssh-strict-kex' first, and if it still fails we can add more explicit "
                "legacy algorithm controls."
            )

        return base_message
