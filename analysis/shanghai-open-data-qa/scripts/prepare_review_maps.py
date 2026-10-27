import json,csv
from pathlib import Path
import shapely
from shapely.geometry import shape,box
from pyproj import Transformer
ROOT=Path(__file__).resolve().parents[1]
P=Transformer.from_crs(4326,32651,always_xy=True);INV=Transformer.from_crs(32651,4326,always_xy=True)
def project(g):return shapely.transform(g,P.transform,interleaved=False)
def path_lines(g):
 if g.is_empty:return []
 if g.geom_type=='Polygon':return[list(g.exterior.coords)]+[list(x.coords) for x in g.interiors]
 if g.geom_type in ('LineString','LinearRing'):return[list(g.coords)]
 if hasattr(g,'geoms'):return [p for x in g.geoms for p in path_lines(x)]
 return []
def svg_paths(g,cx,cy):
 return [' '.join(('M' if i==0 else 'L')+f'{(x-cx+150)*2:.2f},{(cy+100-y)*2:.2f}' for i,(x,y) in enumerate(line)) for line in path_lines(g)]
byarea={};aoi_names={'陆家嘴':'lujiazui','南京西路':'nanjing-west','新天地':'xintiandi','虹桥':'hongqiao'}
for name,aid in aoi_names.items():
 for kind in ['building','road']:
  feats=json.load(open(ROOT/'results'/f'{kind}-overlay-{aid}.geojson'))['features']
  byarea[(name,kind)]=[(f['properties'],project(shape(f['geometry']))) for f in feats]
miss=list(csv.DictReader(open(ROOT/'results/building-audit-candidates.csv')))
history={r['osm_id']:r for r in json.load(open(ROOT/'results/building-candidate-osm-history.json'))}
rows=[]
for r in miss:
 fs=byarea[(r['area'],'building')];target=next(g for props,g in fs if props['source']=='Geofabrik' and props['id']==r['osm_id']);c=target.centroid;clip=box(c.x-150,c.y-100,c.x+150,c.y+100);shapes=[]
 for props,g in fs:
  if not g.intersects(clip):continue
  shapes.append({'id':props['id'],'source':props['source'],'target':props['id']==r['osm_id'] and props['source']=='Geofabrik','paths':svg_paths(g.intersection(clip),c.x,c.y)})
 ll=INV.transform(c.x,c.y);h=history[r['osm_id']]
 rows.append({'case_id':'building-'+r['osm_id'],'area':r['area'],'type':'建筑参考差异','label':r['area']+' · '+r['osm_id'],'source_id':r['osm_id'],'longitude':ll[0],'latitude':ll[1],'detail':f'最高IoU {float(r["iou"]):.3f}，未达0.5。OSM首次制图/修改：{h["last_modified_utc"]}，version={h["version"]}。'+(' 该对象标注layer=4与level=3，可能是楼上构筑物，应先检查building与building:part语义。' if h['tags'].get('layer')=='4' else ' 仅列为参考差异，未据此认定真实漏建。'),'shapes_json':json.dumps(shapes,ensure_ascii=False,separators=(',',':'))})
points=json.load(open(ROOT/'results/road-topology-candidates.geojson'))['features']
pair_rows=list(csv.DictReader(open(ROOT/'results/building-matched-pairs.csv')))
for area in aoi_names:
 candidates=[r for r in pair_rows if r['area']==area]
 r=max(candidates,key=lambda x:float(x['hausdorff_m']))
 if float(r['hausdorff_m'])<1:continue
 fs=byarea[(area,'building')];target=next(g for p,g in fs if p['source']=='Geofabrik' and p['id']==r['osm_id']);c=target.centroid;clip=box(c.x-150,c.y-100,c.x+150,c.y+100);shapes=[]
 for props,g in fs:
  if g.intersects(clip):shapes.append({'id':props['id'],'source':props['source'],'target':props['id'] in (r['osm_id'],r['overture_id']),'paths':svg_paths(g.intersection(clip),c.x,c.y)})
 ll=INV.transform(c.x,c.y)
 rows.append({'case_id':'geometry-'+r['osm_id'],'area':area,'type':'建筑几何差异','label':area+' · 最大边界差异 '+r['osm_id'],'source_id':r['osm_id'],'longitude':ll[0],'latitude':ll[1],'detail':f'匹配IoU {float(r["iou"]):.6f}；质心差异 {float(r["centroid_distance_m"]):.3f} m；Hausdorff边界差异 {float(r["hausdorff_m"]):.3f} m。共享OSM来源，相对几何差异不代表绝对精度。','shapes_json':json.dumps(shapes,ensure_ascii=False,separators=(',',':'))})
for i,f in enumerate(x for x in points if x['properties']['source']=='Overture'):
 p=f['properties'];c=project(shape(f['geometry']));clip=box(c.x-150,c.y-100,c.x+150,c.y+100);shapes=[]
 for props,g in byarea[(p['area'],'road')]:
  if g.intersects(clip):shapes.append({'id':props['id'],'source':props['source'],'target':False,'paths':svg_paths(g.intersection(clip),c.x,c.y)})
 ll=INV.transform(c.x,c.y)
 rows.append({'case_id':'road-'+str(i+1),'area':p['area'],'type':'道路近接候选','label':p['area']+' · 道路近接点 '+str(i+1),'source_id':p['id'],'longitude':ll[0],'latitude':ll[1],'detail':f'原生度1节点距另一同层道路 {p["distance_m"]:.3f} m；两个数据源均出现，需核查入口、门禁、真实通行及层级，不能自动吸附。','shapes_json':json.dumps(shapes,ensure_ascii=False,separators=(',',':'))})
json.dump(rows,open(ROOT/'results/review-map-rows.json','w'),ensure_ascii=False,indent=2)
# Retain only fields needed for geometric and temporal QA; no contact metadata.
for r in history.values():
 r.pop('changeset',None);r['tags']={k:v for k,v in r['tags'].items() if k in ['name','building','building:levels','layer','level','level:ref','addr:floor']}
json.dump(list(history.values()),open(ROOT/'results/building-candidate-osm-history.json','w'),ensure_ascii=False,indent=2)
print('Prepared',len(rows),'geographic comparison cases')
