from __future__ import annotations

import unittest
from types import SimpleNamespace

from switchbasictool import CommandResult, OperationNotSupportedError, get_operations
from switchbasictool.operations import BaseOperations, H3COperations, HuaweiOperations, get_operations_class


class FakeClient:
    def __init__(self, vendor_name: str) -> None:
        self.vendor_profile = SimpleNamespace(name=vendor_name)
        self.calls: list[tuple[str, float | None]] = []

    def send_command(self, command: str, timeout: float | None = None) -> CommandResult:
        self.calls.append((command, timeout))
        return CommandResult(
            command=command,
            raw_output=command,
            output=command,
            duration=0.0,
            timed_out=False,
        )


class OperationsFactoryTests(unittest.TestCase):
    def test_huawei_alias_resolves_to_huawei_operations(self) -> None:
        self.assertIs(get_operations_class("vrp"), HuaweiOperations)
        self.assertIs(get_operations_class("hw"), HuaweiOperations)

    def test_h3c_alias_resolves_to_h3c_operations(self) -> None:
        self.assertIs(get_operations_class("comware"), H3COperations)
        self.assertIs(get_operations_class("h3c_comware"), H3COperations)

    def test_unknown_vendor_falls_back_to_base_operations(self) -> None:
        self.assertIs(get_operations_class("unknown_vendor"), BaseOperations)

    def test_factory_uses_client_vendor_profile_name(self) -> None:
        client = FakeClient("huawei")
        operations = get_operations(client)
        self.assertIsInstance(operations, HuaweiOperations)


class HuaweiOperationsTests(unittest.TestCase):
    def test_huawei_common_commands(self) -> None:
        client = FakeClient("huawei")
        operations = HuaweiOperations(client)

        operations.get_version()
        operations.get_hostname(timeout=3.0)
        operations.get_interface_brief()
        operations.get_vlan_summary()
        operations.get_mac_table()
        operations.get_arp_table()
        operations.get_lldp_neighbors()
        operations.get_running_config()
        operations.get_current_config_snippet("sysname")
        operations.get_port_config("GigabitEthernet0/0/1")

        self.assertEqual(
            client.calls,
            [
                ("display version", None),
                ("display current-configuration | include sysname", 3.0),
                ("display interface brief", None),
                ("display vlan summary", None),
                ("display mac-address", None),
                ("display arp", None),
                ("display lldp neighbor brief", None),
                ("display current-configuration", None),
                ("display current-configuration | include sysname", None),
                ("display current-configuration interface GigabitEthernet0/0/1", None),
            ],
        )

    def test_supported_operations_lists_the_enabled_huawei_methods(self) -> None:
        operations = HuaweiOperations(FakeClient("huawei"))
        self.assertEqual(
            operations.supported_operations(),
            (
                "get_version",
                "get_hostname",
                "get_interface_brief",
                "get_vlan_summary",
                "get_mac_table",
                "get_arp_table",
                "get_lldp_neighbors",
                "get_running_config",
                "get_current_config_snippet",
                "get_port_config",
            ),
        )


class H3COperationsTests(unittest.TestCase):
    def test_h3c_vendor_specific_commands(self) -> None:
        client = FakeClient("h3c")
        operations = H3COperations(client)

        operations.get_vlan_summary()
        operations.get_lldp_neighbors(timeout=5.0)
        operations.get_port_config("Ten-GigabitEthernet1/0/1")

        self.assertEqual(
            client.calls,
            [
                ("display vlan", None),
                ("display lldp neighbor-information list", 5.0),
                ("display current-configuration interface Ten-GigabitEthernet1/0/1", None),
            ],
        )


class BaseOperationsTests(unittest.TestCase):
    def test_unsupported_operation_raises_clear_error(self) -> None:
        operations = BaseOperations(FakeClient("generic"))
        with self.assertRaises(OperationNotSupportedError):
            operations.get_version()

    def test_templated_commands_strip_arguments(self) -> None:
        client = FakeClient("huawei")
        operations = HuaweiOperations(client)

        operations.get_current_config_snippet("  sysname  ")
        operations.get_port_config("  GigabitEthernet1/0/1  ")

        self.assertEqual(
            client.calls,
            [
                ("display current-configuration | include sysname", None),
                ("display current-configuration interface GigabitEthernet1/0/1", None),
            ],
        )

    def test_templated_commands_reject_line_breaks(self) -> None:
        operations = HuaweiOperations(FakeClient("huawei"))
        with self.assertRaises(ValueError):
            operations.get_current_config_snippet("sysname\nospf")


if __name__ == "__main__":
    unittest.main()
