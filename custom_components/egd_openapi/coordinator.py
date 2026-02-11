"""DataUpdateCoordinator for EG.D OpenAPI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import EGDAPIAuthError, EGDAPIError, EGDOpenAPIClient
from .const import (
    ATTR_INTERVAL_MINUTES,
    CONF_DAYS_BACK_FETCH,
    CONF_DAYS_TO_KEEP_SERIES,
    CONF_EAN,
    CONF_INCLUDE_SERIES_ATTRIBUTE,
    CONF_MEASUREMENT_TYPE,
    CONF_PROFILE_MAP,
    CONF_SELECTED_PROFILES,
    CONF_ZDROJ_DAT,
    DEFAULT_DAYS_BACK_FETCH,
    DEFAULT_DAYS_TO_KEEP_SERIES,
    DEFAULT_INCLUDE_SERIES_ATTRIBUTE,
    DOMAIN,
    MEASUREMENT_C1,
    POINTS_PER_DAY,
    VALID_STATUS_AB,
    VALID_STATUS_C1,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ProfileDayData:
    """Computed data for one profile and one day."""

    total_kwh: float
    window_start: datetime
    window_end: datetime
    valid_points: int
    invalid_points: int
    series_points: list[list[int | float | None]]


@dataclass(slots=True)
class CoordinatorPayload:
    """Coordinator payload."""

    by_profile: dict[str, ProfileDayData]
    last_success_utc: datetime | None


class EGDOpenAPICoordinator(DataUpdateCoordinator[CoordinatorPayload]):
    """Coordinator fetching once per day and on manual refresh."""

    def __init__(self, hass: HomeAssistant, client: EGDOpenAPIClient, entry_data: dict[str, Any]) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,
        )
        self.client = client
        self.entry_data = entry_data
        self.series_history: dict[str, list[list[int | float | None]]] = {}

    async def _async_update_data(self) -> CoordinatorPayload:
        try:
            return await self._async_fetch()
        except EGDAPIAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except EGDAPIError as err:
            raise UpdateFailed(f"API error: {err}") from err
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _async_fetch(self) -> CoordinatorPayload:
        config = self.entry_data
        options = self.entry_data.get("options", {})

        ean = config[CONF_EAN]
        measurement_type = config[CONF_MEASUREMENT_TYPE]
        zdroj_dat = config.get(CONF_ZDROJ_DAT)
        selected_profiles = options.get(CONF_SELECTED_PROFILES, config.get(CONF_SELECTED_PROFILES, []))
        days_back = int(options.get(CONF_DAYS_BACK_FETCH, DEFAULT_DAYS_BACK_FETCH))

        if not selected_profiles:
            raise UpdateFailed("No profiles are selected.")

        local_tz = dt_util.get_time_zone("Europe/Prague")
        now_local = dt_util.now().astimezone(local_tz)

        yesterday = now_local.date() - timedelta(days=1)
        day_list = [yesterday - timedelta(days=offset) for offset in reversed(range(days_back))]

        profile_latest: dict[str, ProfileDayData] = {}

        for day in day_list:
            start_local = datetime.combine(day, time.min, tzinfo=local_tz)
            end_local = datetime.combine(day, time.max, tzinfo=local_tz)

            if measurement_type == MEASUREMENT_C1:
                from_param = start_local.isoformat()
                to_param = end_local.isoformat()
            else:
                from_param = start_local.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
                to_param = end_local.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

            for profile_code in selected_profiles:
                rows = await self.client.async_get_consumption(
                    ean=ean,
                    measurement_type=measurement_type,
                    profile=profile_code,
                    time_from=from_param,
                    time_to=to_param,
                    zdroj_dat=zdroj_dat,
                )

                computed = self._compute_profile_day(
                    rows=rows,
                    measurement_type=measurement_type,
                    window_start=start_local.astimezone(UTC),
                    window_end=end_local.astimezone(UTC),
                )

                self._append_series(profile_code, computed.series_points)
                if day == yesterday:
                    profile_latest[profile_code] = computed

        return CoordinatorPayload(
            by_profile=profile_latest,
            last_success_utc=datetime.now(tz=UTC),
        )

    def _append_series(self, profile_code: str, points: list[list[int | float | None]]) -> None:
        keep_days = int(
            self.entry_data.get("options", {}).get(
                CONF_DAYS_TO_KEEP_SERIES,
                DEFAULT_DAYS_TO_KEEP_SERIES,
            )
        )
        keep_points = max(1, keep_days) * POINTS_PER_DAY

        hist = self.series_history.setdefault(profile_code, [])
        hist.extend(points)
        if len(hist) > keep_points:
            self.series_history[profile_code] = hist[-keep_points:]

    def _compute_profile_day(
        self,
        *,
        rows: list[dict[str, Any]],
        measurement_type: str,
        window_start: datetime,
        window_end: datetime,
    ) -> ProfileDayData:
        valid_status = VALID_STATUS_C1 if measurement_type == MEASUREMENT_C1 else VALID_STATUS_AB

        valid_points = 0
        invalid_points = 0
        total_kwh = Decimal("0")
        series_points: list[list[int | float | None]] = []

        for row in rows:
            ts = self._parse_timestamp(row)
            if ts is None:
                continue

            value = self._parse_decimal(row.get("hodnota") or row.get("value") or row.get("spotreba"))
            status = str(row.get("status") or row.get("stav") or "").strip()
            unit = str(row.get("jednotka") or row.get("unit") or "kWh").strip()

            timestamp_ms = int(ts.astimezone(UTC).timestamp() * 1000)

            if status != valid_status or value is None:
                invalid_points += 1
                series_points.append([timestamp_ms, None])
                continue

            interval_kwh = self._normalize_to_kwh(value, unit)
            valid_points += 1
            total_kwh += interval_kwh
            series_points.append([timestamp_ms, float(interval_kwh)])

        return ProfileDayData(
            total_kwh=float(total_kwh),
            window_start=window_start,
            window_end=window_end,
            valid_points=valid_points,
            invalid_points=invalid_points,
            series_points=series_points,
        )

    @staticmethod
    def _parse_timestamp(row: dict[str, Any]) -> datetime | None:
        raw = row.get("cas") or row.get("timestamp") or row.get("datum") or row.get("time")
        if not raw:
            return None

        if isinstance(raw, (int, float)):
            return datetime.fromtimestamp(float(raw), tz=UTC)

        if not isinstance(raw, str):
            return None

        raw_norm = raw.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(raw_norm)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    @staticmethod
    def _parse_decimal(value: Any) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value).replace(",", "."))
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _normalize_to_kwh(value: Decimal, unit: str) -> Decimal:
        unit_norm = unit.lower()
        if unit_norm == "wh":
            return value / Decimal("1000")
        if unit_norm == "kw":
            return value * Decimal(str(ATTR_INTERVAL_MINUTES / 60))
        return value

    def include_series_attribute(self) -> bool:
        return bool(
            self.entry_data.get("options", {}).get(
                CONF_INCLUDE_SERIES_ATTRIBUTE,
                DEFAULT_INCLUDE_SERIES_ATTRIBUTE,
            )
        )

    def profile_name(self, profile_code: str) -> str:
        profile_map = self.entry_data.get(CONF_PROFILE_MAP, {})
        return str(profile_map.get(profile_code, profile_code))

    def get_profile_data(self, profile_code: str) -> ProfileDayData | None:
        if not self.data:
            return None
        return self.data.by_profile.get(profile_code)

    def get_series(self, profile_code: str) -> list[list[int | float | None]]:
        return self.series_history.get(profile_code, [])
