# 下载页面重构 Spec

Date: 2026-05-14

## 概述

将下载页面从多 Tab（Geofabrik/Overpass/BBox）重构为单页面工作流，聚焦用户关心的三种选区方式：区域选择、导入矢量、自定义绘制。

## 页面布局

```
┌──────────────────────────────────────────────────────┐
│ [区域选择]  [导入矢量]  [自定义绘制]   ← 三个模式按钮   │
├─────────────────────────┬────────────────────────────┤
│                         │ 选区信息                    │
│      地图区域            │ 面积 / 坐标 / 边界          │
│  (根据模式切换工具)       │ 输出格式: JSON / XML        │
│                         │ 保存路径: outdata/...       │
│                         │ [下载]                      │
├─────────────────────────┴────────────────────────────┤
│ 下载队列                                              │
└──────────────────────────────────────────────────────┘
```

## 三种模式

### 1. 区域选择
- 左侧地图 + 右侧 Geofabrik 树形选择器（上下布局）
- 地图支持 bbox 框选
- 选中 Geofabrik 区域时在地图上高亮边界
- 小区域走 Overpass，大区域（>1°²）提示建议用 Geofabrik 直接下载

### 2. 导入矢量
- 文件上传区（拖拽或点击）
- 支持：GeoJSON(.geojson/.json)、Shapefile(.zip)、KML(.kml)、GeoPackage(.gpkg)
- 上传后后端解析提取边界，前端在地图上显示
- 自动计算 bbox，用 Overpass 下载

### 3. 自定义绘制
- 地图上绘制工具栏：矩形 / 多边形 / 圆形
- 矩形 → Overpass bbox 查询
- 多边形 → Overpass poly 查询
- 圆形 → Overpass around 查询

## 后端 API

### 新增端点

`POST /download/import-vector`
- 接收文件上传
- 用 GDAL/OGR 解析提取几何边界和 bbox
- 返回：bbox、GeoJSON 几何、面积

`POST /download/overpass/query`
- 接收几何数据（bbox/polygon/circle）
- 自动生成 Overpass QL 查询
- 返回生成的查询语句（预览用）

### 保留端点
- `GET /geofabrik/regions` — 区域树（缓存）
- `POST /geofabrik/refresh` — 更新缓存
- `POST /geofabrik/start` — Geofabrik 直接下载
- `POST /overpass/start` — Overpass 查询下载

## 数据来源策略
- bbox < 1°² → Overpass API
- bbox >= 1°² → 提示"区域较大，建议使用 Geofabrik 下载"
- Geofabrik 区域选择 → 直接走 Geofabrik 下载

## 文件变更

| 操作 | 文件 | 职责 |
|------|------|------|
| 重写 | `frontend/src/pages/DownloadPage.tsx` | 新的单页面工作流 |
| 新建 | `frontend/src/components/DrawMap.tsx` | 带绘制工具的地图组件 |
| 修改 | `frontend/src/components/MapSelector.tsx` | 保留但简化 |
| 修改 | `frontend/src/components/RegionTree.tsx` | 保持不变 |
| 修改 | `src/osm_tool/api/routes/download.py` | 新增 import-vector 端点 |
| 新建 | `src/osm_tool/core/downloader/vector_parser.py` | 矢量文件解析 |
| 修改 | `frontend/src/api/index.ts` | 新增 API |
| 修改 | `frontend/package.json` | 添加 leaflet-draw |
