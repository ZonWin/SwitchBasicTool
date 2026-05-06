"""Telnet transport implementation using raw sockets."""

from __future__ import annotations

import socket
import time

from ..exceptions import AuthenticationError, CommandTimeoutError, ConnectionError
from .base import BaseTransport

IAC = 255
DONT = 254
DO = 253
WONT = 252
WILL = 251
SB = 250
SE = 240

OPT_BINARY = 0
OPT_ECHO = 1
OPT_SUPPRESS_GO_AHEAD = 3


class TelnetTransport(BaseTransport):
    """Simple Telnet transport with minimal option negotiation support."""

    def __init__(self, config, vendor_profile) -> None:
        super().__init__(config, vendor_profile)
        self._socket: socket.socket | None = None
        self._pending_bytes = bytearray()

    def connect(self) -> None:
        self.close()
        try:
            sock = socket.create_connection(
                (self.config.host, self.config.resolved_port()),
                timeout=self.config.connect_timeout,
            )
        except OSError as exc:  # pragma: no cover - depends on network conditions
            raise ConnectionError(
                f"Failed to establish Telnet connection to {self.config.host}:{self.config.resolved_port()}."
            ) from exc

        self._socket = sock
        self._pending_bytes.clear()

        if self.config.username is not None or self.config.password is not None:
            try:
                self._perform_login()
            except Exception:
                self.close()
                raise

    def close(self) -> None:
        if self._socket is not None:
            try:
                self._socket.close()
            finally:
                self._socket = None
        self._pending_bytes.clear()

    def is_alive(self) -> bool:
        return self._socket is not None

    def write(self, data: str) -> None:
        self.ensure_alive()
        assert self._socket is not None
        try:
            self._socket.sendall(data.encode(self.config.encoding))
        except OSError as exc:  # pragma: no cover - depends on network conditions
            raise ConnectionError("Failed while sending data over Telnet.") from exc

    def read(self, timeout: float | None = None) -> str:
        self.ensure_alive()
        assert self._socket is not None

        deadline = time.monotonic() + (timeout if timeout is not None else self.config.read_timeout)
        chunks = bytearray()

        while time.monotonic() < deadline:
            remaining = max(deadline - time.monotonic(), 0.01)
            try:
                self._socket.settimeout(min(self.config.read_timeout, remaining))
                data = self._socket.recv(self.config.buffer_size)
            except socket.timeout:
                break
            except OSError as exc:  # pragma: no cover - depends on network conditions
                raise ConnectionError("Failed while receiving data over Telnet.") from exc

            if not data:
                break

            cleaned = self._consume_telnet_bytes(data)
            if cleaned:
                chunks.extend(cleaned)
                if len(data) < self.config.buffer_size:
                    break

        return chunks.decode(self.config.encoding, errors="ignore")

    def _perform_login(self) -> None:
        login_patterns = (
            self.username_prompt_pattern,
            self.password_prompt_pattern,
            self.prompt_pattern,
        )

        try:
            _, matched = self.read_until_any(login_patterns, timeout=self.config.timeout)
        except CommandTimeoutError as exc:
            raise AuthenticationError(
                "Telnet login timed out while waiting for username, password, or device prompt."
            ) from exc

        if matched == self.prompt_pattern:
            return

        if matched == self.username_prompt_pattern:
            if not self.config.username:
                raise AuthenticationError("Telnet server requested a username but none was provided.")
            self.write_line(self.config.username)
            try:
                _, matched = self.read_until_any(
                    (self.password_prompt_pattern, self.prompt_pattern),
                    timeout=self.config.timeout,
                )
            except CommandTimeoutError as exc:
                raise AuthenticationError("Timed out after sending Telnet username.") from exc

        if matched == self.password_prompt_pattern:
            if self.config.password is None:
                raise AuthenticationError("Telnet server requested a password but none was provided.")
            self.write_line(self.config.password)
            try:
                _, matched = self.read_until_any((self.prompt_pattern,), timeout=self.config.timeout)
            except CommandTimeoutError as exc:
                raise AuthenticationError("Timed out after sending Telnet password.") from exc

        if matched != self.prompt_pattern:
            raise AuthenticationError("Telnet login did not reach a device prompt.")

    def _consume_telnet_bytes(self, data: bytes) -> bytes:
        assert self._socket is not None

        buffer = self._pending_bytes + data
        self._pending_bytes = bytearray()
        output = bytearray()
        index = 0

        while index < len(buffer):
            current = buffer[index]
            if current != IAC:
                output.append(current)
                index += 1
                continue

            if index + 1 >= len(buffer):
                self._pending_bytes.extend(buffer[index:])
                break

            command = buffer[index + 1]

            if command == IAC:
                output.append(IAC)
                index += 2
                continue

            if command in {DO, DONT, WILL, WONT}:
                if index + 2 >= len(buffer):
                    self._pending_bytes.extend(buffer[index:])
                    break
                option = buffer[index + 2]
                self._reply_to_negotiation(command, option)
                index += 3
                continue

            if command == SB:
                end = buffer.find(bytes([IAC, SE]), index + 2)
                if end == -1:
                    self._pending_bytes.extend(buffer[index:])
                    break
                index = end + 2
                continue

            index += 2

        return bytes(output)

    def _reply_to_negotiation(self, command: int, option: int) -> None:
        assert self._socket is not None

        if command == WILL:
            reply = DO if option in {OPT_BINARY, OPT_ECHO, OPT_SUPPRESS_GO_AHEAD} else DONT
        elif command == DO:
            reply = WILL if option in {OPT_BINARY, OPT_SUPPRESS_GO_AHEAD} else WONT
        else:
            return

        self._socket.sendall(bytes([IAC, reply, option]))
