# 上海开放地图质量验证

2026-10-27，基于真实开放数据完成下载、来源审计、四区建筑与道路对照。虹桥按用户确认的“交通枢纽＋商务区”测试。陆家嘴限定为分析矩形与浦东新区相交的部分，排除对岸外滩。

## 阅读与结果

- 可交互报告：`report/上海开放地图质量验证.html`（完整单文件，包含已审阅数据）。
- 当前会话预览：http://127.0.0.1:50227/?view=1 。会话内服务不保证应用重启后仍运行。
- 报告源：`report-app/src/content/report/ReportContent.jsx`、`report-app/src/data.json`。
- 建筑指标：`results/building-metrics.json`；逐匹配对子：`results/building-matched-pairs.csv`。
- 道路指标：`results/road-metrics.json`；近接候选：`results/road-topology-candidates.geojson`；5m参考覆盖差异：`results/road-reference-gaps.geojson`。
- 来源、边界、方法阈值、版本与文件校验：`evidence/`。
- 70项数值、证据、来源及边界复核通过：`results/verification.json`。这不等于实地真值验证。

| 测试区 | Overture有效建筑 | OSM参考建筑 | 匹配数 | OSM参考匹配覆盖率 | Overture路网最大连通分量长度占比 |
|---|---:|---:|---:|---:|---:|
| 陆家嘴（浦东） | 1667 | 1075 | 1075 | 100.00% | 99.86% |
| 南京西路 | 5831 | 3116 | 3112 | 99.87% | 99.94% |
| 新天地 | 3067 | 1399 | 1398 | 99.93% | 99.29% |
| 虹桥枢纽＋商务区 | 6945 | 737 | 737 | 100.00% | 99.40% |

5个未达IoU阈值的参考对象均在主要Overture建筑OSM快照之后首次纳入OSM，不能直接称为真实漏建。3个道路近接点在两源均存在，需结合入口、层级与通行条件复核。报告提供10个真实坐标局部图：5个建筑参考差异、2个最大几何差异、3个道路近接点。

## 已取得的数据与限制

1. **Overture 2026-10-21.0**：全上海1,793,830条建筑、219,745条交通segment（其中215,458条road）、241,431条connector。以项目已有16区WGS84市界并集相交筛选，保留完整要素几何，文件均有SHA256及下载清单。原始Parquet位于`data/overture/`，约239MB。
2. **Geofabrik OSM中国PBF**：截止2026-10-25T21:21:21Z，1,615,922,210字节，官方MD5与本地一致；本地提取上海建筑153,856条、highway线要素212,636条。原始PBF与提取Parquet位于`data/geofabrik/`。节点读取使用市界bbox外扩0.03度；边缘1219条不完整bbox way跳过，建筑关系不完整数为0；四个测试区位于内部。
3. **Microsoft**：官方README指向2026-08-13索引。全部30,340条QuadKey逐条空间检索，没有与上海相交的下载分区，因此没有可下载的上海轮廓。该对照、绝对完整率和独立位置误差均为N/A，不能用0代替。
4. **来源依赖**：Overture上海约91.50%建筑几何来自东亚建筑提取数据，8.50%来自OSM；四区所有成功匹配对子共享OSM几何。近乎相同的轮廓不证明毫米级绝对精度。东亚数据只核查原始Zenodo记录及Overture逐要素来源，没有另外下载23GB上游ZIP或作独立真值验证。
5. **几何误差**：采用UTM51N（EPSG:32651）；输出质心距离、Hausdorff距离与对称边界抽样距离。陆家嘴最大边界差异12.658m（r12871465），其IoU仍为0.999970、质心差异约0.001m；南京西路最大质心与边界差异约1.569m。不存在独立基准，未声称RMSE或CE90。
6. **道路拓扑**：原生Overture connector和OSM node建无向图，统一机动车类别；80m外部上下文，内缩30m检查3m近接断点，桥隧/层级分离不自动平面连接。四区未发现连接点缺失引用、离线>1m或本规则下同层交叉断连。未核验单行线、转向限制、访问权限或实地可通行性。
7. **三维限制**：全上海建筑仅1073条有height（约0.060%）、8415条有num_floors；未知高度用于微缩地图时仍应标示为示意。

## 复算

本机下载数据与`.venv`均在Git忽略目录，避免将大体积数据误推送；小型下载清单另保存在`evidence/`。脚本固定源版本，不随latest自动漂移；Geofabrik远端latest变化后，须取得相同MD5文件才是完全同一输入。

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-lock.txt
.venv/bin/python scripts/acquire_overture.py building
.venv/bin/python scripts/acquire_overture.py segment
.venv/bin/python scripts/acquire_overture.py connector
# 先按evidence清单保存Geofabrik中国PBF至data/geofabrik/china-latest.osm.pbf
.venv/bin/python scripts/extract_geofabrik.py
.venv/bin/python scripts/audit_microsoft.py
.venv/bin/python scripts/prepare_aoi.py
.venv/bin/python scripts/metrics_buildings.py
.venv/bin/python scripts/metrics_roads.py
.venv/bin/python scripts/review_candidates.py
.venv/bin/python scripts/prepare_review_maps.py
.venv/bin/python scripts/verify_results.py
.venv/bin/python scripts/build_snapshot.py
```

测试边界与阈值以`evidence/analysis-config.json`为准。`reviewed-snapshot.json`是分析交付快照；刷新报告时仅更新现有`src/data.json`中的queries及generatedAt，保持报告id与用户展示设置。应用构建遵循`report-app/AGENTS.md`，使用Data插件已有运行时，不改受保护基础设施。

## 来源与署名

- [Overture官方数据下载](https://docs.overturemaps.org/getting-data/)
- [Geofabrik中国](https://download.geofabrik.de/asia/china.html)，数据来自© OpenStreetMap contributors，[ODbL](https://www.openstreetmap.org/copyright)
- [Microsoft GlobalMLBuildingFootprints](https://github.com/microsoft/GlobalMLBuildingFootprints)，CDLA Permissive 2.0（本次上海无可下载分区）
- [东亚建筑提取数据](https://doi.org/10.5281/zenodo.8174931)，CC BY 4.0；Overture记录版本2024-11-01，不等同于影像拍摄日期

报告完成源间验证和候选修正清单。未将候选自动写入线上地图，未把源间一致性当作绝对正确性。
