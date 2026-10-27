import json,csv,collections,re,time
from pathlib import Path
import osmium,shapely,pyarrow.parquet as pq
from shapely.geometry import box,mapping
from pyproj import Transformer
ROOT=Path(__file__).resolve().parents[1];cfg=json.load(open(ROOT/'evidence/analysis-config.json'))
rows=list(csv.DictReader(open(ROOT/'results/building-audit-candidates.csv')));ids={int(r['osm_id'][1:]) for r in rows if r['osm_id'].startswith('w')};history=[]
for w in osmium.FileProcessor(str(ROOT/'data/geofabrik/china-latest.osm.pbf'),entities=osmium.osm.WAY).with_filter(osmium.filter.IdFilter(ids)):
 history.append({'osm_id':'w'+str(w.id),'version':w.version,'last_modified_utc':str(w.timestamp),'tags':{t.k:t.v for t in w.tags if t.k in ['name','building','building:levels','layer','level','level:ref','addr:floor']}})
json.dump(history,open(ROOT/'results/building-candidate-osm-history.json','w'),ensure_ascii=False,indent=2)
print('BUILDING HISTORY',json.dumps(history,ensure_ascii=False),flush=True)
fwd=Transformer.from_crs(4326,32651,always_xy=True);inv=Transformer.from_crs(32651,4326,always_xy=True)
def project(g):return shapely.transform(g,fwd.transform,interleaved=False)
def unproject(g):return shapely.transform(g,inv.transform,interleaved=False)
allowed={'motorway','trunk','primary','secondary','tertiary','residential','living_street','unclassified','service','track','road','unknown'}
t=pq.read_table(ROOT/'data/geofabrik/roads-shanghai.parquet');osm=t.to_pylist();og=project(shapely.from_wkb([r.pop('geometry') for r in osm]));gaps=[];feats=[]
for a in cfg['areas']:
 region=project(shapely.geometry.shape(a['geometry']) if a.get('geometry') else box(*a['bbox']));ov=pq.read_table(ROOT/'data/aoi'/f'overture-segment-{a["id"]}.parquet').to_pylist();lines=[]
 for r in ov:
  if r['subtype']=='road' and r['class'] in allowed and not any('is_under_construction' in (x.get('values') or []) for x in r.get('road_flags') or []):lines.append(project(shapely.from_wkb(r['geometry'])))
 cover=shapely.union_all(lines).buffer(5)
 for r,g in zip(osm,og):
  tags=json.loads(r['tags_json']);cl=tags.get('highway','').removesuffix('_link')
  if cl not in allowed or not g.intersects(region):continue
  gap=g.intersection(region).difference(cover)
  if gap.length<10:continue
  props={'area':a['name'],'area_id':a['id'],'osm_id':r['id'],'class':cl,'uncovered_length_5m_m':float(gap.length),'name':tags.get('name',''),'access':tags.get('access',''),'status':'reference_difference_manual_review'}
  gaps.append(props);feats.append({'type':'Feature','properties':props,'geometry':mapping(unproject(gap))})
json.dump({'type':'FeatureCollection','features':feats},open(ROOT/'results/road-reference-gaps.geojson','w'),ensure_ascii=False,separators=(',',':'))
if gaps:
 with open(ROOT/'results/road-reference-gaps.csv','w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(gaps[0]));w.writeheader();w.writerows(sorted(gaps,key=lambda x:x['uncovered_length_5m_m'],reverse=True))
print('ROAD GAPS',len(gaps),collections.Counter(r['area'] for r in gaps),flush=True)
