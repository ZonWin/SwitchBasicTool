"""Vendor operations registry and factory."""

from __future__ import annotations

from ..client import NetworkDeviceClient
from .base import BaseOperations


def _normalize_vendor_name(name: str) -> str:
    return name.strip().lower().replace("-", "_").replace(" ", "_")


_OPERATIONS_REGISTRY: dict[str, type[BaseOperations]] = {}


def register_operations_class(
    vendor_name: str,
    operations_class: type[BaseOperations],
    *,
    replace: bool = True,
) -> type[BaseOperations]:
    """Register an operations class for one vendor name or alias."""

    normalized_name = _normalize_vendor_name(vendor_name)
    if not normalized_name:
        raise ValueError("vendor_name cannot be empty")
    if not replace and normalized_name in _OPERATIONS_REGISTRY:
        raise ValueError(f"Operations class already registered for vendor '{vendor_name}'.")
    _OPERATIONS_REGISTRY[normalized_name] = operations_class
    return operations_class


def get_operations_class(vendor_name: str) -> type[BaseOperations]:
    """Return the registered operations class for a vendor or alias."""

    normalized_name = _normalize_vendor_name(vendor_name)
    return _OPERATIONS_REGISTRY.get(normalized_name, BaseOperations)


def get_operations(client: NetworkDeviceClient) -> BaseOperations:
    """Build a vendor operations instance from an existing client."""

    operations_class = get_operations_class(client.vendor_profile.name)
    return operations_class(client)


from .aruba_aoscx import ArubaAOSCXOperations  # noqa: E402
from .cisco_ios import CiscoIOSOperations  # noqa: E402
from .h3c import H3COperations  # noqa: E402
from .huawei import HuaweiOperations  # noqa: E402
from .zte import ZTEOperations  # noqa: E402


register_operations_class("generic", BaseOperations)
register_operations_class("cisco_ios", CiscoIOSOperations)
register_operations_class("cisco", CiscoIOSOperations)
register_operations_class("ios", CiscoIOSOperations)
register_operations_class("huawei", HuaweiOperations)
register_operations_class("vrp", HuaweiOperations)
register_operations_class("huawei_vrp", HuaweiOperations)
register_operations_class("hw", HuaweiOperations)
register_operations_class("h3c", H3COperations)
register_operations_class("comware", H3COperations)
register_operations_class("h3c_comware", H3COperations)
register_operations_class("aruba_aoscx", ArubaAOSCXOperations)
register_operations_class("aruba", ArubaAOSCXOperations)
register_operations_class("aruba_cx", ArubaAOSCXOperations)
register_operations_class("aoscx", ArubaAOSCXOperations)
register_operations_class("hpe_aruba", ArubaAOSCXOperations)
register_operations_class("hp_aruba", ArubaAOSCXOperations)
register_operations_class("zte", ZTEOperations)
register_operations_class("zxr10", ZTEOperations)
register_operations_class("zte_zxr10", ZTEOperations)
register_operations_class("8900e", ZTEOperations)
