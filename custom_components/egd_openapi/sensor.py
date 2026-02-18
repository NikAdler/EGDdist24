"""Sensors for EG.D OpenAPI."""

from __future__ import annotations

from datetime import UTC
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_EAN, CONF_SELECTED_PROFILES, DOMAIN
from .coordinator import EGDOpenAPICoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator: EGDOpenAPICoordinator = runtime["coordinator"]

    selected_profiles = entry.options.get(CONF_SELECTED_PROFILES, entry.data.get(CONF_SELECTED_PROFILES, []))
    ean = entry.data[CONF_EAN]

    entities: list[SensorEntity] = [EGDLastUpdateSensor(coordinator, ean)]
    for profile in selected_profiles:
        entities.append(EGDDailyEnergySensor(coordinator, ean, profile))
        entities.append(EGDSeriesSensor(coordinator, ean, profile))

    async_add_entities(entities)


class EGDBaseSensor(CoordinatorEntity[EGDOpenAPICoordinator], SensorEntity):
    """Base sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EGDOpenAPICoordinator, ean: str, profile_code: str, kind: str) -> None:
        super().__init__(coordinator)
        self._ean = ean
        self._profile_code = profile_code
        self._kind = kind
        self._attr_unique_id = f"{ean}_{profile_code}_{kind}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._ean)},
            "name": f"EG.D {self._ean}",
            "manufacturer": "EG.D / Distribuce24",
            "model": "OpenAPI",
        }

    def _profile_label(self) -> str:
        """Return user-friendly profile label."""
        profile_name = self.coordinator.profile_name(self._profile_code)
        code = self._profile_code.upper()

        if code.startswith("IS"):
            direction = "Export to grid"
        elif code.startswith("IC"):
            direction = "Import consumption"
        else:
            direction = "Measured energy"

        if "Q" in code:
            granularity = "quarter-hour"
        elif "H" in code:
            granularity = "hourly"
        elif "C" in code:
            granularity = "consumption curve"
        else:
            granularity = "profile"

        if profile_name and profile_name != self._profile_code:
            return f"{direction} {granularity} ({profile_name}, {self._profile_code})"
        return f"{direction} {granularity} ({self._profile_code})"


class EGDDailyEnergySensor(EGDBaseSensor):
    """Yesterday daily energy sensor."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    def __init__(self, coordinator: EGDOpenAPICoordinator, ean: str, profile_code: str) -> None:
        super().__init__(coordinator, ean, profile_code, "daily_energy")
        self._attr_name = f"{self._profile_label()} - Yesterday energy"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.get_profile_data(self._profile_code)
        if not data:
            return None
        return round(data.total_kwh, 6)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.get_profile_data(self._profile_code)
        if not data:
            return {"ean": self._ean, "profile_code": self._profile_code}

        return {
            "ean": self._ean,
            "profile_code": self._profile_code,
            "profile_name": self.coordinator.profile_name(self._profile_code),
            "window_start": data.window_start.isoformat(),
            "window_end": data.window_end.isoformat(),
            "valid_points": data.valid_points,
            "invalid_points": data.invalid_points,
        }


class EGDSeriesSensor(EGDBaseSensor):
    """Series sensor with interval points in attributes."""

    def __init__(self, coordinator: EGDOpenAPICoordinator, ean: str, profile_code: str) -> None:
        super().__init__(coordinator, ean, profile_code, "series")
        self._attr_name = f"{self._profile_label()} - 15-minute series"

    @property
    def native_value(self) -> str | float | None:
        data = self.coordinator.get_profile_data(self._profile_code)
        if not data:
            return None
        return data.window_start.astimezone(UTC).date().isoformat()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "ean": self._ean,
            "profile_code": self._profile_code,
            "profile_name": self.coordinator.profile_name(self._profile_code),
        }

        if self.coordinator.include_series_attribute():
            attrs["series"] = self.coordinator.get_series(self._profile_code)
            attrs["unit"] = UnitOfEnergy.KILO_WATT_HOUR
            attrs["interval_minutes"] = 15

        return attrs


class EGDLastUpdateSensor(CoordinatorEntity[EGDOpenAPICoordinator], SensorEntity):
    """Last successful update timestamp sensor."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_has_entity_name = True

    def __init__(self, coordinator: EGDOpenAPICoordinator, ean: str) -> None:
        super().__init__(coordinator)
        self._ean = ean
        self._attr_name = "Last successful update"
        self._attr_unique_id = f"{ean}_last_update"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._ean)},
            "name": f"EG.D {self._ean}",
            "manufacturer": "EG.D / Distribuce24",
            "model": "OpenAPI",
        }

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self.coordinator.data.last_success_utc
