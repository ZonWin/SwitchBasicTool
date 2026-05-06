"""Vendor profile registry and built-in vendor definitions."""

from __future__ import annotations

from dataclasses import dataclass

from .exceptions import VendorProfileNotFoundError


def _normalize_vendor_name(name: str) -> str:
    return name.strip().lower().replace("-", "_").replace(" ", "_")


@dataclass(frozen=True, slots=True)
class VendorProfile:
    """Defaults that describe a vendor's CLI behavior."""

    name: str
    aliases: tuple[str, ...] = ()
    prompt_pattern: str = (
        r"(?m)(?:<[^<>\r\n]+>|\[[^\[\]\r\n]+\]|[A-Za-z0-9._()@:/-]+(?:\([^)]+\))?[>#])\s*$"
    )
    more_patterns: tuple[str, ...] = (
        r"--More--",
        r"----\s+More\s+----",
        r"Press any key to continue",
    )
    username_prompt_pattern: str = r"(?im)(?:username|user\s+name|login)\s*[:>]\s*$"
    password_prompt_pattern: str = r"(?im)password\s*[:>]\s*$"
    session_init_commands: tuple[str, ...] = ()

    def all_names(self) -> tuple[str, ...]:
        return (self.name, *self.aliases)


_PROFILE_REGISTRY: dict[str, VendorProfile] = {}
_CANONICAL_PROFILES: dict[str, VendorProfile] = {}


def register_vendor_profile(profile: VendorProfile, *, replace: bool = True) -> VendorProfile:
    """Register a vendor profile and all of its aliases."""

    normalized_names = {_normalize_vendor_name(name) for name in profile.all_names()}
    if not replace:
        duplicated = normalized_names.intersection(_PROFILE_REGISTRY)
        if duplicated:
            joined = ", ".join(sorted(duplicated))
            raise ValueError(f"Vendor profile names already registered: {joined}")

    for name in normalized_names:
        _PROFILE_REGISTRY[name] = profile

    _CANONICAL_PROFILES[_normalize_vendor_name(profile.name)] = profile
    return profile


def get_vendor_profile(name: str) -> VendorProfile:
    """Return a registered vendor profile by name or alias."""

    normalized_name = _normalize_vendor_name(name)
    try:
        return _PROFILE_REGISTRY[normalized_name]
    except KeyError as exc:
        raise VendorProfileNotFoundError(
            f"Vendor profile '{name}' was not found. Register it first or use 'generic'."
        ) from exc


def resolve_vendor_profile(
    vendor: str | None = None,
    vendor_profile: VendorProfile | None = None,
) -> VendorProfile:
    """Resolve either an explicit profile or a registered vendor name."""

    if vendor_profile is not None:
        return vendor_profile
    if vendor is None or not vendor.strip():
        return get_vendor_profile("generic")
    return get_vendor_profile(vendor)


def list_vendor_profiles() -> tuple[VendorProfile, ...]:
    """Return canonical registered profiles."""

    return tuple(_CANONICAL_PROFILES[name] for name in sorted(_CANONICAL_PROFILES))


GENERIC_PROFILE = register_vendor_profile(
    VendorProfile(
        name="generic",
    )
)

HUAWEI_VRP_PROFILE = register_vendor_profile(
    VendorProfile(
        name="huawei",
        aliases=("vrp", "huawei_vrp", "hw"),
        prompt_pattern=r"(?m)(?:<[-A-Za-z0-9_./()]+>|\[[^\[\]\r\n]+\])\s*$",
        more_patterns=(
            r"--More--",
            r"(?im)^\s*-+\s*More\s*-+\s*$",
            r"(?im)^\s*-+\s*More\s*\(.*?\)\s*-+\s*$",
            r"(?im)press\s+(?:any\s+key|space)\s+to\s+continue",
        ),
        username_prompt_pattern=r"(?im)(?:username|user-name|login)\s*[:>]\s*$",
        password_prompt_pattern=r"(?im)password\s*[:>]\s*$",
        session_init_commands=("screen-length 0 temporary",),
    )
)

H3C_PROFILE = register_vendor_profile(
    VendorProfile(
        name="h3c",
        aliases=("comware", "h3c_comware"),
        prompt_pattern=r"(?m)(?:<[-A-Za-z0-9_./()]+>|\[[^\[\]\r\n]+\])\s*$",
        more_patterns=(
            r"--More--",
            r"(?im)^\s*-+\s*More\s*-+\s*$",
            r"(?im)^\s*-+\s*More\s*\(.*?\)\s*-+\s*$",
            r"(?im)press\s+(?:any\s+key|space)\s+to\s+continue",
        ),
        username_prompt_pattern=r"(?im)(?:username|user-name|login)\s*[:>]\s*$",
        password_prompt_pattern=r"(?im)password\s*[:>]\s*$",
        session_init_commands=("screen-length disable",),
    )
)

CISCO_IOS_PROFILE = register_vendor_profile(
    VendorProfile(
        name="cisco_ios",
        aliases=("cisco", "ios"),
        prompt_pattern=r"(?m)[A-Za-z0-9._()/-]+(?:\([^)]+\))?[>#]\s*$",
        session_init_commands=("terminal length 0",),
    )
)

JUNIPER_JUNOS_PROFILE = register_vendor_profile(
    VendorProfile(
        name="juniper",
        aliases=("junos",),
        prompt_pattern=r"(?m)[A-Za-z0-9._@/-]+[>%#]\s*$",
        session_init_commands=("set cli screen-length 0", "set cli screen-width 0"),
    )
)

ARISTA_EOS_PROFILE = register_vendor_profile(
    VendorProfile(
        name="arista_eos",
        aliases=("arista", "eos"),
        prompt_pattern=r"(?m)[A-Za-z0-9._()/-]+(?:\([^)]+\))?[>#]\s*$",
        session_init_commands=("terminal length 0",),
    )
)

ZTE_ZXR10_PROFILE = register_vendor_profile(
    VendorProfile(
        name="zte",
        aliases=("zxr10", "zte_zxr10", "8900e"),
        prompt_pattern=r"(?m)[-A-Za-z0-9_.]+(?:\([^)]+\))?[>#]\s*$",
        more_patterns=(
            r"--More--",
            r"(?im)^\s*-+\s*More\s*-+\s*$",
            r"(?im)press\s+(?:any\s+key|space)\s+to\s+continue",
        ),
        username_prompt_pattern=r"(?im)(?:username|user-name|login)\s*[:>]\s*$",
        password_prompt_pattern=r"(?im)password\s*[:>]\s*$",
        session_init_commands=("no terminal length",),
    )
)
