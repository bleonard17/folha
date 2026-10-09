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
SITES = {
    'sever': {'name': 'Sever do Vouga — Parque da Cabreia', 'lat': 40.752806, 'lon': -8.390222},
    'faias': {'name': 'Bosque das Faias', 'lat': 40.413475, 'lon': -7.511206},
}
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
            'site_name':site['name'],'site_center':{'lat':site['lat'],'lon':site['lon']}}
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


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='data/satellite-observations.json')
    parser.add_argument('--today',default=None,help='ISO date override for tests')
    args=parser.parse_args(argv)
    today=date.fromisoformat(args.today) if args.today else datetime.now(timezone.utc).date()
    result={'schema_version':1,'generated_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'source':'Element 84 Earth Search Sentinel-2 C1 L2A',
            'source_url':'https://earth-search.aws.element84.com/v1',
            'method':'Small-area cloud-screened spectral index comparison against summer reference; NOT a verified autumn leaf-color observation',
            'destinations':{}}
    with requests.Session() as session:
        for site_id, site in SITES.items():
            print(f'Analyzing {site_id}...',flush=True)
            result['destinations'][site_id]=scan_site(session,site,today)
            print(site_id,result['destinations'][site_id]['status'],result['destinations'][site_id].get('reason'),flush=True)
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f'Wrote {out}',flush=True)
    return 0


if __name__=='__main__':sys.exit(main())