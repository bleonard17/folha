import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import satellite_probe as sat

def test_summer_dates():
    from datetime import date
    assert sat.summer_dates(date(2026,10,9))==(date(2026,7,10),date(2026,8,31))
    assert sat.summer_dates(date(2027,3,9))==(date(2026,7,10),date(2026,8,31))

def test_diff_is_spectral_not_leaf_stage():
    shape=(20,20)
    baseline={'red':np.full(shape,0.06),'green':np.full(shape,0.10),'nir':np.full(shape,0.45),'valid':np.ones(shape,dtype=bool),'vegetation':np.ones(shape,dtype=bool)}
    latest={'red':np.full(shape,0.10),'green':np.full(shape,0.11),'nir':np.full(shape,0.37),'valid':np.ones(shape,dtype=bool),'vegetation':np.ones(shape,dtype=bool)}
    result=sat.compare(baseline,latest)
    assert result['sampled_pixels']==400
    assert result['ndvi_difference'] < 0
    assert result['red_green_ratio_difference'] > 0
    assert 'stage' not in result

def test_insufficient_pixels_returns_no_measurement():
    shape=(20,20)
    baseline={'red':np.ones(shape),'green':np.ones(shape),'nir':np.ones(shape),'valid':np.zeros(shape,dtype=bool),'vegetation':np.zeros(shape,dtype=bool)}
    latest={'red':np.ones(shape),'green':np.ones(shape),'nir':np.ones(shape),'valid':np.ones(shape,dtype=bool)}
    assert sat.compare(baseline,latest) is None

def test_failed_catalog_does_not_invent_results():
    from datetime import date
    class FailSession:
        def post(self,*args,**kwargs): raise TimeoutError('Offline')
    result=sat.scan_site(FailSession(),sat.SITES['sever'],date(2026,10,9))
    assert result['status']=='unavailable' and result['validated'] is False and result['stage'] is None
def test_all_regions_and_curated_site_count():
    assert len(sat.SITES) == 19
    assert len(set(sat.SITES)) == 19
    assert set(site['region'] for site in sat.SITES.values()) == set(sat.REGIONS)
    assert {r:sum(site['region']==r for site in sat.SITES.values()) for r in sat.REGIONS} == {
        'Norte':8, 'Centro':8, 'Lisboa':2, 'Alentejo':1
    }
    assert all(-10 < s['lon'] < -6 and 37 < s['lat'] < 43 for s in sat.SITES.values())


def test_region_merge_requires_complete_verified_manifest(tmp_path):
    import json
    from datetime import date
    for region in sat.REGIONS:
        destinations = {}
        for site_id, site in sat.SITES.items():
            if site['region'] != region:
                continue
            destinations[site_id] = {
                'status':'unavailable','validated':False,'stage':None,
                'region':region,'sampling_scope':'representative_point_400m',
                'site_name':site['name'],
                'site_center':{'lat':site['lat'],'lon':site['lon']},
                'reason':'clouds'
            }
        (tmp_path / (region+'.json')).write_text(
            json.dumps(sat.build_document(destinations,region=region)),encoding='utf8'
        )
    merged=sat.merge_regional_outputs(tmp_path)
    assert len(merged['destinations']) == 19
    assert list(merged['destinations']) == list(sat.SITES)
    assert merged['region'] is None
    assert all(not x['validated'] and x['stage'] is None for x in merged['destinations'].values())


def test_merge_rejects_missing_region(tmp_path):
    import pytest,json
    region='Norte'
    (tmp_path/'Norte.json').write_text(json.dumps(sat.build_document({
        key:{'status':'unavailable','validated':False,'stage':None,
             'region':region,'sampling_scope':'representative_point_400m'}
        for key,site in sat.SITES.items() if site['region']==region
    },region=region)),encoding='utf8')
    with pytest.raises(ValueError,match='Incomplete'):
        sat.merge_regional_outputs(tmp_path)


def test_merge_rejects_fake_verified_leaf_stage(tmp_path):
    import pytest,json
    region='Alentejo'
    (tmp_path/'Alentejo.json').write_text(json.dumps(sat.build_document({
        'mamede':{'status':'experimental','validated':False,'stage':'peak',
                  'region':region,'sampling_scope':'representative_point_400m',
                  'metrics':{'ndvi_difference':0.1}}
    },region=region)),encoding='utf8')
    with pytest.raises(ValueError,match='unverified foliage stage'):
        sat.merge_regional_outputs(tmp_path)
