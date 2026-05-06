"""Manual test entrypoint for real network-device sessions."""

from __future__ import annotations

import argparse
import getpass
import socket
import sys
import time
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from switchbasictool import (
        ConnectionConfig,
        NetworkDeviceClient,
        SwitchBasicToolError,
        list_vendor_profiles,
        resolve_vendor_profile,
    )
else:
    from . import (
        ConnectionConfig,
        NetworkDeviceClient,
        SwitchBasicToolError,
        list_vendor_profiles,
        resolve_vendor_profile,
    )

DEFAULT_COMMANDS_BY_VENDOR: dict[str, tuple[str, ...]] = {
    "huawei": (
        "display version",
        "display current-configuration | include sysname",
        "display interface brief",
    ),
    "h3c": (
        "display version",
        "display current-configuration | include sysname",
        "display interface brief",
    ),
    "cisco_ios": (
        "show version",
        "show running-config | include hostname",
    ),
    "juniper": (
        "show version",
        "show configuration system host-name | display set",
    ),
    "arista_eos": (
        "show version",
        "show running-config | include hostname",
    ),
    "zte": (
        "show version",
        "show running-config | include hostname",
        "show ip interface brief",
        "show interface brief",
    ),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manual smoke-test tool for SSH/Telnet switch sessions.",
    )
    parser.add_argument("--host", help="Target device IP or hostname.")
    parser.add_argument("--protocol", choices=("ssh", "telnet"), default="ssh")
    parser.add_argument("--port", type=int, help="Override the default port for the protocol.")
    parser.add_argument("--username", help="Login username.")
    parser.add_argument("--password", help="Login password.")
    parser.add_argument(
        "--ask-password",
        action="store_true",
        help="Prompt for a password even if --password was not provided.",
    )
    parser.add_argument("--vendor", default="generic", help="Vendor profile name or alias.")
    parser.add_argument("--prompt-pattern", help="Override the device prompt regex.")
    parser.add_argument(
        "--command",
        action="append",
        default=[],
        help="Command to execute. Repeat this option to run multiple commands.",
    )
    parser.add_argument(
        "--command-file",
        help="Read commands from a file, one command per line. Empty lines and '#' comments are ignored.",
    )
    parser.add_argument(
        "--init-command",
        action="append",
        default=[],
        help="Extra session-init command. Repeat to append more commands.",
    )
    parser.add_argument(
        "--disable-vendor-init",
        action="store_true",
        help="Skip built-in vendor session-init commands such as pagination disable commands.",
    )
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--read-timeout", type=float, default=1.0)
    parser.add_argument("--banner-timeout", type=float, default=30.0)
    parser.add_argument("--auth-timeout", type=float, default=20.0)
    parser.add_argument("--encoding", default="utf-8")
    parser.add_argument("--key-file", help="SSH private key path.")
    parser.add_argument("--strict-host-key", action="store_true")
    parser.add_argument("--allow-agent", action="store_true")
    parser.add_argument("--look-for-keys", action="store_true")
    parser.add_argument(
        "--ssh-local-version",
        help="Override the local SSH version string, for example 'SSH-2.0-PuTTY_Release_0.70'.",
    )
    parser.add_argument(
        "--disable-ssh-strict-kex",
        action="store_true",
        help="Disable Paramiko strict KEX mode for older SSH servers.",
    )
    parser.add_argument("--no-command-echo", action="store_true")
    parser.add_argument("--show-raw", action="store_true", help="Print raw output instead of cleaned output.")
    parser.add_argument(
        "--probe-ssh-banner",
        action="store_true",
        help="Only probe whether the target port returns a valid SSH banner, then exit.",
    )
    parser.add_argument(
        "--probe-timeout",
        type=float,
        default=5.0,
        help="Timeout used by --probe-ssh-banner.",
    )
    parser.add_argument(
        "--show-profile",
        action="store_true",
        help="Print the resolved vendor profile before running commands.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enter an interactive command loop after running scripted commands.",
    )
    parser.add_argument(
        "--list-vendors",
        action="store_true",
        help="Print built-in vendor profiles and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_vendors:
        _print_vendors()
        return 0

    if not args.host:
        parser.error("--host is required unless --list-vendors is used.")

    if args.probe_ssh_banner:
        return _probe_ssh_banner(
            host=args.host,
            port=args.port or 22,
            timeout=args.probe_timeout,
            local_version=args.ssh_local_version,
        )

    password = _resolve_password(
        provided_password=args.password,
        ask_password=args.ask_password,
        protocol=args.protocol,
        username=args.username,
        key_file=args.key_file,
        allow_agent=args.allow_agent,
        look_for_keys=args.look_for_keys,
    )
    commands = _collect_commands(args.command, args.command_file)
    used_default_commands = False

    if not commands and not args.interactive:
        commands = _get_default_commands(args.vendor)
        used_default_commands = bool(commands)
        if not commands:
            parser.error("No commands were provided. Use --command, --command-file, or --interactive.")

    config = ConnectionConfig(
        host=args.host,
        protocol=args.protocol,
        username=args.username,
        password=password,
        port=args.port,
        connect_timeout=args.connect_timeout,
        timeout=args.timeout,
        read_timeout=args.read_timeout,
        banner_timeout=args.banner_timeout,
        auth_timeout=args.auth_timeout,
        encoding=args.encoding,
        vendor=args.vendor,
        prompt_pattern=args.prompt_pattern,
        session_init_commands=tuple(args.init_command),
        use_vendor_session_init=not args.disable_vendor_init,
        strict_host_key=args.strict_host_key,
        allow_agent=args.allow_agent,
        look_for_keys=args.look_for_keys,
        key_filename=args.key_file,
        ssh_strict_kex=False if args.disable_ssh_strict_kex else None,
        ssh_local_version=args.ssh_local_version,
        command_echo=not args.no_command_echo,
    )

    try:
        with NetworkDeviceClient(config) as client:
            if args.show_profile:
                _print_profile(client)

            if used_default_commands:
                print(f"Using default commands for vendor '{client.vendor_profile.name}'.")

            for command in commands:
                _run_command(client, command, show_raw=args.show_raw)

            if args.interactive:
                _interactive_loop(client, show_raw=args.show_raw)
    except (OSError, SwitchBasicToolError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    return 0


def _collect_commands(cli_commands: list[str], command_file: str | None) -> list[str]:
    commands = [command for command in cli_commands if command.strip()]
    if command_file is None:
        return commands

    with open(command_file, encoding="utf-8") as handle:
        for raw_line in handle:
            command = raw_line.strip()
            if not command or command.startswith("#"):
                continue
            commands.append(command)
    return commands


def _get_default_commands(vendor_name: str) -> tuple[str, ...]:
    normalized_name = vendor_name.strip().lower().replace("-", "_")
    try:
        canonical_name = resolve_vendor_profile(vendor_name).name
    except Exception:
        canonical_name = normalized_name
    return DEFAULT_COMMANDS_BY_VENDOR.get(canonical_name, ())


def _resolve_password(
    *,
    provided_password: str | None,
    ask_password: bool,
    protocol: str,
    username: str | None,
    key_file: str | None,
    allow_agent: bool,
    look_for_keys: bool,
) -> str | None:
    if provided_password is not None:
        return provided_password
    if ask_password:
        return getpass.getpass("Password: ")
    if protocol == "telnet" and username:
        return getpass.getpass("Password: ")
    if protocol == "ssh" and username and not any((key_file, allow_agent, look_for_keys)):
        return getpass.getpass("Password: ")
    return None


def _run_command(client: NetworkDeviceClient, command: str, *, show_raw: bool) -> None:
    print(f"\n>>> {command}")
    result = client.send_command(command)
    print(result.raw_output if show_raw else result.output)


def _interactive_loop(client: NetworkDeviceClient, *, show_raw: bool) -> None:
    print("\nInteractive mode started. Type 'exit' or 'quit' to leave.")
    while True:
        try:
            command = input("switchbasictool> ").strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            break

        if not command:
            continue
        if command.lower() in {"exit", "quit"}:
            break
        _run_command(client, command, show_raw=show_raw)


def _print_profile(client: NetworkDeviceClient) -> None:
    profile = client.vendor_profile
    print("Resolved vendor profile:")
    print(f"  name: {profile.name}")
    print(f"  aliases: {', '.join(profile.aliases) if profile.aliases else '-'}")
    print(f"  prompt_pattern: {profile.prompt_pattern}")
    print(f"  init_commands: {client.session_init_commands or '-'}")


def _print_vendors() -> None:
    print("Built-in vendor profiles:")
    for profile in list_vendor_profiles():
        aliases = f" ({', '.join(profile.aliases)})" if profile.aliases else ""
        print(f"- {profile.name}{aliases}")


def _probe_ssh_banner(
    *,
    host: str,
    port: int,
    timeout: float,
    local_version: str | None,
) -> int:
    print(f"Probing SSH banner from {host}:{port} with timeout={timeout:.1f}s")

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            banner_text = local_version or "SSH-2.0-SwitchBasicTool_0.1"
            local_banner = f"{banner_text}\r\n".encode("ascii", errors="strict")
            sock.sendall(local_banner)
            print(f"Sent local banner: {local_banner.decode('ascii').strip()!r}")
            deadline = time.monotonic() + timeout
            chunks = bytearray()

            while time.monotonic() < deadline and len(chunks) < 512:
                try:
                    data = sock.recv(512)
                except socket.timeout:
                    break

                if not data:
                    break

                chunks.extend(data)
                if b"\n" in data:
                    break
    except OSError as exc:
        print(f"[ERROR] TCP connect failed: {exc}", file=sys.stderr)
        return 1

    if not chunks:
        print(
            "[ERROR] Connected to the port, but no SSH banner was received before timeout or disconnect.",
            file=sys.stderr,
        )
        return 1

    decoded = chunks.decode("utf-8", errors="replace").strip()
    print(f"Received: {decoded!r}")

    if decoded.startswith("SSH-"):
        print("Result: valid SSH banner detected.")
        return 0

    print(
        "Result: the port responded, but it did not start with 'SSH-'. "
        "This strongly suggests the service is not actually SSH.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
