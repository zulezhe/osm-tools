# Download UX Improvement Design

Date: 2026-05-14

## Overview

4 项下载体验优化：Geofabrik 本地缓存、文件树展示、Overpass/BBox 合并、默认保存路径。

---

## 1. Geofabrik 本地缓存 + 刷新改"更新"

### 问题
每次加载 Geofabrik 区域列表都要请求远程 `index-v1.json`，速度慢。

### 方案

**后端**
- 首次请求时从 `https://download.geofabrik.de/index-v1.json` 拉取数据，存入本地缓存文件 `{cwd}/.cache/geofabrik_regions.json`
- `GET /geofabrik/regions` 优先读缓存，缓存存在则直接返回（秒回）
- 新增 `POST /geofabrik/refresh` 端点：强制从远程拉取并更新缓存
- 缓存文件记录 `fetched_at` 时间戳

**前端**
- 页面加载时自动调用 `GET /geofabrik/regions`（走缓存，即时返回）
- 按钮文字从"刷新"改为"更新"
- 点击"更新"调用 `POST /geofabrik/refresh`，完成后刷新列表

### 涉及文件
- `src/osm_tool/api/routes/download.py` — 新增 refresh 端点
- `src/osm_tool/core/downloader/geofabrik.py` — 缓存读写逻辑
- `frontend/src/api/index.ts` — 新增 refresh API 调用
- `frontend/src/pages/DownloadPage.tsx` — 按钮文案和调用逻辑

---

## 2. Geofabrik 文件树

### 问题
当前 Geofabrik 区域以平铺列表展示，无法体现层级关系。

### 方案

使用 shadcn/ui Collapsible 组件手写轻量树形结构：

**数据结构**：后端已返回 `parent_id` 字段，前端构建树：
```
Africa
  ├── Algeria (58 MB)
  ├── Angola (65 MB)
  └── ...
Asia
  ├── China (580 MB)
  │   ├── Beijing (12 MB)
  │   └── Shanghai (9 MB)
  └── ...
```

**组件**：`RegionTree` 组件
- 每个节点显示名称 + 文件大小
- 有子节点的节点可展开/折叠（箭头图标）
- 叶子节点点击选中，高亮显示
- 支持搜索过滤

**交互**
- 首层节点默认折叠
- 选中叶子节点后，下方显示选中信息（名称、大小、URL）
- 非叶子节点（有 URL）也可选择下载

### 涉及文件
- `frontend/src/components/RegionTree.tsx` — 新建树形组件
- `frontend/src/pages/DownloadPage.tsx` — 替换平铺列表为 RegionTree

---

## 3. Overpass API + BBox 合并

### 问题
Overpass 和 BBox 功能高度重叠，分开增加认知负担。

### 方案

**合并为单一 Overpass 下载 Tab**：
- 地图选区（原有 MapSelector）自动生成 Overpass QL 查询
- 显示 bbox 坐标和自动生成的查询语句（只读预览）
- 移除手动查询文本框
- 输出格式选择保留（JSON/XML）

**后端**：
- 移除 `POST /bbox/start` 端点
- BBox 坐标在前端转换为 Overpass QL：`[bbox:s,w,n,e];(node({{bbox}});<;);out body;`
- 只走 Overpass 下载路径

**前端**：
- 移除 BBox Tab
- Overpass Tab 地图选区后自动生成查询并显示预览
- 显示选中区域面积提示（超过 0.25°² 时警告）

### 涉及文件
- `frontend/src/pages/DownloadPage.tsx` — 移除 BBox Tab，简化 Overpass Tab
- `src/osm_tool/api/routes/download.py` — 移除 bbox 端点
- `src/osm_tool/core/downloader/bbox.py` — 可保留文件但不再暴露 API

---

## 4. 默认保存路径

### 问题
每次下载都需要手动选择保存路径，操作繁琐。

### 方案

**后端**：
- 应用启动时检查 `{cwd}/outdata/` 目录，不存在则创建
- 新增 `GET /config/default-save-path` 端点返回默认路径
- 下载时如果未指定路径，自动使用默认路径 + 文件名

**前端**：
- 页面加载时获取默认保存路径
- FileSelector 的默认值设为 `{默认路径}/{自动生成文件名}`
- 用户仍可手动修改路径

### 文件命名规则
- Geofabrik: `{region_id}.pbf`（如 `china.pbf`）
- Overpass: `overpass_{timestamp}.json`

### 涉及文件
- `src/osm_tool/main.py` — 启动时创建 outdata 目录
- `src/osm_tool/api/routes/download.py` — 新增配置端点
- `frontend/src/pages/DownloadPage.tsx` — 默认路径填充
- `frontend/src/api/index.ts` — 新增配置 API

---

## 文件变更汇总

| 操作 | 文件 |
|------|------|
| 修改 | `src/osm_tool/api/routes/download.py` |
| 修改 | `src/osm_tool/core/downloader/geofabrik.py` |
| 修改 | `src/osm_tool/main.py` |
| 修改 | `frontend/src/pages/DownloadPage.tsx` |
| 修改 | `frontend/src/api/index.ts` |
| 新建 | `frontend/src/components/RegionTree.tsx` |
