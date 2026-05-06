"""Dataclasses shared across the package."""

from __future__ import annotations

from dataclasses import dataclass, field

from .vendors import VendorProfile, _normalize_vendor_name


@dataclass(slots=True)
class ConnectionConfig:
    """Connection settings for one network device session."""

    host: str
    protocol: str = "ssh"
    username: str | None = None
    password: str | None = None
    port: int | None = None
    connect_timeout: float = 10.0
    timeout: float = 10.0
    read_timeout: float = 1.0
    banner_timeout: float = 30.0
    auth_timeout: float = 20.0
    encoding: str = "utf-8"
    newline: str | None = None
    vendor: str = "generic"
    vendor_profile: VendorProfile | None = None
    prompt_pattern: str | None = None
    more_patterns: tuple[str, ...] = field(default_factory=tuple)
    username_prompt_pattern: str | None = None
    password_prompt_pattern: str | None = None
    session_init_commands: tuple[str, ...] = field(default_factory=tuple)
    use_vendor_session_init: bool = True
    strict_host_key: bool = False
    allow_agent: bool = False
    look_for_keys: bool = False
    key_filename: str | None = None
    ssh_strict_kex: bool | None = None
    ssh_local_version: str | None = None
    buffer_size: int = 65535
    command_echo: bool = True

    def __post_init__(self) -> None:
        self.host = self.host.strip()
        self.protocol = self.protocol.strip().lower()
        self.vendor = _normalize_vendor_name(self.vendor)
        self.more_patterns = tuple(self.more_patterns)
        self.session_init_commands = tuple(self.session_init_commands)

        if not self.host:
            raise ValueError("host cannot be empty")
        if self.protocol not in {"ssh", "telnet"}:
            raise ValueError("protocol must be either 'ssh' or 'telnet'")
        if self.buffer_size <= 0:
            raise ValueError("buffer_size must be greater than 0")
        if self.banner_timeout <= 0:
            raise ValueError("banner_timeout must be greater than 0")
        if self.auth_timeout <= 0:
            raise ValueError("auth_timeout must be greater than 0")

    def resolved_port(self) -> int:
        """Return the explicit port or the protocol default."""

        if self.port is not None:
            return self.port
        return 22 if self.protocol == "ssh" else 23

    def resolved_newline(self) -> str:
        """Return an explicit newline or the protocol default."""

        if self.newline is not None:
            return self.newline
        return "\n" if self.protocol == "ssh" else "\r\n"


@dataclass(frozen=True, slots=True)
class CommandResult:
    """The result of one command round trip."""

    command: str
    raw_output: str
    output: str
    duration: float
    timed_out: bool = False
