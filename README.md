# EG.D OpenAPI (Distribuce24) for Home Assistant

Home Assistant custom integration for EG.D / Distribuce24 OpenAPI.

## What it does

- Authenticates using OAuth2 `client_credentials` scope `namerena_data_openapi`.
- Supports **production** and optional **test** environments.
- Configured fully via the Home Assistant UI (config flow, no YAML).
- Creates sensors per selected profile for one EAN per config entry:
  - Daily valid-only energy total in kWh.
  - 15-minute valid-only series in attributes (optional).
  - Last successful fetch timestamp.
- Fetches data once per day at configurable time with randomized minute offset.

## Install via HACS (Custom Repository)

1. Open HACS in Home Assistant.
2. Go to **Integrations**.
3. Open the 3-dot menu → **Custom repositories**.
4. Add this repository URL.
5. Category: **Integration**.
6. Install **EG.D OpenAPI (Distribuce24)**.
7. Restart Home Assistant.

## Manual install

1. Copy `custom_components/egd_openapi` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration**.
4. Search for **EG.D OpenAPI (Distribuce24)**.

## Configuration (UI only)

Setup asks for:
- Environment (production or test)
- `client_id`
- `client_secret`
- EAN (single)
- Measurement type (`A/B` or `C1`)
- `zdrojDat` (for C1)
- Profile multi-select loaded from API

Options allow changing:
- Selected profiles
- `days_to_keep_series` (default 7)
- `include_series_attribute` (default true)
- Daily fetch time (default 16:xx local, random minute stored once)
- `days_back_fetch` (default 1)

## Notes

- Daily updates: designed for once-per-day fetching.
- Valid-only policy:
  - A/B: includes only status `IU012`
  - C1: includes only status `W`
- Invalid points are counted and emitted as `null` in series.

## License

MIT
