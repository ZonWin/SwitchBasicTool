"""H3C / Comware vendor operations."""

from __future__ import annotations

from .base import BaseOperations


class H3COperations(BaseOperations):
    """Common H3C Comware read-only operations."""

    version_command = "display version"
    hostname_command = "display current-configuration | include sysname"
    interface_brief_command = "display interface brief"
    vlan_summary_command = "display vlan"
    mac_table_command = "display mac-address"
    arp_table_command = "display arp"
    lldp_neighbors_command = "display lldp neighbor-information list"
    running_config_command = "display current-configuration"
    config_snippet_template = "display current-configuration | include {keyword}"
    port_config_template = "display current-configuration interface {interface_name}"
