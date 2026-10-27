# 沪上漫游 · Little Shanghai

上海全域的实时等距微缩城市地图，可切换平面矢量与卫星影像。支持自由飞行、自动航线、地标搜索、全 16 区导航和触屏方向控制。

## 运行

在此目录运行 `python3 -m http.server 4186 --bind 127.0.0.1 --directory dist`，浏览器打开 `http://127.0.0.1:4186`。无须安装应用依赖，也无须配置地图密钥。地图数据与影像在线加载，需要网络与支持 WebGL2 的浏览器。

## 操作

- 拖动平移、滚轮或双指缩放、右键拖动旋转。3D 按钮切换俯视与等距。
- P 起飞或结束，方向键／WASD 转向与升降，空格暂停。手机使用屏幕方向键。
- 自动游览提供一江两岸、梧桐与弄堂、江海之间和环游大上海 4 条循环航线。按方向键即可接管自动驾驶。
- 地图位置、角度与缩放写入 URL，可复制链接定位。搜索包含已收录地标与 16 个行政区，不是通用地址检索服务。

## 来源与范围

- 视觉参考：https://tinygyn.com/ ，等距视角、微缩城市和飞机游览概念。未复制其城市图像或飞机代码。
- 真实矢量：OpenFreeMap / OpenMapTiles / OpenStreetMap contributors。https://openfreemap.org/quick_start/ 。按需加载整个上海，建筑轮廓、道路、水系、绿地的覆盖程度由来源决定。
- 影像：Esri World Imagery（Esri、Maxar、Earthstar Geographics、GIS User Community）。影像日期随区域不同，不代表实时拍摄。https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer
- 行政区：阿里云 DataV https://geo.datav.aliyun.com/areas_v3/bound/310000_full.json 。16 区含崇明、长兴、横沙等岛屿；参考边界与中文地点从 GCJ-02 转换到 WGS84 后与底图叠加。
- 地标：东方明珠、上海中心、环球金融中心、金茂大厦为风格化几何模型；不是精密建筑测绘。普通建筑采用已有高度的 0.75 倍，缺失高度使用示意值。

这是可交互的实时矢量风格重建，不是逐瓦片 AI 重绘的全上海像素画；卫星影像作为独立对照图层。

## 验证

`npm run check` 检查脚本，`node --test tests/flight.test.mjs` 校验经纬度移动、坐标转换、航线闭环、暂停恢复与手动接管，以及树木生成的混合几何处理。浏览器验证记录在 `verification.md`。

## 第三方依赖

本地打包 MapLibre GL JS 5.10.0 (BSD-3-Clause) 与 Three.js 0.180.0 (MIT)，许可证保留于 `dist/vendor/`。

## 开放数据质量验证

2026-10-27完成Overture全上海建筑与路网下载，对照Geofabrik OSM，在陆家嘴（浦东）、南京西路、新天地、虹桥交通枢纽＋商务区验证参考覆盖、相对几何差异和原生道路拓扑。查看[验证说明与复算方法](analysis/shanghai-open-data-qa/README.md)及[完整交互报告](analysis/shanghai-open-data-qa/report/上海开放地图质量验证.html)。原始大型数据保留在本机忽略目录。

Microsoft官方当前索引没有上海下载分区；四区所有成功匹配建筑共享OSM上游，因此报告没有将源间一致率解释为真实世界完整率或独立测量精度。候选修正清单尚未自动覆盖线上地图。
