# Version: 1.0.7
"""API client for EG.D OpenAPI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import logging
from typing import Any

from aiohttp import ClientResponseError, ClientSession

from .const import (
    ENV_PRODUCTION,
    MEASUREMENT_C1,
    PROD_DATA_BASE,
    PROD_TOKEN_URL,
    TEST_DATA_BASE,
    TEST_TOKEN_URL,
    TOKEN_SCOPE,
)

_LOGGER = logging.getLogger(__name__)


class EGDAPIError(Exception):
    """Base API error."""


class EGDAPIAuthError(EGDAPIError):
    """Authentication error."""


@dataclass(slots=True)
class Profile:
    """Represents one profile option."""

    code: str
    name: str


class EGDOpenAPIClient:
    """Client for EG.D / Distribuce24 OpenAPI."""

    def __init__(
        self,
        session: ClientSession,
        environment: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        self._session = session
        self._environment = environment
        self._client_id = client_id
        self._client_secret = client_secret

        self._token: str | None = None
        self._token_day: str | None = None

    @property
    def _token_url(self) -> str:
        return PROD_TOKEN_URL if self._environment == ENV_PRODUCTION else TEST_TOKEN_URL

    @property
    def _data_base(self) -> str:
        return PROD_DATA_BASE if self._environment == ENV_PRODUCTION else TEST_DATA_BASE

    async def async_get_token(self, force_refresh: bool = False) -> str:
        """Return cached token for current day or fetch new one."""
        utc_today = datetime.now(tz=UTC).date().isoformat()
        if not force_refresh and self._token and self._token_day == utc_today:
            return self._token

        payload = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "scope": TOKEN_SCOPE,
        }
        async with self._session.post(self._token_url, json=payload) as resp:
            if resp.status in (401, 403):
                raise EGDAPIAuthError("Authentication failed. Verify client_id/client_secret.")
            if resp.status >= 400:
                body = await resp.text()
                raise EGDAPIError(f"Token endpoint error ({resp.status}): {body}")
            data = await resp.json()

        token = data.get("access_token")
        if not token:
            raise EGDAPIError("Token endpoint did not return access_token.")

        self._token = token
        self._token_day = utc_today
        return token

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        token = await self.async_get_token()
        url = f"{self._data_base}/{path.lstrip('/')}"

        headers = {"Authorization": f"Bearer {token}"}

        try:
            async with self._session.request(method, url, params=params, headers=headers) as resp:
                if resp.status == 401:
                    token = await self.async_get_token(force_refresh=True)
                    headers["Authorization"] = f"Bearer {token}"
                    async with self._session.request(
                        method,
                        url,
                        params=params,
                        headers=headers,
                    ) as retry_resp:
                        retry_resp.raise_for_status()
                        return await retry_resp.json()

                resp.raise_for_status()
                return await resp.json()
        except ClientResponseError as err:
            if err.status in (401, 403):
                raise EGDAPIAuthError("Unauthorized request to Distribuce24 API.") from err
            raise EGDAPIError(f"Distribuce24 API request failed: {err.status}") from err
        except EGDAPIError:
            raise
        except Exception as err:  # noqa: BLE001
            raise EGDAPIError("Unexpected API error.") from err

    async def async_get_profiles(self, measurement_type: str) -> list[Profile]:
        """Fetch available profiles for measurement type."""
        endpoint = "c/profily" if measurement_type == MEASUREMENT_C1 else "profily"
        raw = await self._request("GET", endpoint)

        items: list[dict[str, Any]]
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, dict):
            for key in ("items", "data", "profily", "profiles"):
                val = raw.get(key)
                if isinstance(val, list):
                    items = val
                    break
            else:
                items = []
        else:
            items = []

        profiles: list[Profile] = []
        for item in items:
            code = str(item.get("kod") or item.get("code") or item.get("profil") or "").strip()
            name = str(item.get("nazev") or item.get("name") or code).strip()
            if code:
                profiles.append(Profile(code=code, name=name))

        if not profiles:
            raise EGDAPIError("No profiles returned by API.")
        return profiles

    async def async_get_consumption(
        self,
        *,
        ean: str,
        measurement_type: str,
        profile: str,
        time_from: str,
        time_to: str,
        zdroj_dat: str | None,
    ) -> list[dict[str, Any]]:
        """Fetch consumption rows for one profile within interval."""
        if measurement_type == MEASUREMENT_C1:
            params: dict[str, Any] = {
                "ean": ean,
                "profile": profile,
                "from": time_from,
                "to": time_to,
                "zdrojDat": zdroj_dat,
            }
            raw = await self._request("GET", "c/spotreby", params=params)
            return self._extract_rows(raw)

        page_start = 0
        page_size = 3000
        all_rows: list[dict[str, Any]] = []

        while True:
            params = {
                "ean": ean,
                "profile": profile,
                "from": time_from,
                "to": time_to,
                "PageStart": page_start,
                "PageSize": page_size,
            }
            raw = await self._request("GET", "spotreby", params=params)
            rows = self._extract_rows(raw)
            if not rows:
                break

            all_rows.extend(rows)
            if len(rows) < page_size:
                break
            page_start += len(rows)

        return all_rows

    @staticmethod
    def _extract_rows(raw: Any) -> list[dict[str, Any]]:
        if isinstance(raw, list):
            return [r for r in raw if isinstance(r, dict)]
        if isinstance(raw, dict):
            for key in ("items", "data", "spotreby", "rows", "result"):
                val = raw.get(key)
                if isinstance(val, list):
                    return [r for r in val if isinstance(r, dict)]
        return []
