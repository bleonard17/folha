# folha. 🍂

Portugal's autumn foliage tracker — an interactive, mobile-friendly map and guide to estimated fall colors in Portugal.

## Explore

Once GitHub Pages is enabled, visit **https://bleonard17.github.io/folha/**.

## Features

- Nine curated Portuguese foliage destinations, including Parque da Cabreia (Sever do Vouga) and Bosque das Faias (Serra da Estrela).
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
- Destination cards and map markers remain interactive, with region/date filters and a mobile-friendly interface.
- New satellite status panel with an external **Copernicus Browser** link. **No satellite-derived foliage measurements have been generated yet.** The blank `data/satellite-observations.json` file is a future pipeline output, not real-time coverage.
- See [V2 architecture and satellite processing roadmap](V2-ARCHITECTURE.md) for the planned cloud-masked Sentinel-2 analysis and optional scheduled GitHub Actions.

**Note:** The map backgrounds are vector maps, not satellite imagery. Foliage stage shown for a selected date is still weather-informed and experimental.
