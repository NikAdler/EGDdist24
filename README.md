# EG.D OpenAPI (Distribuce24) for Home Assistant

Home Assistant custom integration for EG.D / Distribuce24 OpenAPI.

![EG.D icon](./icon.svg)

## What it does

- Authenticates using OAuth2 `client_credentials` scope `namerena_data_openapi`.
- Supports **production** and optional **test** environments.
- Configured fully via the Home Assistant UI (config flow, no YAML).
- Creates sensors per selected profile for one EAN per config entry:
  - Entity names are human-friendly (import/export + granularity + purpose) instead of raw profile codes only.
  - Daily valid-only energy total in kWh.
  - 15-minute valid-only series in attributes (optional).
  - Last successful fetch timestamp.
- Fetches data once per hour (at configured minute) with lightweight periodic polling.
- API requests are executed automatically once per hour (plus optional manual refresh by user).
- Includes EG.D branded icon files as text-only SVG (`icon.svg`, `custom_components/egd_openapi/logo.svg`).
- Home Assistant integrační dlaždice používá ikonu z `manifest.json`; EG.D logo pro dokumentaci/repo je přes `icon.svg` a `logo.svg`.

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
- Hourly fetch minute (random minute stored once to spread API load)
- `days_back_fetch` (default 1)

## Updates from repository changes

- HACS update detection is enabled for branch-based installs (`zip_release: false`).
- To publish a new integration update, increase `custom_components/egd_openapi/manifest.json` `version`.
- After version bump is pushed, HACS offers update in Home Assistant.
- Scheduler používá přesné hodinové plánování přes `async_track_point_in_time` v timezone Europe/Prague, aby se fetch spouštěl i po delším běhu spolehlivě jednou za hodinu.
- Codex PR helper nepodporuje binární soubory v těle PR diffu; proto jsou v repozitáři pouze SVG ikony.
- HACS GitHub checks for repository description/topics/brands are external repository settings; CI workflow ignores these checks to avoid false CI failures.
- Repository description + topics + brands registration are GitHub-side requirements (cannot be fixed only by integration code).

## Troubleshooting: PR diff, icon/logo a verze 1.0.0

Pokud po instalaci vidíš stále verzi `1.0.0` nebo se nezobrazuje ikona:

1. Ověř, že HACS míří na správný repozitář a branch.
2. V Home Assistant otevři **Developer Tools → YAML** a spusť `Reload` pro custom integrations (nebo restart HA).
3. Ověř nainstalovaný manifest na disku (add-on Terminal / SSH):
   - `cat /config/custom_components/egd_openapi/manifest.json`
   - musí ukazovat aktuální `version` (v tomto repozitáři je `1.1.1`).
4. Pokud je na disku stará verze, smaž integraci z HACS, odstraň adresář
   `/config/custom_components/egd_openapi`, restartuj HA a nainstaluj znovu.
5. V HACS klikni na **Re-download** a potom **Check for updates**.

Poznámka k ikonám:
- V Codex workflow drž pouze textové ikony (SVG), jinak tlačítko "Vytvořit PR" selže.
- Pokud chceš PNG kvůli GitHub/HACS vzhledu, stáhni `icon.svg`/`logo.svg`, převeď lokálně na PNG a nahraj ručně přes GitHub UI (mimo Codex PR helper).
- Ikony v HA UI se i tak často řídí interním brand registry nebo `manifest` `icon` (mdi).

## Notes

- Hourly updates: designed for once-per-hour fetching.
- Valid-only policy:
  - A/B: includes only status `IU012`
  - C1: includes only status `W`
- Invalid points are counted and emitted as `null` in series.

## License

MIT
