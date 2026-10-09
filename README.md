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
