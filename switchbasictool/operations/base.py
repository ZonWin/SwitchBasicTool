"""High-level vendor operations built on top of the session client."""

from __future__ import annotations

from ..client import NetworkDeviceClient
from ..exceptions import OperationNotSupportedError
from ..models import CommandResult


class BaseOperations:
    """Common vendor-operations interface backed by ``NetworkDeviceClient``."""

    version_command: str | None = None
    hostname_command: str | None = None
    interface_brief_command: str | None = None
    ip_interface_brief_command: str | None = None
    vlan_summary_command: str | None = None
    mac_table_command: str | None = None
    arp_table_command: str | None = None
    lldp_neighbors_command: str | None = None
    running_config_command: str | None = None
    config_snippet_template: str | None = None
    port_config_template: str | None = None

    def __init__(self, client: NetworkDeviceClient) -> None:
        self.client = client

    @property
    def vendor_name(self) -> str:
        return self.client.vendor_profile.name

    def supported_operations(self) -> tuple[str, ...]:
        operations = [
            name
            for name, enabled in (
                ("get_version", self.version_command is not None),
                ("get_hostname", self.hostname_command is not None),
                ("get_interface_brief", self.interface_brief_command is not None),
                ("get_ip_interface_brief", self.ip_interface_brief_command is not None),
                ("get_vlan_summary", self.vlan_summary_command is not None),
                ("get_mac_table", self.mac_table_command is not None),
                ("get_arp_table", self.arp_table_command is not None),
                ("get_lldp_neighbors", self.lldp_neighbors_command is not None),
                ("get_running_config", self.running_config_command is not None),
                ("get_current_config_snippet", self.config_snippet_template is not None),
                ("get_port_config", self.port_config_template is not None),
            )
            if enabled
        ]
        return tuple(operations)

    def get_version(self, timeout: float | None = None) -> CommandResult:
        return self._run_named_command(self.version_command, "get_version", timeout=timeout)

    def get_hostname(self, timeout: float | None = None) -> CommandResult:
        return self._run_named_command(self.hostname_command, "get_hostname", timeout=timeout)

    def get_interface_brief(self, timeout: float | None = None) -> CommandResult:
        return self._run_named_command(
            self.interface_brief_command,
            "get_interface_brief",
            timeout=timeout,
        )

    def get_ip_interface_brief(self, timeout: float | None = None) -> CommandResult:
        return self._run_named_command(
            self.ip_interface_brief_command,
            "get_ip_interface_brief",
            timeout=timeout,
        )

    def get_vlan_summary(self, timeout: float | None = None) -> CommandResult:
        return self._run_named_command(
            self.vlan_summary_command,
            "get_vlan_summary",
            timeout=timeout,
        )

    def get_mac_table(self, timeout: float | None = None) -> CommandResult:
        return self._run_named_command(self.mac_table_command, "get_mac_table", timeout=timeout)

    def get_arp_table(self, timeout: float | None = None) -> CommandResult:
        return self._run_named_command(self.arp_table_command, "get_arp_table", timeout=timeout)

    def get_lldp_neighbors(self, timeout: float | None = None) -> CommandResult:
        return self._run_named_command(
            self.lldp_neighbors_command,
            "get_lldp_neighbors",
            timeout=timeout,
        )

    def get_running_config(self, timeout: float | None = None) -> CommandResult:
        return self._run_named_command(
            self.running_config_command,
            "get_running_config",
            timeout=timeout,
        )

    def get_current_config_snippet(
        self,
        keyword: str,
        timeout: float | None = None,
    ) -> CommandResult:
        return self._run_templated_command(
            self.config_snippet_template,
            "get_current_config_snippet",
            timeout=timeout,
            keyword=keyword,
        )

    def get_port_config(
        self,
        interface_name: str,
        timeout: float | None = None,
    ) -> CommandResult:
        return self._run_templated_command(
            self.port_config_template,
            "get_port_config",
            timeout=timeout,
            interface_name=interface_name,
        )

    def _run_named_command(
        self,
        command: str | None,
        operation_name: str,
        *,
        timeout: float | None = None,
    ) -> CommandResult:
        if command is None:
            raise OperationNotSupportedError(
                f"Operation '{operation_name}' is not supported for vendor '{self.vendor_name}'."
            )
        return self.client.send_command(command, timeout=timeout)

    def _run_templated_command(
        self,
        template: str | None,
        operation_name: str,
        *,
        timeout: float | None = None,
        **arguments: str,
    ) -> CommandResult:
        if template is None:
            raise OperationNotSupportedError(
                f"Operation '{operation_name}' is not supported for vendor '{self.vendor_name}'."
            )

        normalized_arguments = {
            name: self._normalize_argument(name, value)
            for name, value in arguments.items()
        }
        command = template.format(**normalized_arguments)
        return self.client.send_command(command, timeout=timeout)

    def _normalize_argument(self, argument_name: str, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{argument_name} cannot be empty")
        if "\r" in normalized or "\n" in normalized:
            raise ValueError(f"{argument_name} cannot contain line breaks")
        return normalized
