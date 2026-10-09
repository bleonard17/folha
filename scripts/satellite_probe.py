#!/usr/bin/env python3
"""Experimental foliage-independent Sentinel-2 reflectance monitoring for folha.

These are observable vegetation indices, NOT validated leaf-color or peak-foliage stages.
Sites use small circular windows centered on representative coordinates. Output is
versioned JSON, with no synthetic observations and no personal data.
"""
from __future__ import annotations
import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import time
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform
import requests

API = 'https://earth-search.aws.element84.com/v1/search'
COLLECTION = 'sentinel-2-c1-l2a'
# All 19 curated map destinations, with coordinates matching index.html.
# Each observation is a 400 m SAMPLE around a representative point, not a
# forest-wide, park-wide, or region-wide measurement.
SITES = {
    'sever': {'name': 'Sever do Vouga — Parque da Cabreia', 'region': 'Centro', 'lat': 40.752806, 'lon': -8.390222},
    'faias': {'name': 'Bosque das Faias', 'region': 'Centro', 'lat': 40.413475, 'lon': -7.511206},
    'geres': {'name': 'Mata da Albergaria', 'region': 'Norte', 'lat': 41.785, 'lon': -8.145},
    'montesinho': {'name': 'Montesinho', 'region': 'Norte', 'lat': 41.936, 'lon': -6.763},
    'margaraca': {'name': 'Mata da Margaraça', 'region': 'Centro', 'lat': 40.213, 'lon': -7.923},
    'bussaco': {'name': 'Mata do Bussaco', 'region': 'Centro', 'lat': 40.379, 'lon': -8.365},
    'lousa': {'name': 'Serra da Lousã', 'region': 'Centro', 'lat': 40.092, 'lon': -8.235},
    'mamede': {'name': 'Serra de São Mamede', 'region': 'Alentejo', 'lat': 39.39, 'lon': -7.377},
    'vinhais': {'name': 'Castanheiros de Vinhais', 'region': 'Norte', 'lat': 41.836, 'lon': -7.005},
    'bertiandos': {'name': 'Lagoas de Bertiandos', 'region': 'Norte', 'lat': 41.788, 'lon': -8.628},
    'sistelo': {'name': 'Sistelo · Vale do Vez', 'region': 'Norte', 'lat': 41.983, 'lon': -8.375},
    'alvao': {'name': 'Parque Natural do Alvão', 'region': 'Norte', 'lat': 41.383, 'lon': -7.874},
    'paiva': {'name': 'Passadiços do Paiva', 'region': 'Norte', 'lat': 40.966, 'lon': -8.157},
    'freita': {'name': 'Serra da Freita', 'region': 'Norte', 'lat': 40.86, 'lon': -8.279},
    'caramulo': {'name': 'Serra do Caramulo', 'region': 'Centro', 'lat': 40.571, 'lon': -8.166},
    'choupal': {'name': 'Mata Nacional do Choupal', 'region': 'Centro', 'lat': 40.222, 'lon': -8.44},
    'setemontes': {'name': 'Mata dos Sete Montes', 'region': 'Centro', 'lat': 39.603, 'lon': -8.418},
    'pena': {'name': 'Parque da Pena', 'region': 'Lisboa', 'lat': 38.787, 'lon': -9.389},
    'monserrate': {'name': 'Parque de Monserrate', 'region': 'Lisboa', 'lat': 38.793, 'lon': -9.419},
}
REGIONS = ('Norte', 'Centro', 'Lisboa', 'Alentejo')

SIZE = 20  # 20 m UTM sampling grid; 400x400 m footprint
METERS = 20
MIN_PIXELS = 30


def search_scenes(session, lat, lon, start, end, limit=40):
    # Satellite item properties report tile-wide cloud cover. Pixel-level SCL is
    # checked separately to avoid mistaking a cloudy forest for a clear one.
    delta = 0.006
    payload = {
        'collections': [COLLECTION],
        'bbox': [lon-delta, lat-delta, lon+delta, lat+delta],
        'datetime': f'{start.isoformat()}T00:00:00Z/{end.isoformat()}T23:59:59Z',
        'limit': limit,
        'query': {'eo:cloud_cover': {'lt': 75}},
        'sortby': [{'field': 'properties.datetime', 'direction': 'desc'}],
    }
    response = session.post(API, json=payload, timeout=45)
    response.raise_for_status()
    items = response.json().get('features', [])
    return sorted(items, key=lambda x: x.get('properties', {}).get('datetime', ''), reverse=True)


def sample_asset(asset, lon, lat, resolution=Resampling.bilinear):
    href = asset['href']
    if not href.startswith('https://'):
        raise ValueError('Only HTTPS imagery assets are supported')
    x, y = transform('EPSG:4326', 'EPSG:32629', [lon], [lat])
    projection = from_origin(x[0] - SIZE*METERS/2, y[0] + SIZE*METERS/2, METERS, METERS)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', GDAL_HTTP_MAX_RETRY='2', GDAL_HTTP_RETRY_DELAY='1'):
        with rasterio.open(href) as src:
            with WarpedVRT(src, crs='EPSG:32629', transform=projection, width=SIZE, height=SIZE, resampling=resolution) as vrt:
                value = vrt.read(1, masked=True).astype('float64').filled(np.nan)
    # Earth Search COG band metadata includes scale and sometimes offsets. Values
    # already interpreted as reflectance are identified via raster metadata.
    bands = asset.get('raster:bands') or []
    meta = bands[0] if bands else {}
    scale = float(meta.get('scale', 0.0001))
    offset = float(meta.get('offset', 0))
    if resolution == Resampling.nearest:
        return value
    return value * scale + offset


def read_scene(scene, site):
    assets = scene.get('assets', {})
    red_key = next((k for k in ('red', 'B04') if k in assets), None)
    green_key = next((k for k in ('green', 'B03') if k in assets), None)
    nir_key = next((k for k in ('nir', 'nir08', 'B08') if k in assets), None)
    scl_key = next((k for k in ('scl', 'SCL') if k in assets), None)
    if not all((red_key,green_key,nir_key,scl_key)):
        raise ValueError('Scene missing red/green/nir/SCL COG bands')
    lon, lat = site['lon'], site['lat']
    red = sample_asset(assets[red_key],lon,lat)
    green = sample_asset(assets[green_key],lon,lat)
    nir = sample_asset(assets[nir_key],lon,lat)
    scl = sample_asset(assets[scl_key],lon,lat,Resampling.nearest)
    coords = np.indices((SIZE,SIZE), dtype='float64')
    circle = (coords[0]-(SIZE-1)/2)**2+(coords[1]-(SIZE-1)/2)**2 <= (SIZE*0.44)**2
    valid = circle & np.isin(scl,[4,5]) & np.isfinite(red) & np.isfinite(green) & np.isfinite(nir)
    valid &= (red>0) & (red<1.4) & (green>0) & (green<1.4) & (nir>0) & (nir<1.4)
    vegetation = valid & (scl == 4)
    return {'red':red,'green':green,'nir':nir,'scl':scl,'valid':valid,
            'vegetation':vegetation,'scene':scene,'count':int(vegetation.sum()),'total':int(circle.sum())}


def select_clear_scene(scenes, site, min_pixels=MIN_PIXELS, attempts=7):
    failures=[]
    for scene in scenes[:attempts]:
        try:
            sample=read_scene(scene,site)
            if sample['count'] >= min_pixels:
                return sample,failures
            failures.append(f"{scene.get('id','?')}: insufficient locally clear vegetation ({sample['count']})")
        except Exception as exc:
            failures.append(f"{scene.get('id','?')}: {type(exc).__name__}: {str(exc)[:120]}")
    return None,failures


def compare(baseline, latest):
    # Only use the same pixels known to be vegetated in midsummer and locally
    # cloud-free on the later acquisition; retain possible senescent bare classes.
    mask=baseline['vegetation'] & latest['valid']
    count=int(mask.sum())
    if count < MIN_PIXELS:
        return None
    def indices(s):
        ndvi=(s['nir']-s['red'])/(s['nir']+s['red']+1e-6)
        rg=s['red']/(s['green']+1e-6)
        return float(np.median(ndvi[mask])),float(np.median(rg[mask]))
    before_ndvi,before_rg=indices(baseline)
    now_ndvi,now_rg=indices(latest)
    return {'sampled_pixels':count,'sampling_resolution_m':METERS,
            'baseline_ndvi':round(before_ndvi,3),'latest_ndvi':round(now_ndvi,3),
            'ndvi_difference':round(now_ndvi-before_ndvi,3),
            'baseline_red_green_ratio':round(before_rg,3),'latest_red_green_ratio':round(now_rg,3),
            'red_green_ratio_difference':round(now_rg-before_rg,3)}


def summer_dates(today):
    year = today.year if today.month >= 9 else today.year-1
    return date(year,7,10),date(year,8,31)


def scan_site(session,site,today):
    summer_start,summer_end=summer_dates(today)
    result={'status':'unavailable','validated':False,'stage':None,
            'model':'sentinel2_summer_comparison_experimental_v1',
            'site_name':site['name'],'region':site['region'],
            'sampling_scope':'representative_point_400m',
            'site_center':{'lat':site['lat'],'lon':site['lon']}}
    # Require autumn recent image after August. Early September difference may
    # be near zero; that's a valid negative result, not evidence of late foliage.
    recent_start=max(date(today.year,9,1),today-timedelta(days=70))
    if today < recent_start:
        result['reason']='Outside northern Portugal foliage monitoring season'
        return result
    try:
        recent_scenes=search_scenes(session,site['lat'],site['lon'],recent_start,today)
        baseline_scenes=search_scenes(session,site['lat'],site['lon'],summer_start,summer_end)
        if not recent_scenes or not baseline_scenes:
            result['reason']='No Sentinel-2 scenes found in one of the comparison windows'
            return result
        recent,recent_failures=select_clear_scene(recent_scenes,site)
        baseline,baseline_failures=select_clear_scene(baseline_scenes,site)
        if not recent or not baseline:
            result['reason']='Insufficient cloud-free forest pixels in sampled scenes'
            result['available_scene_count']={'recent':len(recent_scenes),'baseline':len(baseline_scenes)}
            return result
        metrics=compare(baseline,recent)
        if not metrics:
            result['reason']='Fewer than 30 common clear vegetated reference pixels'
            return result
        result.update({'status':'experimental','metrics':metrics,
            'latest_date':recent['scene']['properties']['datetime'][:10],
            'baseline_date':baseline['scene']['properties']['datetime'][:10],
            'latest_scene':recent['scene']['id'],'baseline_scene':baseline['scene']['id'],
            'latest_tile_cloud_cover_pct':recent['scene']['properties'].get('eo:cloud_cover'),
            'baseline_tile_cloud_cover_pct':baseline['scene']['properties'].get('eo:cloud_cover'),
            'latest_local_vegetation_pixels':recent['count'],
            'baseline_local_vegetation_pixels':baseline['count'],
            'reason':'Measured spectral vegetation differences; NOT a verified foliage-color stage.'})
        return result
    except Exception as exc:
        result['reason']=f'Satellite search or imagery sampling failed: {type(exc).__name__}: {str(exc)[:140]}'
        return result


def build_document(destinations, region=None):
    return {'schema_version': 1,
            'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'source': 'Element 84 Earth Search Sentinel-2 C1 L2A',
            'source_url': 'https://earth-search.aws.element84.com/v1',
            'method': 'Cloud-screened 400 m sample around each representative map coordinate compared with summer; NOT verified autumn leaf color or region-wide vegetation',
            'sampling_scope': 'representative_point_400m',
            'coverage': '19 curated destinations across Norte, Centro, Lisboa and Alentejo',
            'region': region,
            'destinations': destinations}


def merge_regional_outputs(directory):
    """Fail closed when a regional artifact is missing, duplicated or invalid."""
    directory = Path(directory)
    combined = {}
    found_regions = set()
    for path in sorted(directory.glob('*.json')):
        document = json.loads(path.read_text(encoding='utf8'))
        if document.get('schema_version') != 1:
            raise ValueError(f'{path}: unsupported schema')
        region = document.get('region')
        if region not in REGIONS or region in found_regions:
            raise ValueError(f'{path}: invalid or duplicate region {region}')
        found_regions.add(region)
        expected = {key for key, site in SITES.items() if site['region'] == region}
        entries = document.get('destinations')
        if not isinstance(entries, dict) or set(entries) != expected:
            raise ValueError(f'{path}: missing or unexpected sites for {region}')
        for site_id, observation in entries.items():
            if not isinstance(observation, dict) or observation.get('validated') is not False:
                raise ValueError(f'{path}: {site_id} has invalid validation status')
            if observation.get('stage') is not None:
                raise ValueError(f'{path}: {site_id} claimed an unverified foliage stage')
            if observation.get('status') not in ('experimental', 'unavailable'):
                raise ValueError(f'{path}: {site_id} has unsupported status')
            if observation.get('region') != region or observation.get('sampling_scope') != 'representative_point_400m':
                raise ValueError(f'{path}: {site_id} has inconsistent region or sampling scope')
            if observation.get('status') == 'experimental' and not isinstance(observation.get('metrics'), dict):
                raise ValueError(f'{path}: {site_id} missing actual measurements')
        combined.update(entries)
    if found_regions != set(REGIONS) or set(combined) != set(SITES):
        raise ValueError(f'Incomplete regional coverage: {sorted(found_regions)}')
    return build_document({site_id: combined[site_id] for site_id in SITES})


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='data/satellite-observations.json')
    parser.add_argument('--today', default=None, help='ISO date override for tests')
    parser.add_argument('--region', choices=REGIONS, default=None,
                        help='Analyze destinations in just this region')
    parser.add_argument('--merge-dir', default=None,
                        help='Merge previously computed regional JSON files without remote requests')
    args = parser.parse_args(argv)
    if args.merge_dir:
        document = merge_regional_outputs(args.merge_dir)
    else:
        today = date.fromisoformat(args.today) if args.today else datetime.now(timezone.utc).date()
        selected = {k: v for k, v in SITES.items() if args.region is None or v['region'] == args.region}
        entries = {}
        with requests.Session() as session:
            for site_id, site in selected.items():
                print(f'Analyzing {site_id} in {site["region"]}...', flush=True)
                entries[site_id] = scan_site(session, site, today)
                print(site_id, entries[site_id]['status'], entries[site_id].get('reason'), flush=True)
        document = build_document(entries, region=args.region)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(f'Wrote {len(document["destinations"])} destination observations to {out}', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
