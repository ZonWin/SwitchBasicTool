"""Cisco IOS vendor operations."""

from __future__ import annotations

from .base import BaseOperations


class CiscoIOSOperations(BaseOperations):
    """Common Cisco IOS read-only operations."""

    version_command = "show version"
    hostname_command = "show running-config | include ^hostname"
    interface_brief_command = "show interfaces status"
    ip_interface_brief_command = "show ip interface brief"
    vlan_summary_command = "show vlan brief"
    mac_table_command = "show mac address-table"
    arp_table_command = "show arp"
    lldp_neighbors_command = "show lldp neighbors"
    running_config_command = "show running-config"
    config_snippet_template = "show running-config | include {keyword}"
    port_config_template = "show running-config interface {interface_name}"
