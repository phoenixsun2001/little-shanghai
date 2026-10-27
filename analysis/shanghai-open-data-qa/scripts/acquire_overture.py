"""Stream the fixed Overture release, bbox-pushdown then exact municipal intersection.
Raw features are preserved (not clipped) and saved as local parquet; no credentials.
"""
import json,time,hashlib,sys
from pathlib import Path
import numpy as np
import pyarrow as pa,pyarrow.parquet as pq
import shapely
import overturemaps

ROOT=Path(__file__).resolve().parents[1]
RELEASE='2026-10-21.0'
city=shapely.union_all([shapely.geometry.shape(f['geometry']) for f in json.load(open(ROOT/'evidence/shanghai-administrative-boundary-wgs84.geojson'))['features']])
bbox=list(city.bounds)
shapely.prepare(city)
kind=sys.argv[1]
out=ROOT/'data/overture'/f'{kind}-shanghai-{RELEASE}.parquet'
out.parent.mkdir(parents=True,exist_ok=True)
if out.exists() and out.with_suffix('.manifest.json').exists():
 print('Already acquired:',out,flush=True);sys.exit(0)
start=time.time();print('ACQUIRE',kind,RELEASE,'bbox',bbox,flush=True)
reader=overturemaps.record_batch_reader(kind,bbox=bbox,release=RELEASE,connect_timeout=20,request_timeout=120,stac=True)
if reader is None:raise RuntimeError('No Overture reader')
print('SCHEMA',reader.schema,flush=True)
writer=None;raw=kept=0
try:
 for batch in reader:
  raw+=batch.num_rows
  arr=shapely.from_wkb(batch.column('geometry').to_numpy(zero_copy_only=False))
  mask=shapely.intersects(arr,city)
  table=pa.Table.from_batches([batch]).filter(pa.array(mask))
  if table.num_rows:
   if writer is None:writer=pq.ParquetWriter(str(out)+'.partial',table.schema,compression='zstd')
   writer.write_table(table,row_group_size=10000);kept+=table.num_rows
  print(json.dumps({'type':kind,'bbox_rows_seen':raw,'municipality_rows_saved':kept,'elapsed_s':round(time.time()-start,1)}),flush=True)
finally:
 if writer:writer.close()
if writer is None:raise RuntimeError('No rows saved; keep absence separate from completeness.')
Path(str(out)+'.partial').replace(out)
sha=hashlib.file_digest(open(out,'rb'),'sha256').hexdigest()
manifest={'source':'Overture Maps','release':RELEASE,'type':kind,'source_uri':f's3://overturemaps-us-west-2/release/{RELEASE}/theme='+('buildings' if kind=='building' else 'transportation')+f'/type={kind}/','bbox_wgs84':bbox,'selection':'geometry intersects union of 16 WGS84 Shanghai districts; original geometries retained','bbox_rows':raw,'municipality_rows':kept,'bytes':out.stat().st_size,'sha256':sha,'elapsed_s':round(time.time()-start,1),'acquired_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'file':out.name}
json.dump(manifest,open(out.with_suffix('.manifest.json'),'w'),ensure_ascii=False,indent=2)
print('DONE',json.dumps(manifest),flush=True)
