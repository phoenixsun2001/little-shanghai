import json,csv,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bs=json.load(open(ROOT/'results/building-metrics.json'));rs=json.load(open(ROOT/'results/road-metrics.json'));prof=json.load(open(ROOT/'results/overture-global-profile.json'));gf=json.load(open(ROOT/'evidence/geofabrik-extract-manifest.json'));ms=json.load(open(ROOT/'evidence/microsoft-coverage-audit.json'))
basefiles=['results/building-metrics.json','results/building-matched-pairs.csv','results/road-metrics.json','evidence/analysis-config.json']
links=[{'label':'Overture 官方下载文档','url':'https://docs.overturemaps.org/getting-data/'},{'label':'Geofabrik 中国数据','url':'https://download.geofabrik.de/asia/china.html'},{'label':'Microsoft 官方数据与覆盖说明','url':'https://github.com/microsoft/GlobalMLBuildingFootprints'},{'label':'东亚建筑数据原始记录','url':'https://doi.org/10.5281/zenodo.8174931'}]
source={'provider':'Official public geospatial downloads','label':'上海开放地图验证 · 固定版本与本地复算','files':basefiles,'links':links,'evidenceFlow':[{'title':'固定源版本与空间范围','detail':'Overture 2026-10-21.0；Geofabrik OSM PBF 截至 2026-10-25T21:21:21Z；Microsoft 2026-08-13 全索引空间覆盖核查。先 bbox 查询，再按上海16区 WGS84 市界几何相交筛选。'},{'title':'对照计算','detail':'scripts/metrics_buildings.py 与 scripts/metrics_roads.py；UTM51N 米制；建筑面积>=10m²，质心位于测试区内缩5m；IoU>=0.5 一对一匹配。道路原生ID建立无向图，测试区外80m提供连通上下文，区内缩30m开展断点/交叉检查。'},{'title':'解释边界','detail':'OSM 是对照数据而非真值；几何匹配对子共享OSM上游。Microsoft上海无分区，完整率及误差N/A；未验证绝对位置精度、真实世界建筑完整率或车辆通行限制。'}]}
def query(rows,label,files,definitions=[]):return {'rows':rows,'source':{**source,'label':label,'files':files,'metricDefinitions':definitions}}
brows=[]
for b in bs:
 brows.append({'area':b['area'],'overture':b['overture_buildings'],'osm':b['osm_reference_buildings'],'matched':b['osm_ref_matched'],'unmatched':b['osm_ref_unmatched'],'reference_match_percent':b['reference_match_rate']*100,'reference_area_percent':b['reference_area_coverage']*100,'eab':b['overture_geometry_source_features'].get('doi:10.5281/zenodo.8174931',0),'shared_osm_matches':b['shared_osm_matches'],'centroid_p95_m':b['centroid_p95_m'],'centroid_max_m':b['centroid_max_m'],'hausdorff_max_m':b['hausdorff_max_m'],'boundary_p95_m':b['boundary_distance_p95_m'],'area_km2':b['area_km2'],'iou_median':b['iou_median'],'independent_matched_pairs':b['non_osm_source_matches']})
rrows=[]
for r in rs:
 rrows.append({'area':r['area'],'source':r['source'],'road_km':r['road_length_km'],'road_features':r['road_features_intersecting_aoi'],'lcc_percent':r['lcc_length_share']*100,'components':r['components_with_length_in_aoi'],'deadends':r['interior_degree1_nodes'],'near_miss_candidates':r['near_miss_candidates_3m'],'unconnected_crossings':r['same_grade_unconnected_crossing_candidates'],'grade_excluded':r['grade_separated_crossings_excluded'],'connector_offline':r.get('connector_off_line_over_1m',0),'missing_connectors':r.get('missing_connector_references',0),'ref_5m_percent':r.get('osm_reference_length_covered_within_5m',None)*100 if r.get('osm_reference_length_covered_within_5m') is not None else None})
manifest_rows=[]
for typ,zh in [('building','建筑'),('segment','交通线要素'),('connector','连接点')]:
 m=json.load(open(ROOT/'data/overture'/f'{typ}-shanghai-2026-10-21.0.manifest.json'))
 manifest_rows.append({'source':'Overture','type':zh,'release':'2026-10-21.0','count':m['municipality_rows'],'sha256':m['sha256'],'size_mb':m['bytes']/1e6})
manifest_rows += [{'source':'Geofabrik','type':'建筑','release':'2026-10-25T21:21:21Z','count':gf['buildings'],'sha256':None,'size_mb':None},{'source':'Geofabrik','type':'highway线要素','release':'2026-10-25T21:21:21Z','count':gf['roads'],'sha256':None,'size_mb':None},{'source':'Microsoft','type':'上海相交下载分区','release':'2026-08-13 官方索引','count':len(ms['intersecting_partitions']),'sha256':ms['index_sha256'],'size_mb':None}]
queries={
 'building_results':query(brows,'建筑对照覆盖及几何差异',basefiles[:2],[{'label':'OSM参考匹配覆盖率','definition':'OSM参考建筑中，与一条Overture建筑达成IoU>=0.5的一对一匹配的数量/有效OSM参考数量；不是现实世界完整率。','formula':'matched / osm * 100','componentIds':['building-counts','building-table','building-coverage']},{'label':'几何差异（米）','definition':'同一匹配对的质心距离、对称边界抽样距离与Hausdorff距离；共享OSM来源导致多数相同，不代表独立绝对精度。','componentIds':['geometry-table','geometry-maximum']}]),
 'road_results':query(rrows,'统一机动车范围后的原生路网拓扑',['results/road-metrics.json','results/road-audit-candidates.csv','scripts/metrics_roads.py'],[{'label':'最大连通分量长度占比','definition':'测试框内原生无向道路图的最长连通分量所含道路长度/全部图道路长度。使用80m外部缓冲，不验证单行线、转向或通行权限。','componentIds':['road-connectivity','road-table']},{'label':'近接断点候选','definition':'区内距边界>30m的原生度1节点，在3m内存在另一同层道路且未共享原生连接ID；是待核查候选，不是已证实错误。','componentIds':['road-table','road-candidates']}]),
 'sources':query(manifest_rows,'下载范围与校验清单',['data/overture/*.manifest.json','evidence/geofabrik-extract-manifest.json','evidence/microsoft-coverage-audit.json']),
 'source_composition':query([{'source':'东亚建筑提取数据','count':1641438},{'source':'OpenStreetMap','count':152392}],'Overture上海建筑几何来源',['results/overture-global-profile.json']),
 'building_candidates':query(list(csv.DictReader(open(ROOT/'results/building-audit-candidates.csv'))),f'未达IoU0.5的{sum(b["osm_ref_unmatched"] for b in bs)}个参考对象',['results/building-audit-candidates.csv','results/building-candidate-osm-history.json']),
 'road_candidates':query(list(csv.DictReader(open(ROOT/'results/road-audit-candidates.csv'))),'3个空间近接点、两个数据源各有记录',['results/road-audit-candidates.csv','results/road-topology-candidates.geojson'])}
queries['review_maps']=query(json.load(open(ROOT/'results/review-map-rows.json')),'5个建筑参考差异、2个最大几何差异及3个道路近接点',['results/building-matched-pairs.csv','results/building-candidate-osm-history.json','results/road-topology-candidates.geojson','results/review-map-rows.json'])
queries['review_maps']['payloadColumn']='shapes_json'
snapshot={'surface':'report','title':'上海开放地图：覆盖增补与质量验证','generatedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'status':'complete','filters':[],'exportPreferences':{'selected':None,'destinations':[]},'queries':queries}
json.dump(snapshot,open(ROOT/'results/reviewed-snapshot.json','w'),ensure_ascii=False,indent=2)
print('Saved reviewed snapshot',sum(len(q['rows']) for q in queries.values()),'rows')
