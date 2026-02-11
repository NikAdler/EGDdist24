# EG.D OpenAPI (Distribuce24) for Home Assistant

Home Assistant custom integration for EG.D / Distribuce24 OpenAPI.

![EG.D icon](./icon.svg)

## What it does

- Authenticates using OAuth2 `client_credentials` scope `namerena_data_openapi`.
- Supports **production** and optional **test** environments.
- Configured fully via the Home Assistant UI (config flow, no YAML).
- Creates sensors per selected profile for one EAN per config entry:
  - Daily valid-only energy total in kWh.
  - 15-minute valid-only series in attributes (optional).
  - Last successful fetch timestamp.
- Fetches data once per day at configurable time with randomized minute offset.
- Includes EG.D branded icon files (`icon.svg`, `custom_components/egd_openapi/logo.svg`).
- Home Assistant integrační dlaždice používá ikonu z `manifest.json`; EG.D logo je součástí repozitáře/HACS (`icon.svg`, `logo.svg`).

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

## Updates from repository changes

- HACS update detection is enabled for branch-based installs (`zip_release: false`).
- To publish a new integration update, increase `custom_components/egd_openapi/manifest.json` `version`.
- After version bump is pushed, HACS offers update in Home Assistant.
- Codex PR helper nepodporuje binární soubory v těle PR diffu; proto používáme textové SVG ikony místo PNG.

## Notes

- Daily updates: designed for once-per-day fetching.
- Valid-only policy:
  - A/B: includes only status `IU012`
  - C1: includes only status `W`
- Invalid points are counted and emitted as `null` in series.

## License

MIT
