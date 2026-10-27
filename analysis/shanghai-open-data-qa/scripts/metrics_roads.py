"""Native-ID undirected topology, grade-aware planar candidates, relative coverage.
These are QA candidates, not verified routing or traffic restriction correctness.
"""
import json,csv,collections,math
from pathlib import Path
import numpy as np,pyarrow.parquet as pq,shapely,networkx as nx
from shapely.geometry import box,Point,mapping
from shapely.ops import substring
from pyproj import Transformer
ROOT=Path(__file__).resolve().parents[1];CFG=json.load(open(ROOT/'evidence/analysis-config.json'))
FWD=Transformer.from_crs(4326,32651,always_xy=True);INV=Transformer.from_crs(32651,4326,always_xy=True)
def proj(g):return shapely.transform(g,FWD.transform,interleaved=False)
def unproj(g):return shapely.transform(g,INV.transform,interleaved=False)
def load(path):
 rows=pq.read_table(path).to_pylist();g=proj(shapely.from_wkb([r.pop('geometry') for r in rows]));return rows,g
ALLOWED={'motorway','trunk','primary','secondary','tertiary','residential','living_street','unclassified','service','track','road','unknown'}
MAJOR={'motorway','trunk','primary','secondary','tertiary','residential','living_street','unclassified','road','unknown'}
def yes(v):return v in ('yes','true','1','viaduct','building_passage')
def rule_at(rules,at,default=None):
 value=default
 for rule in rules or []:
  interval=rule.get('between')
  if interval is None or interval[0]-1e-6<=at<=interval[1]+1e-6:value=rule.get('value',value)
 return value

def grade(rec,point):
 at=rec['geom'].project(point,normalized=True) if rec['geom'].length else 0
 if rec['source']=='Geofabrik':
  t=rec['tags'];layer=t.get('layer','0')
  try:level=int(float(layer))
  except ValueError:level=0
  return level,yes(t.get('bridge')),yes(t.get('tunnel'))
 row=rec['row'];level=rule_at(row.get('level_rules'),at,0);flags=set()
 for rule in row.get('road_flags') or []:
  interval=rule.get('between')
  if interval is None or interval[0]-1e-6<=at<=interval[1]+1e-6:flags.update(rule.get('values') or [])
 return level,'is_bridge' in flags,'is_tunnel' in flags

def separated(a,b,p):return grade(a,p)!=grade(b,p)

def road_records(rows,geoms,source,context):
 recs=[];invalid=0
 for row,g in zip(rows,geoms):
  if source=='Overture':
   if row['subtype']!='road':continue
   cls=row['class'] or 'unknown';tags={}
   if any('is_under_construction' in (x.get('values') or []) for x in row.get('road_flags') or []):continue
  else:
   tags=json.loads(row['tags_json']);cls=tags.get('highway','');cls=cls.removesuffix('_link')
  if cls not in ALLOWED or not g.intersects(context):continue
  if g.geom_type!='LineString' or not g.is_valid or g.is_empty or g.length<=0:invalid+=1;continue
  recs.append({'id':row['id'],'row':row,'geom':g,'source':source,'class':cls,'tags':tags,'native_nodes':set()})
 return recs,invalid

osm_rows,osm_geo=load(ROOT/'data/geofabrik/roads-shanghai.parquet')
ct=pq.read_table(ROOT/'data/overture/connector-shanghai-2026-10-21.0.parquet',columns=['id','geometry'])
cg=proj(shapely.from_wkb(ct['geometry'].to_numpy(zero_copy_only=False)));connectors=dict(zip(ct['id'].to_pylist(),cg))
allmetrics=[];issues=[];features=[]
def make_network(recs,source):
 graph=nx.MultiGraph();coords={};incident=collections.defaultdict(set);stats=collections.Counter();usage=collections.Counter()
 if source=='Geofabrik':
  for r in recs:
   r['refs']=json.loads(r['row']['nodes_json']);r['xy']=np.asarray(r['geom'].coords)
   usage.update(set(r['refs']));usage[r['refs'][0]]+=1;usage[r['refs'][-1]]+=1
 for r in recs:
  g=r['geom'];anchors=[]
  if source=='Overture':
   conns=sorted(r['row'].get('connectors') or [],key=lambda x:x['at']);prev=-1
   if len(conns)<2:stats['segments_without_two_connectors']+=1
   if not conns or abs(conns[0]['at'])>1e-8 or abs(conns[-1]['at']-1)>1e-8:stats['segments_missing_endpoint_anchor']+=1
   for conn in conns:
    nid=conn['connector_id'];at=conn['at'];r['native_nodes'].add(nid)
    if not 0<=at<=1:stats['invalid_linear_reference']+=1;continue
    if nid not in connectors:stats['missing_connector_references']+=1;continue
    p=connectors[nid];dist=p.distance(g)
    if dist>1:stats['connector_off_line_over_1m']+=1
    t=0. if at==0 else 1. if at==1 else g.project(p,normalized=True)
    if t<prev-1e-8:stats['nonmonotonic_projection']+=1;t=at
    prev=t;anchors.append((nid,t,p));coords[nid]=p;incident[nid].add(r['id'])
  else:
   xy=r['xy'];lens=np.r_[0,np.cumsum(np.linalg.norm(np.diff(xy,axis=0),axis=1))];total=lens[-1]
   for i,n in enumerate(r['refs']):
    r['native_nodes'].add(str(n));coords[str(n)]=Point(xy[i]);incident[str(n)].add(r['id'])
    if i in (0,len(r['refs'])-1) or usage[n]>1:anchors.append((str(n),float(lens[i]/total),Point(xy[i])))
  for (n1,t1,p1),(n2,t2,p2) in zip(anchors,anchors[1:]):
   if t2-t1<=1e-10:stats['zero_length_anchor_intervals']+=1;continue
   line=substring(g,t1,t2,normalized=True)
   graph.add_edge(n1,n2,length=line.length,geometry=line,road_id=r['id'],road_class=r['class'])
  for nid,t,p in anchors:graph.add_node(nid)
 return graph,coords,incident,dict(stats)

def analyse(a,source,recs,region,inner):
 graph,coords,incident,stats=make_network(recs,source);components=list(nx.connected_components(graph));membership={n:i for i,c in enumerate(components) for n in c};lengths=collections.Counter();major_lengths=collections.Counter()
 for u,v,k,e in graph.edges(keys=True,data=True):
  length=e['geometry'].intersection(region).length
  if length:
   lengths[membership[u]]+=length
   if e['road_class'] in MAJOR:major_lengths[membership[u]]+=length
 total=sum(lengths.values());lcc=max(lengths.values(),default=0);major_total=sum(major_lengths.values());major_lcc=max(major_lengths.values(),default=0)
 interior=[n for n in graph if n in coords and inner.contains(coords[n])];dead=[n for n in interior if graph.degree(n)==1]
 geoms=[r['geom'] for r in recs];tree=shapely.STRtree(geoms);near=[];cross=[];grade_excluded=0;cross_pairs=0
 for nid in dead:
  p=coords[nid];cands=tree.query(p,predicate='dwithin',distance=3);best=None
  native_records=[r for r in recs if r['id'] in incident[nid]]
  for j in cands:
   r=recs[int(j)]
   if r['id'] in incident[nid] or nid in r['native_nodes']:continue
   if any(separated(nr,r,p) for nr in native_records):continue
   distance=float(p.distance(r['geom']))
   if best is None or distance<best[0]:best=(distance,r)
  if best:
   distance,r=best;near.append((nid,p,distance,r['id']))
   issues.append({'area':a['name'],'source':source,'issue':'interior_deadend_near_other_road_within_3m','feature_id':nid,'other_id':r['id'],'distance_m':distance,'status':'candidate_manual_review'})
   features.append({'type':'Feature','properties':{'area':a['name'],'source':source,'issue':'near_miss_candidate','id':nid,'distance_m':distance,'other_id':r['id']},'geometry':mapping(unproj(p))})
 pairs=tree.query(geoms,predicate='intersects')
 for i,j in zip(*pairs):
  if j<=i:continue
  r1,r2=recs[int(i)],recs[int(j)];intersection=r1['geom'].intersection(r2['geom'])
  points=[intersection] if intersection.geom_type=='Point' else list(intersection.geoms) if intersection.geom_type=='MultiPoint' else []
  for p in points:
   if not inner.contains(p):continue
   cross_pairs+=1
   common=r1['native_nodes']&r2['native_nodes']
   if any(n in coords and coords[n].distance(p)<=1 for n in common):continue
   if separated(r1,r2,p):grade_excluded+=1;continue
   cross.append((r1['id'],r2['id'],p));issues.append({'area':a['name'],'source':source,'issue':'same_grade_planar_crossing_without_shared_native_node','feature_id':r1['id'],'other_id':r2['id'],'distance_m':0,'status':'candidate_grade_and_access_manual_review'})
   features.append({'type':'Feature','properties':{'area':a['name'],'source':source,'issue':'unconnected_crossing_candidate','id':r1['id'],'other_id':r2['id']},'geometry':mapping(unproj(p))})
 core=[r for r in recs if r['geom'].intersects(region)]
 return {'area_id':a['id'],'area':a['name'],'source':source,'road_features_intersecting_aoi':len(core),'road_length_km':sum(r['geom'].intersection(region).length for r in core)/1000,'native_nodes_in_aoi':sum(region.contains(p) for n,p in coords.items() if n in graph),'graph_edges_in_aoi':sum(e['geometry'].intersects(region) for u,v,k,e in graph.edges(keys=True,data=True)),'components_with_length_in_aoi':len(lengths),'lcc_length_share':lcc/total if total else None,'major_lcc_length_share':major_lcc/major_total if major_total else None,'major_road_length_km':major_total/1000,'interior_nodes':len(interior),'interior_degree1_nodes':len(dead),'near_miss_candidates_3m':len(near),'same_grade_unconnected_crossing_candidates':len(cross),'planar_crossing_points_checked':cross_pairs,'grade_separated_crossings_excluded':grade_excluded,'short_features_under_1m':sum(r['geom'].length<1 for r in core),'exact_duplicate_geometry_excess':len(core)-len({shapely.normalize(r['geom']).wkb for r in core}),**stats}

for a in CFG['areas']:
 region=proj(shapely.geometry.shape(a['geometry']) if a.get('geometry') else box(*a['bbox']));context=region.buffer(250);inner=region.buffer(-30)
 orows,og=load(ROOT/'data/aoi'/f'overture-segment-{a["id"]}.parquet');over,inv1=road_records(orows,og,'Overture',context);osm,inv2=road_records(osm_rows,osm_geo,'Geofabrik',context)
 # Overture AOI files have 0.001 deg (~100m) acquisition buffer. Apply the same
 # smaller 80m context to both sources rather than silently using unequal context.
 context=region.buffer(80);over=[r for r in over if r['geom'].intersects(context)];osm=[r for r in osm if r['geom'].intersects(context)]
 om=analyse(a,'Overture',over,region,inner);sm=analyse(a,'Geofabrik',osm,region,inner)
 om['invalid_road_geometry_excluded']=inv1;sm['invalid_road_geometry_excluded']=inv2
 ovunion=shapely.union_all([r['geom'] for r in over]);oslines=shapely.union_all([r['geom'].intersection(region) for r in osm]);reference_length=oslines.length
 for buf in [3,5,10]:
  covered=oslines.intersection(ovunion.buffer(buf)).length;om[f'osm_reference_length_covered_within_{buf}m']=covered/reference_length if reference_length else None
  om[f'osm_reference_length_m_{buf}m']=reference_length;om[f'osm_reference_covered_length_m_{buf}m']=covered
 allmetrics.extend([om,sm]);print(json.dumps(om,ensure_ascii=False),flush=True);print(json.dumps(sm,ensure_ascii=False),flush=True)
 feats=[]
 for src,records in [('Overture',over),('Geofabrik',osm)]:
  for r in records:
   if r['geom'].intersects(region):feats.append({'type':'Feature','properties':{'source':src,'id':r['id'],'class':r['class']},'geometry':mapping(unproj(r['geom']))})
 json.dump({'type':'FeatureCollection','features':feats},open(ROOT/'results'/f'road-overlay-{a["id"]}.geojson','w'),ensure_ascii=False,separators=(',',':'))
json.dump(allmetrics,open(ROOT/'results/road-metrics.json','w'),ensure_ascii=False,indent=2)
if issues:
 with open(ROOT/'results/road-audit-candidates.csv','w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(issues[0]));w.writeheader();w.writerows(issues)
json.dump({'type':'FeatureCollection','features':features},open(ROOT/'results/road-topology-candidates.geojson','w'),ensure_ascii=False,separators=(',',':'))
