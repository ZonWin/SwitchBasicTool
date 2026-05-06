"""High-level client that unifies SSH and Telnet behavior."""

from __future__ import annotations

import re
import time

from .exceptions import CommandTimeoutError, PromptNotFoundError, TransportClosedError
from .models import CommandResult, ConnectionConfig
from .transports import BaseTransport, SSHTransport, TelnetTransport
from .vendors import VendorProfile, resolve_vendor_profile

ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


class NetworkDeviceClient:
    """Reusable network-device client for switch automation."""

    def __init__(self, config: ConnectionConfig) -> None:
        self.config = config
        self.vendor_profile: VendorProfile = resolve_vendor_profile(
            config.vendor,
            config.vendor_profile,
        )
        self.transport: BaseTransport = self._build_transport()
        self._initial_output = ""

    @property
    def prompt_pattern(self) -> str:
        return self.config.prompt_pattern or self.vendor_profile.prompt_pattern

    @property
    def more_patterns(self) -> tuple[str, ...]:
        return self.config.more_patterns or self.vendor_profile.more_patterns

    @property
    def session_init_commands(self) -> tuple[str, ...]:
        commands: list[str] = []
        vendor_commands = self.vendor_profile.session_init_commands if self.config.use_vendor_session_init else ()
        for command in (*vendor_commands, *self.config.session_init_commands):
            if command and command not in commands:
                commands.append(command)
        return tuple(commands)

    def connect(self) -> "NetworkDeviceClient":
        if self.transport.is_alive():
            return self

        self.transport.connect()
        self._prime_session()
        return self

    def disconnect(self) -> None:
        self.transport.close()

    def close(self) -> None:
        self.disconnect()

    def is_alive(self) -> bool:
        return self.transport.is_alive()

    def send(self, data: str) -> None:
        self._ensure_connected()
        self.transport.write(data)

    def recv(self, timeout: float | None = None) -> str:
        self._ensure_connected()
        return self.transport.read(timeout=timeout)

    def read_until(self, pattern: str, timeout: float | None = None) -> str:
        self._ensure_connected()
        return self.transport.read_until(pattern, timeout=timeout)

    def read_until_prompt(self, timeout: float | None = None) -> str:
        self._ensure_connected()
        return self._collect_until_prompt(timeout=timeout)

    def send_command(self, command: str, timeout: float | None = None) -> CommandResult:
        self._ensure_connected()

        prepared_command = command.rstrip("\r\n")
        self.transport.drain(idle_timeout=0.1, overall_timeout=0.2)

        start = time.monotonic()
        self.transport.write_line(prepared_command)
        raw_output = self._collect_until_prompt(timeout=timeout)
        duration = time.monotonic() - start
        output = self._clean_output(prepared_command, raw_output)

        return CommandResult(
            command=prepared_command,
            raw_output=raw_output,
            output=output,
            duration=duration,
            timed_out=False,
        )

    def send_commands(
        self,
        commands: list[str] | tuple[str, ...],
        timeout: float | None = None,
    ) -> list[CommandResult]:
        return [self.send_command(command, timeout=timeout) for command in commands]

    def __enter__(self) -> "NetworkDeviceClient":
        return self.connect()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.disconnect()

    def _build_transport(self) -> BaseTransport:
        if self.config.protocol == "ssh":
            return SSHTransport(self.config, self.vendor_profile)
        if self.config.protocol == "telnet":
            return TelnetTransport(self.config, self.vendor_profile)
        raise ValueError(f"Unsupported protocol: {self.config.protocol}")

    def _ensure_connected(self) -> None:
        if not self.transport.is_alive():
            raise TransportClosedError("Client is not connected. Call connect() first.")

    def _prime_session(self) -> None:
        try:
            self._initial_output = self._collect_until_prompt(timeout=min(self.config.timeout, 5.0))
        except PromptNotFoundError:
            self._initial_output = self.transport.drain(idle_timeout=0.2, overall_timeout=1.0)

        for command in self.session_init_commands:
            self.send_command(command, timeout=self.config.timeout)

    def _collect_until_prompt(self, timeout: float | None = None) -> str:
        patterns = (*self.more_patterns, self.prompt_pattern)
        deadline = time.monotonic() + (timeout if timeout is not None else self.config.timeout)
        chunks: list[str] = []

        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            try:
                data, matched = self.transport.read_until_any(patterns, timeout=max(remaining, 0.1))
            except CommandTimeoutError as exc:
                raise PromptNotFoundError(
                    f"Timed out after {timeout or self.config.timeout:.1f}s while waiting for device prompt."
                ) from exc
            chunks.append(data)

            if matched == self.prompt_pattern:
                return "".join(chunks)

            self.transport.write(" ")

        raise PromptNotFoundError(
            f"Timed out after {timeout or self.config.timeout:.1f}s while waiting for device prompt."
        )

    def _clean_output(self, command: str, raw_output: str) -> str:
        output = raw_output.replace("\r\n", "\n").replace("\r", "\n")
        output = output.replace("\x08", "")
        output = ANSI_ESCAPE_RE.sub("", output)

        for pattern in self.more_patterns:
            output = re.sub(pattern, "", output, flags=re.MULTILINE)

        if self.config.command_echo and command:
            escaped_command = re.escape(command.strip())
            output = re.sub(
                rf"(?m)^\s*{escaped_command}\s*$\n?",
                "",
                output,
                count=1,
            )

        output = self._strip_trailing_prompt(output)
        return output.strip("\n")

    def _strip_trailing_prompt(self, text: str) -> str:
        stripped = text.rstrip()
        matches = list(re.finditer(self.prompt_pattern, stripped))
        if matches and matches[-1].end() == len(stripped):
            return stripped[: matches[-1].start()].rstrip()
        return stripped
