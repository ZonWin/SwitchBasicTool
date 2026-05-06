"""SwitchBasicTool public package API."""

from .client import NetworkDeviceClient
from .exceptions import (
    AuthenticationError,
    CommandTimeoutError,
    ConnectionError,
    DependencyMissingError,
    PromptNotFoundError,
    SwitchBasicToolError,
    TransportClosedError,
    VendorProfileNotFoundError,
)
from .models import CommandResult, ConnectionConfig
from .vendors import (
    ARISTA_EOS_PROFILE,
    CISCO_IOS_PROFILE,
    GENERIC_PROFILE,
    H3C_PROFILE,
    HUAWEI_VRP_PROFILE,
    JUNIPER_JUNOS_PROFILE,
    ZTE_ZXR10_PROFILE,
    VendorProfile,
    get_vendor_profile,
    list_vendor_profiles,
    register_vendor_profile,
    resolve_vendor_profile,
)

__all__ = [
    "AuthenticationError",
    "ARISTA_EOS_PROFILE",
    "CISCO_IOS_PROFILE",
    "CommandResult",
    "CommandTimeoutError",
    "ConnectionConfig",
    "ConnectionError",
    "DependencyMissingError",
    "GENERIC_PROFILE",
    "H3C_PROFILE",
    "HUAWEI_VRP_PROFILE",
    "JUNIPER_JUNOS_PROFILE",
    "NetworkDeviceClient",
    "PromptNotFoundError",
    "SwitchBasicToolError",
    "TransportClosedError",
    "ZTE_ZXR10_PROFILE",
    "VendorProfile",
    "VendorProfileNotFoundError",
    "get_vendor_profile",
    "list_vendor_profiles",
    "register_vendor_profile",
    "resolve_vendor_profile",
]
