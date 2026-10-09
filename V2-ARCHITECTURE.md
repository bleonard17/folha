# folha. — V2 roadmap and technical architecture

## Shipped in V2a
- MapLibre GL JS v5.6.0 with OpenFreeMap Liberty (landscape/detailed) and Positron (minimal) vector styles. Both are free to use with attribution and currently need no API key.
- Separate color-coded destination markers and a persistent map selection interaction.
- Built-in geographic outline fallback when tiles or MapLibre fail to load. **No use of OSM volunteer raster tile servers.**
- Satellite-readiness section in selected destination details, backed by an optional JSON feed (`data/satellite-observations.json`). The feed is **empty** because no satellite-derived foliage scores have been computed.
- Open Copernicus Browser link for manual satellite inspection (users search destinations inside Copernicus Browser).

## V2b — Real satellite analysis (not implemented)
1. Define a **forested area of interest (AOI) polygon** for each destination rather than querying just a central point. Mask evergreen stands, roads, roofs, shadows, and water. AOIs and species metadata need manual validation.
2. Discover recent Sentinel-2 Level-2A imagery through Copernicus Data Space Ecosystem's **STAC endpoint**: `https://stac.dataspace.copernicus.eu/v1/`. Check per-scene and pixel-level clouds and shadow. Scene-wide cloud cover is **not** a reliable measure of local visibility.
3. Authenticated Sentinel Hub Process/Statistical APIs can compute per-AOI reflectance and vegetation indices (e.g., NDVI and visible red/green ratios) on clear pixels, comparing with species-aware autumn baseline, earlier clear dates, and matched previous-year conditions. An index by itself cannot prove autumn color; distinguish senescence from drought and land-cover changes.
4. Generate an observation only after a reproducible validation rule: plausible AOI canopy coverage, cloud-free pixel threshold, enough clear observations, observation timestamp, and confidence calibrated against trusted local photography/reports. Otherwise leave it unverified.
5. Run batch processing on a **scheduled GitHub Actions workflow**, with Copernicus API credentials in **GitHub Actions Secrets** (never in JavaScript). Publish a small JSON file to the repository. GitHub Pages remains a static, free frontend.
6. Record provenance and methodology, and avoid mixing satellite observation from days ago with a future visit-date forecast. Present separately: `Estimated stage for selected date` vs `Last satellite-observed stage as of YYYY-MM-DD`.

## Observation JSON schema
`data/satellite-observations.json` has `schema_version: 1`, `generated_at`, `methodology`, and `destinations` object keyed by site ID. A site may be displayed only when it has `validated: true`, `observed_on: YYYY-MM-DD`, `stage` from `early/turning/peak/late`, and `confidence` between 0 and 1. **Do not manually fabricate these entries.** Future schema should also carry AOI, scene IDs, cloud-free pixel fraction, baseline dates and model version before deployment.

## Caveats
- OpenFreeMap is a free third-party community service, not an SLA-backed service. Keep the built-in fallback to avoid map outages breaking the app.
- The main map's `Landscape` style is a detailed street/landscape vector **cartography**, not a satellite view or elevation/terrain DEM.
- Copernicus data may require free registration and authenticated API credentials for processing. Map viewing and external imagery browsing do not provide an automatic foliage score.
- GitHub Pages is a static site. Use Actions for scheduled processing, not browser-embedded credentials.

## References
- https://openfreemap.org/quick_start/
- https://maplibre.org/maplibre-gl-js/docs/
- https://documentation.dataspace.copernicus.eu/APIs/STAC.html
- https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/UserGuides/BeginnersGuide.html
- https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site