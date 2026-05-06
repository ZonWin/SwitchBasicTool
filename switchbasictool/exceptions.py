"""Custom exceptions used by SwitchBasicTool."""


class SwitchBasicToolError(Exception):
    """Base exception for this package."""


class ConnectionError(SwitchBasicToolError):
    """Raised when a network session cannot be established."""


class AuthenticationError(ConnectionError):
    """Raised when remote authentication fails."""


class DependencyMissingError(SwitchBasicToolError):
    """Raised when an optional runtime dependency is unavailable."""


class CommandTimeoutError(SwitchBasicToolError):
    """Raised when command output cannot be collected before timeout."""


class PromptNotFoundError(CommandTimeoutError):
    """Raised when a device prompt is not observed in time."""


class TransportClosedError(SwitchBasicToolError):
    """Raised when operations are attempted on a closed transport."""


class VendorProfileNotFoundError(SwitchBasicToolError):
    """Raised when a vendor profile cannot be resolved."""


class OperationNotSupportedError(SwitchBasicToolError):
    """Raised when a vendor operation is unavailable for the current device."""
