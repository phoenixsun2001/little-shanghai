"""Extract OSM buildings (ways + multipolygon relations) and roads from Geofabrik.
A bounded node dictionary avoids a China-wide geometry location cache.
The node extent includes 0.03 degree padding beyond the municipality bbox.
"""
import json,time,hashlib,collections
from pathlib import Path
import osmium,shapely,numpy as np,pyarrow as pa,pyarrow.parquet as pq
from shapely.geometry import shape,Polygon,LineString
from shapely.ops import polygonize,unary_union
ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/'data/geofabrik/china-latest.osm.pbf'
OUT=ROOT/'data/geofabrik';OUT.mkdir(exist_ok=True,parents=True)
city=unary_union([shape(f['geometry']) for f in json.load(open(ROOT/'evidence/shanghai-administrative-boundary-wgs84.geojson'))['features']]);shapely.prepare(city)
a,b,c,d=city.bounds;pad=.03;bb=(a-pad,b-pad,c+pad,d+pad)
start=time.time()
class Handler(osmium.SimpleHandler):
 def __init__(self):
  super().__init__();self.locations={};self.ways={};self.buildings=[];self.roads=[];self.relations=[];self.total_nodes=0;self.total_ways=0;self.incomplete=0;self.road_nodes={}
 def node(self,n):
  self.total_nodes+=1
  if n.location.valid():
   x,y=n.location.lon,n.location.lat
   if bb[0]<=x<=bb[2] and bb[1]<=y<=bb[3]:self.locations[n.id]=(x,y)
  if self.total_nodes%10000000==0:print('nodes',self.total_nodes,'retained',len(self.locations),'elapsed',round(time.time()-start),flush=True)
 def way(self,w):
  self.total_ways+=1
  refs=[n.ref for n in w.nodes]
  if len(refs)<2 or not any(r in self.locations for r in (refs[0],refs[len(refs)//2],refs[-1])):return
  if any(r not in self.locations for r in refs):self.incomplete+=1;return
  coords=[self.locations[r] for r in refs]
  line=LineString(coords)
  self.ways[w.id]=line
  tags={t.k:t.v for t in w.tags}
  if 'building' in tags and tags['building']!='no' and refs[0]==refs[-1] and len(refs)>=4:
   poly=Polygon(coords)
   if city.intersects(poly):self.buildings.append({'id':'w'+str(w.id),'geometry':poly.wkb,'tags_json':json.dumps(tags,ensure_ascii=False),'osm_type':'way'})
  if 'highway' in tags and city.intersects(line):
   self.roads.append({'id':'w'+str(w.id),'geometry':line.wkb,'tags_json':json.dumps(tags,ensure_ascii=False),'nodes_json':json.dumps(refs),'node_coords_json':json.dumps(coords)})
 def relation(self,r):
  tags={t.k:t.v for t in r.tags}
  if tags.get('building') not in (None,'no') and tags.get('type') in ('multipolygon','building'):
   members=[(m.ref,m.role) for m in r.members if m.type=='w']
   if any(ref in self.ways for ref,role in members):self.relations.append((r.id,members,tags))

reader=osmium.io.Reader(str(FILE));header=reader.header();meta={k:header.get(k) for k in ['osmosis_replication_timestamp','osmosis_replication_sequence_number','generator']};reader.close();print('HEADER',meta,flush=True)
h=Handler();h.apply_file(str(FILE),locations=False)
print('Parsed China file. Buildings',len(h.buildings),'roads',len(h.roads),'candidate building relations',len(h.relations),flush=True)
relation_members=set();relation_incomplete=0
for rid,members,tags in h.relations:
 outer=[h.ways[ref] for ref,role in members if role in ('','outer') and ref in h.ways]
 inner=[h.ways[ref] for ref,role in members if role=='inner' and ref in h.ways]
 if any(ref not in h.ways for ref,role in members):relation_incomplete+=1;continue
 try:
  exterior=unary_union(list(polygonize(unary_union(outer))))
  holes=unary_union(list(polygonize(unary_union(inner)))) if inner else None
  poly=exterior.difference(holes) if holes is not None else exterior
  if not poly.is_empty and poly.geom_type in ('Polygon','MultiPolygon') and city.intersects(poly):
   h.buildings.append({'id':'r'+str(rid),'geometry':poly.wkb,'tags_json':json.dumps(tags,ensure_ascii=False),'osm_type':'relation'})
   relation_members.update('w'+str(ref) for ref,role in members if role in ('','outer'))
 except Exception as e:print('relation_error',rid,str(e),flush=True)
h.buildings=[x for x in h.buildings if x['id'] not in relation_members]
for name,rows in [('buildings-shanghai',h.buildings),('roads-shanghai',h.roads)]:
 table=pa.Table.from_pylist(rows);pq.write_table(table,OUT/(name+'.parquet'),compression='zstd')
 print(name,len(rows),'bytes',(OUT/(name+'.parquet')).stat().st_size,flush=True)
manifest={'source':'Geofabrik OpenStreetMap China extract','source_url':'https://download.geofabrik.de/asia/china-latest.osm.pbf','header':meta,'acquired_pbf_bytes':FILE.stat().st_size,'source_md5':hashlib.file_digest(open(FILE,'rb'),'md5').hexdigest(),'buildings':len(h.buildings),'roads':len(h.roads),'bounded_node_count':len(h.locations),'incomplete_bbox_ways_skipped':h.incomplete,'incomplete_building_relations':relation_incomplete,'member_building_duplicates_removed':len(relation_members),'selection':'complete features intersecting Shanghai municipality; bounded node lookup bbox padded by 0.03 degrees','elapsed_s':round(time.time()-start,1)}
json.dump(manifest,open(ROOT/'evidence/geofabrik-extract-manifest.json','w'),ensure_ascii=False,indent=2)
print('DONE',json.dumps(manifest),flush=True)
