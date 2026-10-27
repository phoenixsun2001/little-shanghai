import React, {useMemo,useState} from 'react';
import {EvidenceChart,DataComponent,DataTable,ReportSection,RichNarrative,useDataApp} from '../../data-app-public.jsx';
const pct=(v)=>v==null?'N/A':`${v.toFixed(2)}%`;
const meters=(v)=>v==null?'N/A':v<.001?'<0.001':v.toFixed(3);
const previews={
 'https://docs.overturemaps.org/getting-data/':{title:'Overture 官方 Quickstart',summary:'官方提供按空间范围下载 GeoParquet 的路径与示例；本次固定使用2026-10-21.0发布。',source:'Overture Maps',approvedForReport:true},
 'https://download.geofabrik.de/asia/china.html':{title:'Geofabrik 中国 OSM 提取',summary:'提供中国PBF，页面和实际PBF header均指向2026-10-25T21:21:21Z数据截止。上海在本地从中国文件提取。',source:'Geofabrik',approvedForReport:true},
 'https://github.com/microsoft/GlobalMLBuildingFootprints':{title:'Microsoft GlobalMLBuildingFootprints',summary:'官方README指向2026-08-13下载索引。本次对30340条QuadKey逐一核对空间覆盖，未发现与上海相交的可下载分区。',source:'Microsoft',approvedForReport:true},
 'https://doi.org/10.5281/zenodo.8174931':{title:'东亚建筑提取数据',summary:'Zenodo记录覆盖中国等东亚地区，许可为CC BY 4.0；Overture上海大量建筑几何沿用此来源。',source:'Zenodo',approvedForReport:true}
};
function Narrative({id,children}){return <RichNarrative id={id} value={children} sourcePreviews={previews}/>;}
function Table({id,title,queryId,rows,columns}){return <DataComponent id={id} title={title} queryId={queryId} kind="table" displayRows={rows} sourceRows={rows}><DataTable rows={rows} columns={columns} searchable={false} compactNumbers={false} caption={title}/></DataComponent>;}
function ReviewMap({rows}){
 const [selected,setSelected]=useState(rows[0]?.case_id),[hover,setHover]=useState('');
 const row=rows.find(x=>x.case_id===selected)||rows[0];
 const shapes=useMemo(()=>JSON.parse(row?.shapes_json||'[]'),[row]);
 if(!row)return null;
 return <DataComponent id="review-map" title="逐项查看几何差异与近接点" kind="custom" queryId="review_maps" displayRows={[row]} sourceRows={[row]}>
  <div className="qa-map-controls"><label>选择核查对象 <select aria-label="选择核查对象" value={row.case_id} onChange={e=>{setSelected(e.target.value);setHover('');}}>{rows.map(x=><option key={x.case_id} value={x.case_id}>{x.label} · {x.type}</option>)}</select></label></div>
  <div className="qa-map-legend"><span><i className="qa-over-line"/>Overture · 实线</span><span><i className="qa-osm-line"/>Geofabrik · 虚线</span><span>UTM 51N · 北向上 · 300 × 200 m</span></div>
  <div className="qa-review-map" data-reviewed-rows>
   <svg viewBox="0 0 600 400" role="group" aria-label={`${row.label}，真实投影局部对照图`}>
    <rect width="600" height="400" fill="var(--muted)"/>
    {[100,200,300,400,500].map(x=><path key={x} d={`M${x},0V400`} stroke="var(--border)" strokeWidth=".5"/>)}
    {[100,200,300].map(y=><path key={y} d={`M0,${y}H600`} stroke="var(--border)" strokeWidth=".5"/>)}
    {shapes.map((s,i)=><g key={i} tabIndex={0} role="img" aria-label={`${s.source} ${s.id}`} onPointerEnter={()=>setHover(`${s.source} · ${s.id}`)} onPointerLeave={()=>setHover('')} onFocus={()=>setHover(`${s.source} · ${s.id}`)} onBlur={()=>setHover('')}>{s.paths.map((p,j)=><path key={j} d={p} fill={row.type.includes('建筑')?(s.target?'var(--qa-osm)':'none'):'none'} fillOpacity={s.target?.2:1} stroke={s.source==='Overture'?'var(--qa-over)':'var(--qa-osm)'} strokeWidth={s.target?3:1.6} strokeDasharray={s.source==='Geofabrik'?'5 3':undefined} strokeLinejoin="round"/>)}</g>)}
    {row.type.includes('道路')&&<circle cx="300" cy="200" r="9" fill="none" stroke="var(--text)" strokeWidth="2" tabIndex={0} role="img" aria-label="近接断点候选" onFocus={()=>setHover('候选点 · '+row.source_id)} onPointerEnter={()=>setHover('候选点 · '+row.source_id)}/>}
    <g stroke="var(--text)" fill="var(--text)"><path d="M24 366h100m-100-5v10m100-10v10" strokeWidth="2"/><text x="24" y="353" stroke="none" fontSize="12">50 m</text><path d="M564 49V20m-5 10 5-10 5 10" fill="none"/><text x="559" y="66" stroke="none" fontSize="12">N</text></g>
   </svg>
   {hover&&<div className="qa-map-tooltip" role="tooltip">{hover}</div>}
  </div>
  <div className="qa-case-note" data-reviewed-rows><strong>{row.label}</strong><p>{row.detail}</p><small>中心 WGS84：{row.longitude.toFixed(6)}, {row.latitude.toFixed(6)}。底图为实际矢量几何，未把卫星屋顶当作地面测量真值。</small></div>
 </DataComponent>;
}
export function ReportContent(){
 const {reviewedRows,appTitle,canEdit,mode,setAppTitle}=useDataApp();
 const b=reviewedRows('building_results'),r=reviewedRows('road_results'),s=reviewedRows('sources'),cases=reviewedRows('review_maps');
 const ov=r.filter(x=>x.source==='Overture');
 const countRows=b.map(x=>({area:x.area,'Overture':x.overture,'Geofabrik':x.osm}));
 const maxRows=b.map(x=>({area:x.area,'质心差异':x.centroid_max_m,'边界差异':x.hausdorff_max_m}));
 const connected=r.map(x=>({area:x.area,source:x.source,'最大连通分量(%)':x.lcc_percent}));
 return <article className="report-content qa-report" aria-label="上海开放地图质量验证报告">
  <header className="report-hero"><h1 data-data-app-title contentEditable={canEdit&&mode==='edit'} suppressContentEditableWarning onBlur={canEdit&&mode==='edit'?e=>setAppTitle(e.currentTarget.textContent.trim()||appTitle):undefined}>{appTitle}</h1><Narrative id="qa-intro">{'陆家嘴、南京西路、新天地、虹桥交通枢纽＋商务区 · 2026年10月27日验证\n\n结论基于开放数据之间的对照。**参考覆盖率不等于现实世界完整率；同源几何相同不等于独立测量精度。**'}</Narrative></header>
  <ReportSection id="qa-summary" title="验证结论" queryId="building_results" queryIds={['building_results','road_results','sources']} sourceRowsByQuery={{building_results:b,road_results:r,sources:s}} showHeading={false}>
   <Narrative id="qa-summary-body">{'## 验证结论\n\n- **Overture可显著补充建筑密度，但增补部分仍需要独立核验。** 上海全域下载到179.4万条建筑；其中91.50%的几何来自东亚建筑提取数据，8.50%来自OSM。四区的有效建筑数均高于Geofabrik，虹桥最明显。\n- **OSM参考匹配覆盖率为99.87%–100%，但不能据此声称高绝对精度。** 四区共5个参考对象未达到IoU 0.5；全部匹配对子共享OSM几何来源，没有独立匹配样本。5个差异对象的OSM版本均为1，制图时间晚于Overture主要建筑OSM快照。\n- **未发现本测试定义下的同层平面交叉断连，但仍有3个空间近接点待查。** 最大连通分量长度占比99.29%–99.94%；两个南京西路点相距其他道路约1.6–1.7m，虹桥一处约0.016m。它们同时存在于两个来源，不能自动吸附。\n- **Microsoft上海轮廓对照不可用，绝对完整率与绝对几何精度暂不能确认。** 官方全球索引中，与上海相交的下载分区为0；这里的0是可下载分区数，不是“建筑完整率0%”。'}</Narrative>
  </ReportSection>
  <section className="qa-section">
   <ReportSection id="building-reading" title="建筑完整性" queryId="building_results" sourceRows={b} showHeading={false}><Narrative id="building-reading-body">{'## 1. 建筑完整性：保留OSM基底，再核查提取轮廓增补\n\n同一测试范围内，Overture包含更多建筑对象。增量主要来自东亚提取数据；**数量更多并不自动证明这些对象全部真实、分割正确或当前仍然存在**。完整性列采用明确的OSM参考分母，另外提供参考建筑面积覆盖率，减轻一栋分成多块所造成的计数偏差。'}</Narrative></ReportSection>
   <EvidenceChart id="building-counts" title="四区建筑数量" queryId="building_results" rows={countRows} sourceRows={b} spec={{type:'bar',x:'area',y:'Overture',fields:['Overture','Geofabrik'],stackable:false,valueDecimals:0,startAtZero:true,colors:{'Overture':'#4e79a7','Geofabrik':'#b37a15'}}} height={330}/>
   <Table id="building-table" title="OSM参考覆盖率与未匹配数量" queryId="building_results" rows={b} columns={[{field:'area',label:'区域'},{field:'overture',label:'Overture有效建筑'},{field:'osm',label:'OSM参考建筑'},{field:'matched',label:'匹配数'},{field:'unmatched',label:'未达阈值'},{field:'reference_match_percent',label:'对象覆盖率',renderCell:pct},{field:'reference_area_percent',label:'面积覆盖率',renderCell:pct}]}/>
   <Narrative id="building-denominator">{'建筑按质心位于测试框内缩5m、有效面、面积至少10m²纳入；以IoU（交集面积／并集面积）≥0.5进行一对一匹配。阈值改为0.25时，南京西路匹配数由3112变为3114；其他区域不变。阈值0.75与0.5结果一致。\n\n“5个未达阈值对象”不等于5栋真实漏建。它们均在2026年10月首次纳入OSM，晚于Overture的主要OSM快照；仍要区分新增制图、部件语义、分割差异与真正漏画。'}</Narrative>
  </section>
  <section className="qa-section">
   <ReportSection id="geometry-reading" title="几何差异" queryId="building_results" sourceRows={b} showHeading={false}><Narrative id="geometry-reading-body">{'## 2. 几何误差：可量化相对差异，独立绝对精度仍缺基准\n\n已对匹配建筑计算UTM 51N米制下的质心距离、Hausdorff边界距离，以及间隔不超过1m的对称边界抽样距离。四区质心差异P95和对称边界距离P95均低于0.001m，这是**共享OSM轮廓几何几乎相同**的结果，不应解释为毫米级测绘精度。\n\n最大差异揭示了少量轮廓变化：陆家嘴最大Hausdorff边界差异12.658m，但该区最大质心差异仅约0.001m；边界最大距离与整体位置偏移衡量的含义不同。南京西路最大质心与边界差异均约1.569m；虹桥最大边界差异约0.036m。最大值与多数对象几乎一致可以同时成立。'}</Narrative></ReportSection>
   <EvidenceChart id="geometry-maximum" title="最大几何差异（米）" queryId="building_results" rows={maxRows} sourceRows={b} spec={{type:'bar',x:'area',y:'质心差异',fields:['质心差异','边界差异'],colors:{'质心差异':'#4e79a7','边界差异':'#b37a15'},valueDecimals:3,stackable:false,startAtZero:true}} height={320}/>
   <Table id="geometry-table" title="几何差异与独立匹配样本数" queryId="building_results" rows={b} columns={[{field:'area',label:'区域'},{field:'matched',label:'匹配对子'},{field:'shared_osm_matches',label:'共享OSM几何'},{field:'centroid_p95_m',label:'质心P95(m)',renderCell:meters},{field:'centroid_max_m',label:'质心最大(m)',renderCell:meters},{field:'hausdorff_max_m',label:'边界最大(m)',renderCell:meters},{field:'independent_matched_pairs',label:'独立匹配对子'}]}/>
   <Narrative id="geometry-limit">{'本次没有获得独立、可追溯精度的上海建筑真值，也没有可用的Microsoft上海轮廓。由此，**真实建筑完整率、独立水平位置误差、RMSE与CE90不作数值结论**。卫星屋顶还可能受拍摄时间、倾斜与高楼视差影响，不能直接代替地面轮廓真值。'}</Narrative>
  </section>
  <section className="qa-section">
   <ReportSection id="road-reading" title="道路拓扑" queryId="road_results" sourceRows={r} showHeading={false}><Narrative id="road-reading-body">{'## 3. 道路拓扑：整体一致，优先核查近接点与较新道路\n\n道路统一为机动车网络，包含内部服务路与track，排除步行道、自行车道、台阶、规划与在建道路。Overture使用原生connector，OSM使用共享node ID；分别构建无向图，并在测试框外80m保留连通上下文。\n\n最大连通分量长度占比反映图中道路的连通程度。少量孤立分量可以来自门禁内部路、停车区或道路裁剪，**不能把所有度1节点或孤立分量都判为错误**。'}</Narrative></ReportSection>
   <EvidenceChart id="road-connectivity" title="最大连通分量占比" queryId="road_results" rows={connected} sourceRows={r} spec={{type:'bar',x:'area',y:'最大连通分量(%)',series:'source',colors:{Overture:'#4e79a7',Geofabrik:'#b37a15'},stackable:false,startAtZero:true,valueDecimals:2}} height={320}/>
   <Table id="road-table" title="机动车道路拓扑对照" queryId="road_results" rows={r} columns={[{field:'area',label:'区域'},{field:'source',label:'来源'},{field:'road_km',label:'长度(km)',renderCell:v=>v.toFixed(2)},{field:'lcc_percent',label:'最大分量占比',renderCell:pct},{field:'components',label:'分量数'},{field:'near_miss_candidates',label:'近接候选'},{field:'unconnected_crossings',label:'同层交叉断连候选'}]}/>
   <Table id="road-coverage-table" title="Overture对较新Geofabrik参考路长的5m覆盖" queryId="road_results" rows={ov} columns={[{field:'area',label:'区域'},{field:'ref_5m_percent',label:'5m缓冲参考覆盖率',renderCell:pct},{field:'missing_connectors',label:'缺失连接点引用'},{field:'connector_offline',label:'连接点离线>1m'}]}/>
   <Narrative id="road-limit">{'四区未发现连接点缺失引用、连接点偏离所属道路超过1m，或本规则下的同层平面交叉断连。空间近接候选去除两源重复后共3个。虹桥还出现1条不足1m的Overture线段，列入复核，不直接删除。\n\nGeofabrik参考道路的5m缓冲覆盖率在虹桥最低，为99.27%；未覆盖差异主要集中在虹桥和南京西路。两源道路均主要沿用OSM，但快照不同：Overture道路为2026-10-10，Geofabrik截止2026-10-25。不能只凭差异确认“新修道路”或错误。\n\n本次验证的是无向几何拓扑，不涵盖单行线、转向限制、权限、车种和实际可通行性；未输出自动修正后的导航网络。'}</Narrative>
  </section>
  <section className="qa-section"><Narrative id="case-heading">{'## 4. 可定位的核查清单\n\n局部对照图保留真实投影位置、50m比例尺和两源轮廓。5个未达匹配阈值的建筑、2个区域最大几何差异实例与3个道路近接点均可切换；悬停或键盘聚焦图形可查看来源与要素ID。'}</Narrative><ReviewMap rows={cases}/></section>
  <section className="qa-section">
   <ReportSection id="source-reading" title="版本与范围" queryId="sources" sourceRows={s} showHeading={false}><Narrative id="source-reading-body">{'## 5. 来源、版本与覆盖边界\n\n全上海范围采用项目已有16区WGS84边界并集，包含崇明、长兴与横沙。先按包围盒筛选，再按市界相交保存原始几何，不把裁断建筑当作完整建筑。南京西路、新天地、虹桥采用明确的分析矩形；陆家嘴矩形另与浦东新区相交，排除黄浦江对岸外滩。测试范围详见可复用GeoJSON与配置，不能当作各商圈的官方边界。\n\n- **Overture：** [2026-10-21.0官方发布](https://docs.overturemaps.org/getting-data/)。建筑1793830条、交通segment 219745条、connector 241431条；其中road 215458条。未发现重复ID、空几何或GEOS无效几何。这些检查不证明覆盖或位置正确。\n- **Geofabrik：** [中国PBF](https://download.geofabrik.de/asia/china.html)约1.62GB，官方MD5与本地文件一致。本地提取上海建筑153856条、highway线要素212636条；建筑关系成员去重并保留完整面。\n- **Microsoft：** [官方README与下载索引](https://github.com/microsoft/GlobalMLBuildingFootprints)，2026-08-13版30340个索引条目，逐QuadKey核查后无上海相交分区；上海轮廓数量、完整率、位置误差均为N/A。\n- **Overture上游：** 东亚提取数据约164.1万条，[Zenodo原始记录](https://doi.org/10.5281/zenodo.8174931)为CC BY 4.0；Overture记录的版本为2024-11-01，不能据此认定影像在该日拍摄。约15.2万条建筑来自OSM，主要版本为2026-09-06。\n\n许可：OSM/Geofabrik为ODbL；东亚建筑提取数据为CC BY 4.0；Microsoft数据说明为CDLA Permissive 2.0。应保留逐要素来源及对应许可，不能给混合数据统一标成无条件开放。'}</Narrative></ReportSection>
   <Table id="download-manifest" title="下载与提取清单" queryId="sources" rows={s} columns={[{field:'source',label:'来源'},{field:'type',label:'对象'},{field:'release',label:'版本/截止'},{field:'count',label:'数量'}]}/>
   <Table id="aoi-table" title="四个测试区（WGS84，经度/纬度）" queryId="building_results" rows={b.map((x,i)=>({...x,bounds:['121.483–121.518 / 31.225–31.252；限浦东','121.437–121.474 / 31.220–31.241','121.463–121.484 / 31.211–31.229','121.285–121.345 / 31.175–31.220'][i]}))} columns={[{field:'area',label:'区域'},{field:'bounds',label:'经度范围 / 纬度范围'},{field:'area_km2',label:'面积(km²)',renderCell:v=>v.toFixed(2)}]}/>
  </section>
  <ReportSection id="qa-recommendations" title="修正建议与放行条件" queryId="building_results" queryIds={['building_results','road_results','sources']} sourceRowsByQuery={{building_results:b,road_results:r,sources:s}} showHeading={false}>
   <Narrative id="qa-recommendations-body">{'## 6. 修正建议与放行条件\n\n1. **建筑采取“较新OSM优先＋Overture提取轮廓增补”的候选方案。** 对5个未达阈值对象逐一核对版本、楼层与部件语义；用IoU和面积覆盖检测拆分/合并，避免将楼上构筑物重复挤出成地面建筑。非OSM增补在独立抽检通过前保留待核验状态，不宣称全市完整。\n2. **路网优先保留较新Geofabrik几何与节点关系。** 核查虹桥与南京西路参考路长差异，以及3个近接点；结合桥隧、层级、入口与权限后决定是否吸附，禁止对所有平面交叉自动打断和连接。\n3. **先补独立参照，再给绝对精度结论。** 需要覆盖四区、明确坐标系和成像日期的正射影像/权威轮廓，或经复核的独立抽样标注。匹配参考覆盖率、候选错误率与绝对精度应分别发布。\n4. **高度单独处理。** Overture全上海建筑仅1073条有height，约0.060%；8415条有num_floors。若后续用于微缩城市，未知高度应明确标示为示意，不能把完整二维轮廓当作完整三维数据。\n\n本报告完成了开放数据下载、来源核查和四区对照验证；没有直接覆盖线上地图，也没有把候选清单自动写成已修正真值。精确计算、逐对象匹配、候选GeoJSON、版本记录和校验清单保留在项目的分析目录中，可复算复查。'}</Narrative>
  </ReportSection>
 </article>;
}
