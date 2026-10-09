# folha. 🍂

Portugal's autumn foliage tracker — an interactive, mobile-friendly map and guide to estimated fall colors in Portugal.

## Explore

Once GitHub Pages is enabled, visit **https://bleonard17.github.io/folha/**.

## Features

- **19 curated destinations**, including Sever do Vouga — Parque da Cabreia, Bosque das Faias (Serra da Estrela), Mata Nacional do Choupal, Alvão, Bertiandos, Vinhais, and Paiva Walkways.
- Interactive vector map with clickable places (no OpenStreetMap raster-tile dependency).
- Visit-date picker, search, filters, destination rankings, and detailed outlooks.
- Weather forecasts and recent observations fetched directly from [Open-Meteo](https://open-meteo.com/).
- Responsive design for mobile and desktop.

## How it works

This is a static website; `index.html` is the complete application. GitHub Pages serves it without a server or API keys. Weather and map library requests depend on the visitor's network access. A locally bundled map fallback displays when the map library is unavailable.

## Important limitations

Foliage stage and peak dates are **experimental estimates**, using typical regional timing and available weather signals. **They are not verified observations of leaf colors** and should not be treated as precise forecasts. Real peak timing varies with tree species, elevation, temperature, drought, storms, and local conditions.

## Deployment

In this repository, open **Settings → Pages**. Under **Build and deployment**, select **Deploy from a branch**, choose **main** and **/(root)**, then **Save**. GitHub will publish at the URL above, usually within a few minutes.

### If GitHub Pages shows 404

Check **Actions** for a completed `pages build and deployment` run. If the branch-based site hasn't built, make a small edit using the GitHub website while signed in as the repository owner; GitHub requires a commit from an admin with a verified email for branch publishing.

## V2 map and satellite groundwork

- Detailed **Landscape** (OpenFreeMap Liberty) and **Minimal** (Positron) interactive maps via MapLibre GL JS; no API key required. If map libraries or tiles fail, a built-in outline remains usable.
- Map markers open **in-map destination tooltips** with foliage stage, estimated timing score, peak window, and an optional link that scrolls to detailed trip information. Clicking a map marker no longer forces the page to scroll.
- Destination cards and map markers remain interactive, with region/date filters and a mobile-friendly interface.
- New satellite status panel with an external **Copernicus Browser** link. **No satellite-derived foliage measurements have been generated yet.** The blank `data/satellite-observations.json` file is a future pipeline output, not real-time coverage.
- See [V2 architecture and satellite processing roadmap](V2-ARCHITECTURE.md) for the planned cloud-masked Sentinel-2 analysis and optional scheduled GitHub Actions.

**Note:** The map backgrounds are vector maps, not satellite imagery. Foliage stage shown for a selected date is still weather-informed and experimental.

## Extended destinations (October 2026)

Ten additional destinations have been curated mainly north of Lisbon: Vinhais chestnut groves, Lagoas de Bertiandos, Sistelo, Alvão Natural Park, Paiva Walkways, Serra da Freita, Serra do Caramulo, Mata Nacional do Choupal, Mata dos Sete Montes, and Parque da Pena.

**Important:** These new locations have provisional seasonal peak windows. The dates are planning heuristics, **not verified local foliage observations or scientific forecasts**. The marker coordinates identify representative areas, not necessarily trailheads or entrances. This is not an exhaustive inventory of every Portuguese protected area; mixed evergreen habitats may show only patchy fall color.

Tourism and nature references: [Visit Portugal — Alvão](https://www.visitportugal.com/pt-pt/content/parque-natural-do-alvao), [Paiva Walkways](https://www.visitportugal.com/pt-pt/content/passadicos-do-paiva), [Parque da Pena](https://www.visitportugal.com/pt-pt/content/parque-da-pena), [Mata dos Sete Montes](https://www.visitportugal.com/en/NR/exeres/E770E38B-1249-47FD-A093-542D13E3B1D2), [Serra do Caramulo](https://www.visitportugal.com/pt-pt/destinos/centro-de-portugal/73760), and [Vinhais chestnut season](https://www.visitportugal.com/en/node/522161).

## Public site improvements — October 2026

- **EN / PT toggle** in the site header: English (US) and Portuguese (Portugal). The preferred language is saved in browser local storage; no account is required.
- **Zoom-responsive map marker clustering** on the detailed MapLibre map. Cluster circles show nearby destination counts; select a cluster to zoom in. The always-available SVG fallback continues to show every destination independently.
- **Destination-type filters** distinguish forests and gardens from broader nature areas; this is about the type of place, **not whether autumn colors have been verified**.
- **Privacy and transparency:** a bilingual [privacy, sources and estimates notice](privacy.html) explains browser storage, external providers, map attribution and the experimental nature of the foliage scores. No optional analytics or ad-tracking has been added. A cookie-consent banner may become necessary if those services are added later.
- Project-facing UI is branded as **folha.** without a personal byline. The public GitHub account hosting the source remains discoverable.

Data caveat: nineteen destinations are **curated locations, not comprehensive Portugal-wide coverage**, and scores/peak dates remain experimental weather-informed approximations rather than observations of actual leaf colors.
