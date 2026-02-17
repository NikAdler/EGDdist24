# Version: 1.0.9
"""Constants for EG.D OpenAPI integration."""

from __future__ import annotations

DOMAIN = "egd_openapi"
NAME = "EG.D OpenAPI (Distribuce24)"

CONF_ENVIRONMENT = "environment"
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_EAN = "ean"
CONF_MEASUREMENT_TYPE = "measurement_type"
CONF_ZDROJ_DAT = "zdroj_dat"
CONF_SELECTED_PROFILES = "selected_profiles"
CONF_PROFILE_MAP = "profile_map"

CONF_DAYS_TO_KEEP_SERIES = "days_to_keep_series"
CONF_INCLUDE_SERIES_ATTRIBUTE = "include_series_attribute"
CONF_FETCH_HOUR = "fetch_hour"
CONF_FETCH_MINUTE = "fetch_minute"
CONF_DAYS_BACK_FETCH = "days_back_fetch"

ENV_PRODUCTION = "production"
ENV_TEST = "test"

MEASUREMENT_AB = "A/B"
MEASUREMENT_C1 = "C1"

ZDROJ_ELEKTROMER = "ELEKTROMER"
ZDROJ_ODBERNE_MISTO = "ODBERNE_MISTO"

DEFAULT_DAYS_TO_KEEP_SERIES = 7
DEFAULT_INCLUDE_SERIES_ATTRIBUTE = True
DEFAULT_FETCH_HOUR = 16
DEFAULT_DAYS_BACK_FETCH = 1

VALID_STATUS_AB = "IU012"
VALID_STATUS_C1 = "W"

ATTR_INTERVAL_MINUTES = 15
POINTS_PER_DAY = 96

PLATFORMS: list[str] = ["sensor"]

TOKEN_SCOPE = "namerena_data_openapi"

PROD_TOKEN_URL = "https://idm.distribuce24.cz/oauth/token"
PROD_DATA_BASE = "https://data.distribuce24.cz/rest"
TEST_TOKEN_URL = "https://test.distribuce24.cz/idm/oauth/token"
TEST_DATA_BASE = "https://test.distribuce24.cz/openApi"

COORDINATOR = "coordinator"
UNSUB_SCHEDULE = "unsub_schedule"
