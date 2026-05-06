"""ZTE / ZXR10 vendor operations."""

from __future__ import annotations

from .base import BaseOperations


class ZTEOperations(BaseOperations):
    """Common ZTE ZXR10 read-only operations.

    The command choices in this class are aligned with the ZXR10 8900E
    V3.02.01 user manual package provided alongside this repository work.
    """

    version_command = "show version"
    # The manual documents both the `hostname` command and `show running-config | include ...`.
    hostname_command = "show running-config | include hostname"
    interface_brief_command = "show interface brief"
    ip_interface_brief_command = "show ip interface brief"
    vlan_summary_command = "show vlan"
    mac_table_command = "show mac table"
    arp_table_command = "show arp"
    lldp_neighbors_command = "show lldp neighbor"
    running_config_command = "show running-config"
    config_snippet_template = "show running-config | include {keyword}"
