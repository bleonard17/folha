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