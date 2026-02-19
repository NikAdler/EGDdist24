# EG.D OpenAPI (Distribuce24) pro Home Assistant

Vlastní integrace Home Assistant pro EG.D / Distribuce24 OpenAPI.

![Logo EG.D](./icon.svg)

## Co integrace dělá

- Přihlášení přes OAuth2 `client_credentials` se scope `namerena_data_openapi`.
- Podpora prostředí **produkce** i **test**.
- Nastavení přes UI (config flow), bez YAML konfigurace.
- Senzory pro vybrané profily na jedno EAN:
  - denní energie (kWh),
  - 15min řada v atributu (volitelně),
  - čas posledního úspěšného načtení.
- Automatické načítání dat 1× za hodinu.

## Instalace přes HACS (Custom repository)

1. V Home Assistant otevři HACS.
2. Integrations → menu se 3 tečkami → **Custom repositories**.
3. Přidej URL tohoto repozitáře, typ **Integration**.
4. Nainstaluj **EG.D OpenAPI (Distribuce24)**.
5. Restartuj Home Assistant.

## Proč HACS někdy píše „Commit ... bude stažen“

Tohle je standardní chování HACS při instalaci z větve bez release.
Aby HACS zobrazoval čitelnou verzi místo commitu, používej GitHub Release:

- v `custom_components/egd_openapi/manifest.json` zvyš `version`,
- vytvoř GitHub **tag** a **release** se stejnou verzí,
- HACS pak nabídne instalaci/release podle verze.

Repo je nastavený na branch instalaci (`zip_release: false`), takže HACS bere aktuální commit z větve.

## Nastavení integrace

Při prvním spuštění zadáš:

- prostředí (production/test),
- `client_id`, `client_secret`,
- EAN,
- typ měření (`A/B` nebo `C1`),
- zdroj dat pro C1,
- výběr profilů.

V nastavení integrace lze měnit:

- vybrané profily,
- kolik dní držet řadu,
- zapnutí/vypnutí atributu se sérií,
- minutu hodinového načítání,
- počet dní zpětného načtení.

## Poznámky

- Časové plánování běží spolehlivě 1× za hodinu.
- Validní body:
  - A/B: `IU012`
  - C1: `W`
- Nevalidní body se počítají a do řady jdou jako `null`.

## Troubleshooting

Pokud po aktualizaci nevidíš novou verzi:

1. Zkontroluj `/config/custom_components/egd_openapi/manifest.json`.
2. V HACS dej **Re-download**.
3. Restartuj Home Assistant.

Aktuální verze v tomto repozitáři: **1.1.5**.

## Licence

MIT
