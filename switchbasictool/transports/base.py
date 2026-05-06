"""Abstract transport interface used by the client."""

from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod
from typing import Sequence

from ..exceptions import CommandTimeoutError, TransportClosedError
from ..models import ConnectionConfig
from ..vendors import VendorProfile


class BaseTransport(ABC):
    """Common behavior shared by concrete transport implementations."""

    def __init__(self, config: ConnectionConfig, vendor_profile: VendorProfile) -> None:
        self.config = config
        self.vendor_profile = vendor_profile

    @property
    def prompt_pattern(self) -> str:
        return self.config.prompt_pattern or self.vendor_profile.prompt_pattern

    @property
    def more_patterns(self) -> tuple[str, ...]:
        return self.config.more_patterns or self.vendor_profile.more_patterns

    @property
    def username_prompt_pattern(self) -> str:
        return self.config.username_prompt_pattern or self.vendor_profile.username_prompt_pattern

    @property
    def password_prompt_pattern(self) -> str:
        return self.config.password_prompt_pattern or self.vendor_profile.password_prompt_pattern

    @abstractmethod
    def connect(self) -> None:
        """Open a session."""

    @abstractmethod
    def close(self) -> None:
        """Close the session."""

    @abstractmethod
    def is_alive(self) -> bool:
        """Return whether the session is still usable."""

    @abstractmethod
    def write(self, data: str) -> None:
        """Send raw data to the remote endpoint."""

    @abstractmethod
    def read(self, timeout: float | None = None) -> str:
        """Read data from the remote endpoint."""

    def ensure_alive(self) -> None:
        if not self.is_alive():
            raise TransportClosedError("Transport is not connected.")

    def write_line(self, line: str) -> None:
        self.write(f"{line}{self.config.resolved_newline()}")

    def read_until(self, pattern: str, timeout: float | None = None) -> str:
        data, _ = self.read_until_any((pattern,), timeout=timeout)
        return data

    def read_until_any(
        self,
        patterns: Sequence[str],
        timeout: float | None = None,
    ) -> tuple[str, str]:
        self.ensure_alive()

        if not patterns:
            raise ValueError("patterns cannot be empty")

        compiled_patterns = [re.compile(pattern) for pattern in patterns]
        deadline = time.monotonic() + (timeout if timeout is not None else self.config.timeout)
        chunks: list[str] = []

        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            chunk = self.read(timeout=min(self.config.read_timeout, max(remaining, 0.01)))
            if chunk:
                chunks.append(chunk)
                current = "".join(chunks)
                for pattern, regex in zip(patterns, compiled_patterns, strict=True):
                    if regex.search(current):
                        return current, pattern
            elif remaining <= 0:
                break

        combined = "".join(chunks)
        raise CommandTimeoutError(
            f"Timed out after {timeout or self.config.timeout:.1f}s while waiting for patterns: {patterns!r}. "
            f"Collected data length: {len(combined)}"
        )

    def drain(self, idle_timeout: float = 0.2, overall_timeout: float = 1.0) -> str:
        self.ensure_alive()

        deadline = time.monotonic() + overall_timeout
        chunks: list[str] = []

        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            chunk = self.read(timeout=min(idle_timeout, remaining))
            if not chunk:
                break
            chunks.append(chunk)

        return "".join(chunks)
