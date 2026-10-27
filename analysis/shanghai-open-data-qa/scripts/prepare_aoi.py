import json,collections,time,hashlib
from pathlib import Path
import pyarrow as pa,pyarrow.parquet as pq,shapely,numpy as np
from shapely.geometry import shape,box,mapping
ROOT=Path(__file__).resolve().parents[1]
config=json.load(open(ROOT/'evidence/analysis-config.json'));aois=config['areas']
out=ROOT/'data/aoi';out.mkdir(parents=True,exist_ok=True)
for a in aois:a['geom']=(shape(a['geometry']) if a.get('geometry') else box(*a['bbox'])).buffer(.001)
geo={'type':'FeatureCollection','features':[{'type':'Feature','properties':{k:v for k,v in a.items() if k not in ('bbox','geom','geometry')},'geometry':a.get('geometry') or mapping(box(*a['bbox']))} for a in aois]}
json.dump(geo,open(ROOT/'evidence/test-areas-wgs84.geojson','w'),ensure_ascii=False)
profiles={}
for kind in ['building','segment','connector']:
 path=ROOT/'data/overture'/f'{kind}-shanghai-2026-10-21.0.parquet'
 pf=pq.ParquetFile(path);writers={};n=invalid=empty=0;ids=set();dupids=0;sources=collections.Counter();geom_sources=collections.Counter();versions=collections.Counter();attrs=collections.Counter();counts=collections.Counter()
 for batch in pf.iter_batches(batch_size=20000):
  g=shapely.from_wkb(batch.column('geometry').to_numpy(zero_copy_only=False));n+=len(g)
  invalid+=int((~shapely.is_valid(g)).sum());empty+=int(shapely.is_empty(g).sum())
  for x in batch.column('id').to_pylist():
   if x in ids:dupids+=1
   ids.add(x)
  for ss in batch.column('sources').to_pylist():
   for source in ss or []:
    sources[source.get('dataset') or 'unknown']+=1
    versions[(source.get('dataset') or 'unknown')+' | '+str(source.get('version'))]+=1
    if source.get('property') in ('','geometry',None):geom_sources[source.get('dataset') or 'unknown']+=1
  if kind=='building':
   for field in ['height','num_floors']:
    attrs[field+'_nonnull']+=len(batch)-batch.column(field).null_count
  for a in aois:
   mask=shapely.intersects(g,a['geom']);table=pa.Table.from_batches([batch]).filter(pa.array(mask))
   if table.num_rows:
    if a['id'] not in writers:writers[a['id']]=pq.ParquetWriter(out/f'overture-{kind}-{a["id"]}.parquet',table.schema,compression='zstd')
    writers[a['id']].write_table(table);counts[a['id']]+=table.num_rows
 for w in writers.values():w.close()
 profiles[kind]={'rows':n,'duplicate_ids':dupids,'invalid_geometries':invalid,'empty_geometries':empty,'source_entries':dict(sources),'geometry_source_entries':dict(geom_sources),'source_versions':dict(versions),'attributes':dict(attrs),'aoi_with_buffer_rows':dict(counts)}
 print(kind,json.dumps(profiles[kind],ensure_ascii=False),flush=True)
json.dump(profiles,open(ROOT/'results/overture-global-profile.json','w'),ensure_ascii=False,indent=2)
