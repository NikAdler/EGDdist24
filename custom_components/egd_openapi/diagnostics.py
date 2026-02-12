"""Diagnostics for EG.D OpenAPI."""
# Version: 1.0.5

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, DOMAIN

REDACT_KEYS = {CONF_CLIENT_ID, CONF_CLIENT_SECRET}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = dict(config_entry.data)
    for key in REDACT_KEYS:
        if key in data:
            data[key] = "***REDACTED***"

    runtime = hass.data.get(DOMAIN, {}).get(config_entry.entry_id, {})
    coordinator: DataUpdateCoordinator | None = runtime.get("coordinator")

    return {
        "entry": data,
        "options": dict(config_entry.options),
        "coordinator_last_update_success": coordinator.last_update_success if coordinator else None,
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    device: DeviceEntry,
) -> dict[str, Any]:
    """Return device diagnostics."""
    return {
        "device": {
            "id": device.id,
            "name": device.name,
            "model": device.model,
            "manufacturer": device.manufacturer,
        },
        "entry_id": config_entry.entry_id,
    }
