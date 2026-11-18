# folha. — Architecture and validation roadmap

_Reviewed 18 November 2026. Source of truth: [index.html](index.html), [scripts/satellite_probe.py](scripts/satellite_probe.py), [satellite workflow](.github/workflows/satellite.yml) and [data feed](data/satellite-observations.json)._

## Production architecture

- **Hosting:** GitHub Pages, canonical custom domain **https://folha.trilho.dev/** via [CNAME](CNAME); Cloudflare provides DNS only for the subdomain.
- **Frontend:** Static [index.html](index.html), translation dictionary and localization in [i18n.js](i18n.js), bilingual [privacy / methods notice](privacy.html). All data is visible client-side; no account or backend is needed.
- **Maps:** MapLibre GL JS with OpenFreeMap Liberty / Positron vector styles, markers/popups, clustering at overview zoom and an interactive bundled SVG fallback. This is **cartography**, not satellite imagery.
- **Foliage forecast:** Approximate seasonal peak calendar, simple temperature-history shifts, forecast rain and wind. The displayed stage and timing score are **planning heuristics**, not observed canopy colors.
- **Satellite observations:** Weekly September–December, four regional GitHub Actions jobs (Norte, Centro, Lisboa, Alentejo) run [scripts/satellite_probe.py](scripts/satellite_probe.py). A merger validates all **19** site IDs before committing a JSON feed. The app reads the freshest GitHub raw JSON with a bundled-file fallback because bot-generated commits do not trigger a GitHub Pages rebuild.
- **Imagery source:** Element 84 [Earth Search STAC](https://earth-search.aws.element84.com/v1), Sentinel-2 Level 2A band COGs (red, green, NIR and SCL). No commercial Copernicus API credentials are currently required.
- **Observation semantics:** Locally cloud-screened approximately **400 × 400 m sample** centered on each map pin; compare recent NDVI and red/green ratios against a July–August reference scene. A sample is neither an entire park nor a reliable representation of every species or leaf color. The output stays `validated:false` and `stage:null` even where real satellite measurements exist.
- **Status data:** `experimental` indicates actual measured spectral differences with acquisition dates; `unavailable` means no qualifying paired observations. Do not treat lack of data as green foliage. The frontend never translates these data into a verified peak-color class.

## Remaining scientific work (not implemented)

1. **Validate forest boundaries and sample placement.** Replace representative points with curated polygons; exclude evergreen stands, roads, buildings, water, and open ground. Map current markers are *not* guaranteed trailheads.
2. **Validate against dated local photographs / ground reports.** Define species-specific color stages and calibration before claiming satellite-derived foliage onset, peak or confidence.
3. **Handle temporal and atmospheric differences.** Multiple matched clear observations, cloud/shadow and terrain screening, cross-year baselines and drought/storm confounders are not solved by two simple spectral indices.
4. **Document confidence only with evidence.** Avoid displaying a fabricated confidence score when coverage is sparse, or reinterpreting NDVI alone as a tree-color measurement.
5. **Expand beyond the 19 curated mainland points only after validating sample representativeness.** The four regional labels refer to the *existing tracked destinations*, not full satellite coverage of those regions or the Azores/Madeira.

## Data contract

The committed [JSON](data/satellite-observations.json) uses `schema_version:1`, `generated_at`, `source`, `method`, `sampling_scope`, and a `destinations` dictionary keyed by ID. Each record stores `region`, `site_center`, `validated:false`, `stage:null`, `status`; measured records also hold `latest_date`, `baseline_date`, source scene IDs, NDVI/red-green metrics and paired pixel counts.

A future validated leaf-color stage would require **a new, separately reviewed evidence model**. Do not populate `validated:true` or `stage` merely because a cloud-free scene exists.

## Operations and limitations

- The scheduled workflow is [satellite.yml](.github/workflows/satellite.yml). [Tests](tests/test_satellite_probe.py) enforce regional completeness and fail on fabricated leaf stages.
- [Social preview workflow](.github/workflows/social-preview.yml) renders the artwork in [social-preview.svg](social-preview.svg) to [og-image.png](og-image.png) for WhatsApp / iMessage.
- OpenFreeMap and Earth Search are third-party services without an application-specific uptime guarantee. A map fallback and a lack-of-satellite-data state are intentional.
- Avoid adding a Cloudflare Worker / database or moving the site off Pages without a concrete feature that requires it.

## References

- https://openfreemap.org/quick_start/
- https://maplibre.org/maplibre-gl-js/docs/
- https://earth-search.aws.element84.com/v1
- https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED
- https://docs.github.com/en/pages
