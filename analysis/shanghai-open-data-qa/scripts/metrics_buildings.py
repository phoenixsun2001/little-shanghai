"""Reference-relative building matching, not absolute completeness/accuracy."""
import json,csv,collections,re
from pathlib import Path
import numpy as np,pyarrow.parquet as pq,shapely
from shapely.geometry import box,mapping
from pyproj import Transformer
ROOT=Path(__file__).resolve().parents[1];CFG=json.load(open(ROOT/'evidence/analysis-config.json'))
FWD=Transformer.from_crs('EPSG:4326',CFG['metric_crs'],always_xy=True);INV=Transformer.from_crs(CFG['metric_crs'],'EPSG:4326',always_xy=True)
def proj(g):return shapely.transform(g,FWD.transform,interleaved=False)
def unproj(g):return shapely.transform(g,INV.transform,interleaved=False)
def write_csv(path,rows):
 if not rows:return
 with open(path,'w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def quantile(x,q):return float(np.quantile(x,q)) if len(x) else None
def sources(row):return sorted({s['dataset'] for s in row.get('sources') or [] if s.get('property') in ('','geometry',None)})
def load(path):
 rows=pq.read_table(path).to_pylist();gg=proj(shapely.from_wkb([r.pop('geometry') for r in rows]));return rows,gg
osm_rows,osm_geo=load(ROOT/'data/geofabrik/buildings-shanghai.parquet');out=[];cases=[];pair_rows=[];audit_rows=[]
for a in CFG['areas']:
 region=proj(shapely.geometry.shape(a['geometry']) if a.get('geometry') else box(*a['bbox']));inner=region.buffer(-5);buffer=region.buffer(100)
 ov_rows,ov=load(ROOT/'data/aoi'/f'overture-building-{a["id"]}.parquet')
 keep=shapely.intersects(osm_geo,buffer);osr=[r for r,k in zip(osm_rows,keep) if k];osg=osm_geo[keep]
 def eligible(rows,g):
  valid=shapely.is_valid(g)&(~shapely.is_empty(g));poly=np.isin(shapely.get_type_id(g),[3,6]);area=shapely.area(g);good=valid&poly&(area>=10)
  core=shapely.contains(inner,shapely.centroid(g))
  stats={'raw_core':int(core.sum()),'invalid_core':int((core&~valid).sum()),'small_core':int((core&(area<10)).sum()),'nonpolygon_core':int((core&~poly).sum())}
  return [r for r,k in zip(rows,good) if k],g[good],stats
 ov_rows,ov,ovstats=eligible(ov_rows,ov);osr,osg,osstats=eligible(osr,osg)
 ovcore=shapely.contains(inner,shapely.centroid(ov));oscore=shapely.contains(inner,shapely.centroid(osg))
 tree=shapely.STRtree(ov);idx=tree.query(osg,predicate='intersects');candidates=[]
 if idx.shape[1]:
  inter=shapely.area(shapely.intersection(osg[idx[0]],ov[idx[1]]));union=shapely.area(osg[idx[0]])+shapely.area(ov[idx[1]])-inter;ious=inter/union
  candidates=sorted([(float(v),int(i),int(j)) for v,i,j in zip(ious,idx[0],idx[1]) if v>0],reverse=True)
 def match(threshold):
  rr=set();oo=set();selected=[]
  for iou,i,j in candidates:
   if iou<threshold:break
   if i not in rr and j not in oo:rr.add(i);oo.add(j);selected.append((iou,i,j))
  return rr,oo,selected
 rr,oo,matched=match(.5);core_pairs=[(v,i,j) for v,i,j in matched if oscore[i]]
 displacements=[];haus=[];assd=[];ious=[];independent=[]
 for v,i,j in core_pairs:
  r=osg[i];o=ov[j];d=float(r.centroid.distance(o.centroid));h=float(shapely.hausdorff_distance(r.boundary,o.boundary,densify=.25))
  # Symmetric boundary-sample distance: sample at <=1m along all rings.
  rb=shapely.segmentize(r.boundary,1);ob=shapely.segmentize(o.boundary,1)
  rp=shapely.points(shapely.get_coordinates(rb));op=shapely.points(shapely.get_coordinates(ob))
  sd=float((np.sum(shapely.distance(rp,o.boundary))+np.sum(shapely.distance(op,r.boundary)))/(len(rp)+len(op)))
  ss=sources(ov_rows[j]);shared='OpenStreetMap' in ss
  displacements.append(d);haus.append(h);assd.append(sd);ious.append(v)
  if not shared:independent.append((v,d,h,sd))
  pair_rows.append({'area':a['name'],'overture_id':ov_rows[j]['id'],'osm_id':osr[i]['id'],'iou':v,'centroid_distance_m':d,'hausdorff_m':h,'symmetric_boundary_distance_m':sd,'overture_geometry_sources':' | '.join(ss),'shares_osm_geometry_source':shared})
  if d>2 or v<.75:audit_rows.append({'area':a['name'],'issue':'matched_geometry_difference','overture_id':ov_rows[j]['id'],'osm_id':osr[i]['id'],'iou':v,'centroid_distance_m':d})
 ov_union=shapely.union_all(ov);ref_union=shapely.union_all(osg[oscore]);ref_area=float(ref_union.area);covered_area=float(ref_union.intersection(ov_union).area)
 sensitivity={}
 for threshold in [.25,.5,.75]:
  rset,oset,_=match(threshold);sensitivity[str(threshold)]=sum(bool(oscore[i]) for i in rset)/int(oscore.sum()) if oscore.sum() else None
 unmatched=[i for i in np.where(oscore)[0] if i not in rr]
 for i in unmatched:
  audit_rows.append({'area':a['name'],'issue':'osm_reference_without_iou05_match','overture_id':'','osm_id':osr[i]['id'],'iou':max((v for v,k,j in candidates if k==i),default=0),'centroid_distance_m':None})
 result={'area_id':a['id'],'area':a['name'],'bbox':a['bbox'],'area_km2':float(region.area/1e6),'overture_raw':ovstats,'osm_raw':osstats,'overture_buildings':int(ovcore.sum()),'osm_reference_buildings':int(oscore.sum()),'osm_ref_matched':len(core_pairs),'osm_ref_unmatched':len(unmatched),'reference_match_rate':len(core_pairs)/int(oscore.sum()) if oscore.sum() else None,'reference_area_coverage':covered_area/ref_area if ref_area else None,'reference_area_m2':ref_area,'reference_area_covered_m2':covered_area,'overture_supported_by_osm':sum(bool(ovcore[j]) for j in oo),'iou_median':quantile(ious,.5),'iou_p05':quantile(ious,.05),'centroid_median_m':quantile(displacements,.5),'centroid_p95_m':quantile(displacements,.95),'centroid_max_m':max(displacements,default=None),'hausdorff_max_m':max(haus,default=None),'boundary_max_m':max(assd,default=None),'relative_difference_above_1mm_pairs':sum(h>.001 for h in haus),'hausdorff_median_m':quantile(haus,.5),'hausdorff_p95_m':quantile(haus,.95),'boundary_distance_median_m':quantile(assd,.5),'boundary_distance_p95_m':quantile(assd,.95),'shared_osm_matches':len(core_pairs)-len(independent),'non_osm_source_matches':len(independent),'non_osm_iou_median':quantile([r[0] for r in independent],.5),'non_osm_centroid_median_m':quantile([r[1] for r in independent],.5),'non_osm_centroid_p95_m':quantile([r[1] for r in independent],.95),'non_osm_boundary_p95_m':quantile([r[3] for r in independent],.95),'sensitivity_iou_match_rate':sensitivity,'overture_geometry_source_features':dict(collections.Counter(' | '.join(sources(r)) for r,k in zip(ov_rows,ovcore) if k)),'absolute_completeness':None,'absolute_horizontal_accuracy':None}
 out.append(result);print(json.dumps(result,ensure_ascii=False),flush=True)
 # Save portable full-AOI geometries with source and matching status for review.
 feats=[]
 for label,rows,geoms,core,seen in [('Overture',ov_rows,ov,ovcore,oo),('Geofabrik',osr,osg,oscore,rr)]:
  for i in np.where(core)[0]:
   feats.append({'type':'Feature','properties':{'source':label,'id':rows[i]['id'],'matched_iou05':i in seen,'geometry_sources':' | '.join(sources(rows[i])) if label=='Overture' else 'OpenStreetMap'},'geometry':mapping(unproj(geoms[i]))})
 json.dump({'type':'FeatureCollection','features':feats},open(ROOT/'results'/f'building-overlay-{a["id"]}.geojson','w'),ensure_ascii=False,separators=(',',':'))
 # Deterministic cases: missing refs, lowest IoU, and non-OSM matched differences.
 selected=[]
 for i in unmatched[:3]:selected.append(('unmatched_reference',None,i,None))
 for v,i,j in sorted(core_pairs)[:3]:selected.append(('low_iou_match',v,i,j))
 for v,i,j in sorted(core_pairs,key=lambda q:osg[q[1]].centroid.distance(ov[q[2]].centroid),reverse=True)[:2]:selected.append(('largest_relative_shift',v,i,j))
 for typ,v,i,j in selected:
  props={'area':a['name'],'area_id':a['id'],'case_type':typ,'osm_id':osr[i]['id'],'overture_id':ov_rows[j]['id'] if j is not None else None,'iou':v}
  cases.append({'type':'Feature','properties':{**props,'source':'Geofabrik'},'geometry':mapping(unproj(osg[i]))})
  if j is not None:cases.append({'type':'Feature','properties':{**props,'source':'Overture'},'geometry':mapping(unproj(ov[j]))})
json.dump(out,open(ROOT/'results/building-metrics.json','w'),ensure_ascii=False,indent=2)
write_csv(ROOT/'results/building-matched-pairs.csv',pair_rows);write_csv(ROOT/'results/building-audit-candidates.csv',audit_rows)
json.dump({'type':'FeatureCollection','features':cases},open(ROOT/'results/building-review-cases.geojson','w'),ensure_ascii=False,separators=(',',':'))
