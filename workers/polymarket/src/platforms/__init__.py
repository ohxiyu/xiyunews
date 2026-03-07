"""
Platform registry - provides platform list for API.

SSOT: All data comes from Polyrouter, not from individual adapters.
This module only provides platform metadata for the /v1/platforms endpoint.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class PlatformInfo:
    """Platform metadata for API response."""
    id: str
    name: str
    enabled: bool
    description: str = ""


# Platform List - Polymarket only
PLATFORMS = [
    PlatformInfo(
        id="polymarket",
        name="Polymarket",
        enabled=True,
        description="The largest prediction market platform",
    ),
]


def list_platforms(include_disabled: bool = False) -> List[PlatformInfo]:
    """
    List all available platforms.

    Args:
        include_disabled: If True, include disabled platforms

    Returns:
        List of PlatformInfo objects
    """
    if include_disabled:
        return PLATFORMS
    return [p for p in PLATFORMS if p.enabled]


def get_registry():
    """Get a simple registry-like object for backward compatibility."""
    class SimpleRegistry:
        def list_platforms(self, include_disabled=False):
            return list_platforms(include_disabled)

        def get_platform_info(self, platform_id):
            for p in PLATFORMS:
                if p.id == platform_id:
                    return p
            return None

    return SimpleRegistry()


__all__ = ['PlatformInfo', 'list_platforms', 'get_registry', 'PLATFORMS']
