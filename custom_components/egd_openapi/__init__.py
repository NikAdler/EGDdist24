"""EG.D OpenAPI integration."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change

from .api import EGDOpenAPIClient
from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_FETCH_HOUR,
    CONF_FETCH_MINUTE,
    DEFAULT_FETCH_HOUR,
    DOMAIN,
    PLATFORMS,
    UNSUB_SCHEDULE,
)
from .coordinator import EGDOpenAPICoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from config entry."""
    session = async_get_clientsession(hass)

    client = EGDOpenAPIClient(
        session=session,
        environment=entry.data["environment"],
        client_id=entry.data[CONF_CLIENT_ID],
        client_secret=entry.data[CONF_CLIENT_SECRET],
    )

    entry_payload: dict[str, Any] = dict(entry.data)
    entry_payload["options"] = dict(entry.options)

    coordinator = EGDOpenAPICoordinator(hass, client, entry_payload)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"coordinator": coordinator}

    _schedule_daily_refresh(hass, entry, coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


def _schedule_daily_refresh(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: EGDOpenAPICoordinator,
) -> None:
    hour = int(entry.options.get(CONF_FETCH_HOUR, DEFAULT_FETCH_HOUR))
    minute = int(entry.options.get(CONF_FETCH_MINUTE, entry.data.get(CONF_FETCH_MINUTE, 1)))

    async def _trigger_refresh(now: datetime) -> None:
        _LOGGER.debug("Scheduled EG.D refresh triggered at %s", now)
        await coordinator.async_request_refresh()

    unsub = async_track_time_change(hass, _trigger_refresh, hour=hour, minute=minute, second=0)
    hass.data[DOMAIN][entry.entry_id][UNSUB_SCHEDULE] = unsub


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        runtime = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if runtime and (unsub := runtime.get(UNSUB_SCHEDULE)):
            unsub()
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry after updates."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
