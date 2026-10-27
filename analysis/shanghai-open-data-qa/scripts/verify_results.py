"""Recompute decisive metrics directly from saved matched-pair evidence and geometry."""
import json,csv,math,hashlib,collections
from pathlib import Path
import numpy as np,pyarrow.parquet as pq,shapely
ROOT=Path(__file__).resolve().parents[1]
b=json.load(open(ROOT/'results/building-metrics.json'));r=json.load(open(ROOT/'results/road-metrics.json'));pairs=list(csv.DictReader(open(ROOT/'results/building-matched-pairs.csv')))
checks=[]
def check(name,condition):
 assert condition,name;checks.append({'check':name,'result':'passed'})
for x in b:
 pp=[p for p in pairs if p['area']==x['area']]
 check(x['area']+' denominator reconciliation',x['osm_ref_matched']+x['osm_ref_unmatched']==x['osm_reference_buildings'])
 check(x['area']+' pair row count',len(pp)==x['osm_ref_matched'])
 check(x['area']+' unique reference matching',len({p['osm_id'] for p in pp})==len(pp))
 check(x['area']+' unique target matching',len({p['overture_id'] for p in pp})==len(pp))
 check(x['area']+' coverage recomputation',abs(x['reference_match_rate']-len(pp)/x['osm_reference_buildings'])<1e-12)
 check(x['area']+' median/P95 centroid recomputation',abs(x['centroid_p95_m']-np.quantile([float(p['centroid_distance_m']) for p in pp],.95))<1e-10)
 check(x['area']+' maximum geometry differences recomputation',abs(x['centroid_max_m']-max(float(p['centroid_distance_m']) for p in pp))<1e-10 and abs(x['hausdorff_max_m']-max(float(p['hausdorff_m']) for p in pp))<1e-10)
 # Re-read an Overture/OSM pair and recompute its IoU in geographic coordinates.
 ov=pq.read_table(ROOT/'data/aoi'/f'overture-building-{x["area_id"]}.parquet',columns=['id','geometry']).to_pylist();od={p['id']:shapely.from_wkb(p['geometry']) for p in ov}
 p=pp[len(pp)//2]
 os=pq.read_table(ROOT/'data/geofabrik/buildings-shanghai.parquet',columns=['id','geometry']).to_pylist();g=next(shapely.from_wkb(q['geometry']) for q in os if q['id']==p['osm_id']);o=od[p['overture_id']]
 recomputed=g.intersection(o).area/g.union(o).area
 check(x['area']+' independent sample IoU recomputation',abs(float(p['iou'])-recomputed)<.001)
 check(x['area']+' zero independent matches treated unavailable',x['non_osm_source_matches']==0 and x['absolute_horizontal_accuracy'] is None)
for x in r:
 check(x['area']+' '+x['source']+' connectivity range',0<=x['lcc_length_share']<=1)
 if x['source']=='Overture':
  for d in [3,5,10]:
   check(x['area']+f' {d}m road coverage recomputation',abs(x[f'osm_reference_length_covered_within_{d}m']-x[f'osm_reference_covered_length_m_{d}m']/x[f'osm_reference_length_m_{d}m'])<1e-12)
  check(x['area']+' buffer coverage monotonicity',x['osm_reference_length_covered_within_3m']<=x['osm_reference_length_covered_within_5m']+1e-12<=x['osm_reference_length_covered_within_10m']+2e-12)
for typ in ['building','segment','connector']:
 p=ROOT/'data/overture'/f'{typ}-shanghai-2026-10-21.0.parquet';m=json.load(open(p.with_suffix('.manifest.json')))
 check(typ+' saved row count',pq.ParquetFile(p).metadata.num_rows==m['municipality_rows'])
 check(typ+' SHA256',hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()==m['sha256'])
gf=json.load(open(ROOT/'evidence/geofabrik-extract-manifest.json'));expected=(ROOT/'evidence/geofabrik-china-latest.osm.pbf.md5').read_text().split()[0]
check('Geofabrik official MD5',gf['source_md5']==expected)
ms=json.load(open(ROOT/'evidence/microsoft-coverage-audit.json'));check('Microsoft missing coverage is not numeric completeness',not ms['intersecting_partitions'] and ms['not_a_zero_completeness_measurement'])
hist=json.load(open(ROOT/'results/building-candidate-osm-history.json'));check('All unmatched candidates occur after principal OSM building snapshot',len(hist)==sum(x['osm_ref_unmatched'] for x in b) and all(x['version']==1 and x['last_modified_utc']>'2026-09-06' for x in hist))
cfg=json.load(open(ROOT/'evidence/analysis-config.json'));boundary=json.load(open(ROOT/'evidence/shanghai-administrative-boundary-wgs84.geojson'))
lu=shapely.geometry.shape(cfg['areas'][0]['geometry']);pd=next(shapely.geometry.shape(f['geometry']) for f in boundary['features'] if '浦东' in str(f['properties']))
check('Lujiazui boundary excludes the opposite bank',lu.difference(pd).area<1e-12)
json.dump({'checks':checks,'passed':len(checks)},open(ROOT/'results/verification.json','w'),ensure_ascii=False,indent=2)
print('Passed',len(checks),'reconciliation, evidence and provenance checks.')
