# 来源与发现

## 必须保留的判断边界
- Overture 的 sources 字段需要统计上游来源；其与 OSM/Microsoft 有共同血缘的匹配不能表述为独立验证。
- 建筑轮廓完整率需要明确参考分母。无独立实测基准时使用“对参考建筑集合的覆盖率”，不称全城绝对完整率。
- 几何检查在米制投影中计算，IoU、质心距离、边界距离需以匹配条件和样本数为前提。
- 道路交叉需尊重桥梁/隧道/层级，不能把所有平面交叉都视为断连。

## 来源核实（2026-10-27）
- Overture 官方 Quickstart 与 S3 release 列表一致：最新 2026-10-21.0。
- Geofabrik 未提供 Shanghai 子区域；下载其中国 1.5 GB PBF，在本地抽取上海。页面数据截止 2026-10-25T21:21:21Z（最终以 PBF header 为准）。
- Microsoft 官方 README 指向 2026-08-13 dataset-links.csv，共 30,340 行。按全索引 QuadKey 计算空间包围盒，上海范围相交分区为 0；不能获取上海建筑对照轮廓，指标应为 N/A 而非 0% 完整率。
- 互联网检索工具不可用；已通过浏览器访问 Overture 官方文档，通过 HTTPS 获取官方说明、索引及源文件。

## 下载完成
- Overture 上海建筑：1,793,830 条（市界相交，保留原始几何），187,976,067 字节。
- Overture segment：219,745 条，其中 road 215,458、rail 4,253、water 34；应先按主题和道路类别统一范围再比较。
- Overture connector：241,431 条。
- 下载文件均已保存 SHA-256 清单，原始要素包含 sources 等来源属性。
- 抽查 Overture 建筑发现 doi:10.5281/zenodo.8174931（east_asian_buildings）来源，版本 2024-11-01。道路抽查为 OSM 2026-10-10 快照；需要统计全量来源，不能仅以 Overture 发布日表示影像/实地日期。
- Geofabrik PBF header 截止：2026-10-25T21:21:21Z，约比 Overture 道路 OSM 快照晚 15 天。
- Overture Python 对 STAC 索引 URL 返回 403，自动回退 S3 分区+行组空间过滤；实际上海数据已成功下载。

## 全量 Overture 初检
- 建筑 1,793,830：未发现重复 ID、空几何或 GEOS 无效几何；这不证明位置/覆盖正确。
- 1,641,438 建筑的 geometry 来源为东亚建筑提取数据（doi:10.5281/zenodo.8174931）；152,392 来源为 OSM。OSM 建筑来源版本主要是 2026-09-06，而非道路的 2026-10-10。
- 所有已下载 road/segment 与 connector 的来源均为 OSM。与 Geofabrik 的路网对照是同源不同处理/时点的一致性验证。
- Overture 建筑 height 非空 1,073，num_floors 非空 8,415。替换微缩图时不得把低高度覆盖当作完整三维模型。
