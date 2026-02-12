"""EG.D OpenAPI integration."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util import dt as dt_util

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
    """Schedule refresh at a fixed local time in Europe/Prague and re-schedule daily."""
    hour = int(entry.options.get(CONF_FETCH_HOUR, DEFAULT_FETCH_HOUR))
    minute = int(entry.options.get(CONF_FETCH_MINUTE, entry.data.get(CONF_FETCH_MINUTE, 1)))
    prague_tz = dt_util.get_time_zone("Europe/Prague")

    def _next_run(now_local: datetime) -> datetime:
        next_local = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_local <= now_local:
            next_local = next_local + timedelta(days=1)
        return next_local.astimezone(dt_util.UTC)

    async def _schedule_next(now_utc: datetime | None = None) -> None:
        local_now = (now_utc or dt_util.now()).astimezone(prague_tz)
        run_at_utc = _next_run(local_now)
        _LOGGER.debug(
            "Scheduling EG.D next refresh for %s local (%s UTC)",
            run_at_utc.astimezone(prague_tz).isoformat(),
            run_at_utc.isoformat(),
        )

        async def _run_scheduled(_: datetime) -> None:
            _LOGGER.debug("Scheduled EG.D refresh triggered")
            await coordinator.async_request_refresh()
            await _schedule_next()

        unsub = async_track_point_in_time(hass, _run_scheduled, run_at_utc)
        hass.data[DOMAIN][entry.entry_id][UNSUB_SCHEDULE] = unsub

    hass.async_create_task(_schedule_next())


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
