# Version: 1.0.7
"""Config flow for EG.D OpenAPI."""

from __future__ import annotations

from collections.abc import Mapping
from random import randint
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EGDAPIAuthError, EGDAPIError, EGDOpenAPIClient, Profile
from .const import (
    CONF_DAYS_BACK_FETCH,
    CONF_DAYS_TO_KEEP_SERIES,
    CONF_EAN,
    CONF_ENVIRONMENT,
    CONF_FETCH_HOUR,
    CONF_FETCH_MINUTE,
    CONF_INCLUDE_SERIES_ATTRIBUTE,
    CONF_MEASUREMENT_TYPE,
    CONF_PROFILE_MAP,
    CONF_SELECTED_PROFILES,
    CONF_ZDROJ_DAT,
    DEFAULT_DAYS_BACK_FETCH,
    DEFAULT_DAYS_TO_KEEP_SERIES,
    DEFAULT_FETCH_HOUR,
    DEFAULT_INCLUDE_SERIES_ATTRIBUTE,
    DOMAIN,
    ENV_PRODUCTION,
    ENV_TEST,
    MEASUREMENT_AB,
    MEASUREMENT_C1,
    ZDROJ_ELEKTROMER,
    ZDROJ_ODBERNE_MISTO,
)


class EGDConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for EG.D OpenAPI."""

    VERSION = 1

    def __init__(self) -> None:
        self._user_input: dict[str, Any] = {}
        self._profiles: list[Profile] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            self._user_input = user_input
            await self.async_set_unique_id(user_input[CONF_EAN])
            self._abort_if_unique_id_configured()

            try:
                self._profiles = await self._async_fetch_profiles(user_input)
                return await self.async_step_profiles()
            except EGDAPIAuthError:
                errors["base"] = "auth"
            except EGDAPIError:
                errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_ENVIRONMENT, default=ENV_PRODUCTION): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[ENV_PRODUCTION, ENV_TEST],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key="environment",
                    )
                ),
                vol.Required(CONF_CLIENT_ID): str,
                vol.Required(CONF_CLIENT_SECRET): str,
                vol.Required(CONF_EAN): str,
                vol.Required(CONF_MEASUREMENT_TYPE, default=MEASUREMENT_AB): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[MEASUREMENT_AB, MEASUREMENT_C1],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_ZDROJ_DAT, default=ZDROJ_ELEKTROMER): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[ZDROJ_ELEKTROMER, ZDROJ_ODBERNE_MISTO],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_profiles(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        profile_options = [
            selector.SelectOptionDict(value=profile.code, label=f"{profile.code} - {profile.name}")
            for profile in self._profiles
        ]
        default_selection = self._default_profiles(self._profiles)

        if user_input is not None:
            selected = user_input.get(CONF_SELECTED_PROFILES, [])
            if not selected:
                errors["base"] = "profiles_required"
            else:
                profile_map = {p.code: p.name for p in self._profiles}
                data = dict(self._user_input)
                data[CONF_SELECTED_PROFILES] = selected
                data[CONF_PROFILE_MAP] = profile_map
                data[CONF_FETCH_MINUTE] = randint(1, 59)

                return self.async_create_entry(
                    title=f"EG.D {data[CONF_EAN]}",
                    data=data,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_SELECTED_PROFILES, default=default_selection): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=profile_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(step_id="profiles", data_schema=schema, errors=errors)

    async def _async_fetch_profiles(self, user_input: Mapping[str, Any]) -> list[Profile]:
        session = async_get_clientsession(self.hass)
        client = EGDOpenAPIClient(
            session=session,
            environment=user_input[CONF_ENVIRONMENT],
            client_id=user_input[CONF_CLIENT_ID],
            client_secret=user_input[CONF_CLIENT_SECRET],
        )
        return await client.async_get_profiles(user_input[CONF_MEASUREMENT_TYPE])

    @staticmethod
    def _default_profiles(profiles: list[Profile]) -> list[str]:
        if not profiles:
            return []

        def _contains(code: str, keys: tuple[str, ...]) -> bool:
            code_up = code.upper()
            return any(key in code_up for key in keys)

        import_candidates = [p.code for p in profiles if _contains(p.code, ("IC", "ICQ"))]
        export_candidates = [p.code for p in profiles if _contains(p.code, ("IS", "ISQ"))]

        selected: list[str] = []

        if import_candidates:
            preferred = next((c for c in import_candidates if "ICQ2" in c.upper()), import_candidates[0])
            selected.append(preferred)

        if export_candidates:
            preferred = next((c for c in export_candidates if "ISQ2" in c.upper()), export_candidates[0])
            if preferred not in selected:
                selected.append(preferred)

        if not selected:
            selected = [profiles[0].code]

        return selected

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return EGDOptionsFlow(config_entry)


class EGDOptionsFlow(config_entries.OptionsFlow):
    """Handle integration options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        profile_map: dict[str, str] = self.config_entry.data.get(CONF_PROFILE_MAP, {})
        selected_profiles = self.config_entry.options.get(
            CONF_SELECTED_PROFILES,
            self.config_entry.data.get(CONF_SELECTED_PROFILES, []),
        )

        profile_options = [
            selector.SelectOptionDict(value=code, label=f"{code} - {name}")
            for code, name in profile_map.items()
        ]

        schema = vol.Schema(
            {
                vol.Required(CONF_SELECTED_PROFILES, default=selected_profiles): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=profile_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    CONF_DAYS_TO_KEEP_SERIES,
                    default=self.config_entry.options.get(CONF_DAYS_TO_KEEP_SERIES, DEFAULT_DAYS_TO_KEEP_SERIES),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
                vol.Required(
                    CONF_INCLUDE_SERIES_ATTRIBUTE,
                    default=self.config_entry.options.get(
                        CONF_INCLUDE_SERIES_ATTRIBUTE,
                        DEFAULT_INCLUDE_SERIES_ATTRIBUTE,
                    ),
                ): bool,
                vol.Required(
                    CONF_FETCH_HOUR,
                    default=self.config_entry.options.get(CONF_FETCH_HOUR, DEFAULT_FETCH_HOUR),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
                vol.Required(
                    CONF_FETCH_MINUTE,
                    default=self.config_entry.options.get(
                        CONF_FETCH_MINUTE,
                        self.config_entry.data.get(CONF_FETCH_MINUTE, randint(1, 59)),
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=59)),
                vol.Required(
                    CONF_DAYS_BACK_FETCH,
                    default=self.config_entry.options.get(CONF_DAYS_BACK_FETCH, DEFAULT_DAYS_BACK_FETCH),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=14)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
