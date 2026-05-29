# Download UX Improvement 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化下载体验 — Geofabrik 本地缓存、文件树、Overpass/BBox 合并、默认保存路径

**Architecture:** 后端添加缓存层和配置端点，前端重构 DownloadPage 为两个 Tab（Geofabrik + Overpass），新建 RegionTree 树形组件

**Tech Stack:** FastAPI, React 19, TypeScript, Tailwind CSS, shadcn/ui Collapsible

---

## File Structure

| 操作 | 文件 | 职责 |
|------|------|------|
| 修改 | `src/osm_tool/core/downloader/geofabrik.py` | 添加本地缓存读写 |
| 修改 | `src/osm_tool/api/routes/download.py` | 新增 refresh/config 端点，移除 bbox 端点 |
| 修改 | `src/osm_tool/app.py` | 启动时创建 outdata 目录 |
| 修改 | `frontend/src/api/index.ts` | 新增 refresh/config API，移除 startBbox |
| 新建 | `frontend/src/components/RegionTree.tsx` | Geofabrik 文件树组件 |
| 修改 | `frontend/src/pages/DownloadPage.tsx` | 移除 BBox Tab，集成 RegionTree，默认路径 |

---

### Task 1: Geofabrik 后端缓存

**Files:**
- Modify: `src/osm_tool/core/downloader/geofabrik.py`

- [ ] **Step 1: 添加缓存逻辑到 GeofabrikIndex**

在 `GeofabrikIndex` 类中添加缓存方法。缓存文件路径为 `{cwd}/.cache/geofabrik_regions.json`。

修改 `geofabrik.py`，在 `GeofabrikIndex` 类中添加：

```python
import json
from pathlib import Path

class GeofabrikIndex:
    """Geofabrik 区域索引"""

    CACHE_DIR = Path.cwd() / ".cache"
    CACHE_FILE = CACHE_DIR / "geofabrik_regions.json"

    def __init__(self):
        self._regions: list[RegionInfo] = []

    def fetch_index(self, use_cache: bool = True) -> list[RegionInfo]:
        """获取区域索引，默认使用缓存"""
        if use_cache:
            cached = self._load_cache()
            if cached is not None:
                self._regions = cached
                return self._regions
        # 从远程获取
        resp = requests.get(GEOFABRIK_INDEX_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        self._regions = self._parse_index(data)
        self._save_cache()
        return self._regions

    def _load_cache(self) -> list[RegionInfo] | None:
        """从本地缓存加载"""
        if not self.CACHE_FILE.exists():
            return None
        try:
            data = json.loads(self.CACHE_FILE.read_text(encoding="utf-8"))
            return [
                RegionInfo(
                    id=r["id"], name=r["name"], parent_id=r.get("parent_id"),
                    url=r["url"], size_bytes=r.get("size_bytes", 0),
                )
                for r in data
            ]
        except Exception:
            return None

    def _save_cache(self) -> None:
        """保存到本地缓存"""
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data = [
            {"id": r.id, "name": r.name, "parent_id": r.parent_id, "url": r.url, "size_bytes": r.size_bytes}
            for r in self._regions
        ]
        self.CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
```

保留原有的 `get_children`、`get_region`、`_parse_index` 方法不变。

- [ ] **Step 2: 运行现有测试确认无破坏**

Run: `cd E:/oliver/learn/osm-download && uv run python -m pytest tests/test_geofabrik.py -v`
Expected: 现有测试通过（如有网络依赖测试可能需要 mock）

- [ ] **Step 3: Commit**

```bash
git add src/osm_tool/core/downloader/geofabrik.py
git commit -m "feat: add local cache for Geofabrik region index"
```

---

### Task 2: 后端 API 端点修改

**Files:**
- Modify: `src/osm_tool/api/routes/download.py`

- [ ] **Step 1: 修改 geofabrik_regions 端点使用缓存**

将 `geofabrik_regions` 改为默认走缓存：

```python
@router.get("/geofabrik/regions")
async def geofabrik_regions():
    """获取 Geofabrik 区域树（优先缓存）"""
    from osm_tool.core.downloader.geofabrik import GeofabrikIndex

    try:
        index = GeofabrikIndex()
        regions = index.fetch_index(use_cache=True)
        return {
            "code": 0,
            "data": [
                {
                    "id": r.id,
                    "name": r.name,
                    "parent_id": r.parent_id,
                    "url": r.url,
                    "size_bytes": r.size_bytes,
                }
                for r in regions
            ],
        }
    except Exception as e:
        return {"code": 1, "message": str(e)}
```

- [ ] **Step 2: 新增 geofabrik_refresh 端点**

```python
@router.post("/geofabrik/refresh")
async def geofabrik_refresh():
    """强制刷新 Geofabrik 区域缓存"""
    from osm_tool.core.downloader.geofabrik import GeofabrikIndex

    try:
        index = GeofabrikIndex()
        regions = index.fetch_index(use_cache=False)
        return {
            "code": 0,
            "data": {
                "count": len(regions),
            },
        }
    except Exception as e:
        return {"code": 1, "message": str(e)}
```

- [ ] **Step 3: 新增 default_save_path 端点**

```python
import os
from pathlib import Path

@router.get("/config/default-save-path")
async def default_save_path():
    """获取默认保存路径"""
    default_dir = Path.cwd() / "outdata"
    default_dir.mkdir(parents=True, exist_ok=True)
    return {"code": 0, "data": {"path": str(default_dir)}}
```

- [ ] **Step 4: 移除 bbox_start 端点**

删除 `bbox_start` 函数整体（约30行）。

- [ ] **Step 5: Commit**

```bash
git add src/osm_tool/api/routes/download.py
git commit -m "feat: add refresh/config endpoints, remove bbox endpoint"
```

---

### Task 3: 应用启动时创建 outdata 目录

**Files:**
- Modify: `src/osm_tool/app.py`

- [ ] **Step 1: 在 create_app 中创建 outdata 目录**

在 `create_app` 函数开头添加：

```python
def create_app() -> FastAPI:
    app = FastAPI(title="OSM Data Toolbox", version="0.1.0")

    # 确保输出目录存在
    outdata = Path.cwd() / "outdata"
    outdata.mkdir(parents=True, exist_ok=True)

    # ... 其余不变
```

- [ ] **Step 2: Commit**

```bash
git add src/osm_tool/app.py
git commit -m "feat: create outdata directory on app startup"
```

---

### Task 4: 前端 API 层更新

**Files:**
- Modify: `frontend/src/api/index.ts`

- [ ] **Step 1: 更新 downloadApi**

```typescript
export const downloadApi = {
  getGeofabrikRegions: () => api<any[]>('/download/geofabrik/regions'),
  refreshGeofabrikRegions: () => post<{ count: number }>('/download/geofabrik/refresh', {}),
  startGeofabrik: (params: { url: string; save_path: string; region_name?: string }) =>
    post<{ task_id: string }>('/download/geofabrik/start', params),
  startOverpass: (params: { query: string; save_path: string; output_format?: string }) =>
    post<{ task_id: string }>('/download/overpass/start', params),
  getDefaultSavePath: () => api<{ path: string }>('/download/config/default-save-path'),
  getTasks: () => api<any[]>('/download/tasks'),
  cancelTask: (id: string) => post(`/download/tasks/${id}/cancel`, {}),
}
```

移除 `startBbox`。添加 `refreshGeofabrikRegions` 和 `getDefaultSavePath`。

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/index.ts
git commit -m "feat: add refresh/config API calls, remove bbox API"
```

---

### Task 5: RegionTree 树形组件

**Files:**
- Create: `frontend/src/components/RegionTree.tsx`

- [ ] **Step 1: 创建 RegionTree 组件**

```tsx
import { useState } from 'react'

interface Region {
  id: string
  name: string
  parent_id: string | null
  url: string
  size_bytes: number
}

interface TreeNodeProps {
  name: string
  regions: Region[]
  allRegions: Region[]
  selectedId: string | null
  onSelect: (region: Region) => void
  defaultOpen?: boolean
}

function TreeNode({ name, regions, allRegions, selectedId, onSelect, defaultOpen = false }: TreeNodeProps) {
  const [open, setOpen] = useState(defaultOpen)
  const children = allRegions.filter(r => regions.some(cr => cr.id === r.parent_id))

  return (
    <div>
      {regions.map(region => {
        const hasChildren = allRegions.some(r => r.parent_id === region.id)
        const isSelected = selectedId === region.id
        const sizeStr = region.size_bytes ? `${(region.size_bytes / 1024 / 1024).toFixed(0)} MB` : ''

        return (
          <div key={region.id}>
            <div
              className={`flex cursor-pointer items-center gap-1 rounded px-2 py-1 text-sm hover:bg-[var(--muted)] ${isSelected ? 'bg-[var(--muted)]' : ''}`}
              onClick={() => {
                if (hasChildren) setOpen(!open)
                if (region.url) onSelect(region)
              }}
            >
              {hasChildren ? (
                <span className="w-4 text-center text-xs text-[var(--muted-foreground)]">
                  {open ? '▼' : '▶'}
                </span>
              ) : (
                <span className="w-4" />
              )}
              <span className="flex-1">{region.name}</span>
              {sizeStr && (
                <span className="text-xs text-[var(--muted-foreground)]">{sizeStr}</span>
              )}
            </div>
            {hasChildren && open && (
              <div className="ml-4">
                <TreeNode
                  name=""
                  regions={allRegions.filter(r => r.parent_id === region.id)}
                  allRegions={allRegions}
                  selectedId={selectedId}
                  onSelect={onSelect}
                />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

interface RegionTreeProps {
  regions: Region[]
  selectedId: string | null
  onSelect: (region: Region) => void
}

export function RegionTree({ regions, selectedId, onSelect }: RegionTreeProps) {
  const roots = regions.filter(r => r.parent_id === null)

  return (
    <div className="max-h-80 overflow-auto">
      <TreeNode
        name=""
        regions={roots}
        allRegions={regions}
        selectedId={selectedId}
        onSelect={onSelect}
      />
      {regions.length === 0 && (
        <p className="py-4 text-center text-sm text-[var(--muted-foreground)]">
          点击更新加载区域列表
        </p>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/RegionTree.tsx
git commit -m "feat: add RegionTree component for hierarchical Geofabrik display"
```

---

### Task 6: 重构 DownloadPage

**Files:**
- Modify: `frontend/src/pages/DownloadPage.tsx`

这是最大的改动，将三 Tab 重构为两 Tab（Geofabrik + Overpass），集成 RegionTree，移除 BBox，添加默认路径。

- [ ] **Step 1: 重写 DownloadPage.tsx**

```tsx
import { useState, useEffect } from 'react'
import { downloadApi } from '../api'
import { useTasks } from '../hooks/useTasks'
import { FileSelector } from '../components/FileSelector'
import { TaskTable } from '../components/TaskTable'
import { MapSelector } from '../components/MapSelector'
import { RegionTree } from '../components/RegionTree'

export function DownloadPage() {
  const { tasks } = useTasks('download')
  const [tab, setTab] = useState<'geofabrik' | 'overpass'>('geofabrik')

  // 默认保存路径
  const [defaultSavePath, setDefaultSavePath] = useState('')

  // Geofabrik
  const [geoRegions, setGeoRegions] = useState<any[]>([])
  const [geoSelected, setGeoSelected] = useState<any>(null)
  const [geoPath, setGeoPath] = useState('')
  const [geoRefreshing, setGeoRefreshing] = useState(false)

  // Overpass
  const [opBbox, setOpBbox] = useState({ left: 116.3, bottom: 39.8, right: 116.5, top: 40.0 })
  const [opFormat, setOpFormat] = useState('json')
  const [opPath, setOpPath] = useState('')

  const [loading, setLoading] = useState(false)

  // 获取默认保存路径
  useEffect(() => {
    downloadApi.getDefaultSavePath().then(data => {
      setDefaultSavePath(data.path)
    }).catch(() => {})
  }, [])

  // 页面加载时自动获取 Geofabrik 区域（走缓存）
  useEffect(() => {
    fetchRegions()
  }, [])

  const fetchRegions = async () => {
    setLoading(true)
    try {
      const data = await downloadApi.getGeofabrikRegions()
      setGeoRegions(data)
    } catch (e: any) {
      alert(e.message)
    } finally {
      setLoading(false)
    }
  }

  const refreshRegions = async () => {
    setGeoRefreshing(true)
    try {
      await downloadApi.refreshGeofabrikRegions()
      await fetchRegions()
    } catch (e: any) {
      alert(e.message)
    } finally {
      setGeoRefreshing(false)
    }
  }

  // 选中 Geofabrik 区域时自动设置保存路径
  const handleGeoSelect = (region: any) => {
    setGeoSelected(region)
    if (region.url && defaultSavePath) {
      const filename = region.id.split('/').pop() + '.pbf'
      setGeoPath(defaultSavePath + '/' + filename)
    }
  }

  const startGeofabrik = async () => {
    if (!geoSelected || !geoPath) return alert('请选择区域和保存路径')
    try {
      await downloadApi.startGeofabrik({ url: geoSelected.url, save_path: geoPath, region_name: geoSelected.name })
    } catch (e: any) {
      alert(e.message)
    }
  }

  // Overpass: 地图选区自动生成查询
  const generateOverpassQuery = () => {
    const { left, bottom, right, top } = opBbox
    return `[out:${opFormat}];\nway(${bottom},${left},${top},${right})["highway"];\nout body;\n>;\nout skel qt;`
  }

  const startOverpass = async () => {
    if (!opPath) return alert('请选择保存路径')
    const query = generateOverpassQuery()
    try {
      await downloadApi.startOverpass({ query, save_path: opPath, output_format: opFormat })
    } catch (e: any) {
      alert(e.message)
    }
  }

  const tabs = [
    { key: 'geofabrik' as const, label: 'Geofabrik' },
    { key: 'overpass' as const, label: 'Overpass API' },
  ]

  const bboxArea = () => {
    const area = (opBbox.right - opBbox.left) * (opBbox.top - opBbox.bottom)
    return { area, oversized: area > 0.25 }
  }

  // 切换到 Overpass tab 时设置默认路径
  const handleTabChange = (key: 'geofabrik' | 'overpass') => {
    setTab(key)
    if (key === 'overpass' && !opPath && defaultSavePath) {
      const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
      const ext = opFormat === 'xml' ? '.osm' : '.json'
      setOpPath(defaultSavePath + '/overpass_' + ts + ext)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-1 border-b border-[var(--border)]">
        {tabs.map(t => (
          <button
            key={t.key}
            className={`px-4 py-2 text-sm ${tab === t.key ? 'border-b-2 border-[var(--primary)] font-medium' : 'text-[var(--muted-foreground)]'}`}
            onClick={() => handleTabChange(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'geofabrik' && (
        <div className="grid grid-cols-2 gap-4">
          <div className="border border-[var(--border)] rounded p-3">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-sm font-medium">区域选择</h3>
              <button
                className="text-xs text-[var(--muted-foreground)] hover:underline"
                onClick={refreshRegions}
                disabled={geoRefreshing}
              >
                {geoRefreshing ? '更新中...' : '更新'}
              </button>
            </div>
            <RegionTree
              regions={geoRegions}
              selectedId={geoSelected?.id ?? null}
              onSelect={handleGeoSelect}
            />
          </div>
          <div className="flex flex-col gap-3">
            <div>
              <label className="text-sm">选中区域: {geoSelected?.name || '未选择'}</label>
            </div>
            <div>
              <label className="mb-1 block text-sm">保存路径</label>
              <FileSelector value={geoPath} onChange={setGeoPath} mode="save_file" fileTypes={[{ label: 'PBF', ext: '*.pbf' }]} />
            </div>
            <button
              className="rounded bg-[var(--primary)] px-4 py-2 text-sm text-[var(--primary-foreground)] hover:opacity-90 disabled:opacity-50"
              onClick={startGeofabrik}
              disabled={!geoSelected || !geoPath}
            >
              下载
            </button>
          </div>
        </div>
      )}

      {tab === 'overpass' && (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <MapSelector bbox={opBbox} onBboxChange={setOpBbox} height="360px" />
            <div className="mt-2 flex items-center justify-between">
              <span className="text-xs text-[var(--muted-foreground)]">
                选区: {opBbox.left.toFixed(4)}, {opBbox.bottom.toFixed(4)} ~ {opBbox.right.toFixed(4)}, {opBbox.top.toFixed(4)}
              </span>
              <span className="text-xs text-[var(--muted-foreground)]">
                面积: {bboxArea().area.toFixed(4)}°²
                {bboxArea().oversized && (
                  <span className="ml-1 text-red-500 font-medium">超过 0.25°²</span>
                )}
              </span>
            </div>
            <div className="mt-2 rounded border border-[var(--border)] bg-[var(--muted)] p-2">
              <label className="mb-1 block text-xs text-[var(--muted-foreground)]">自动生成的 Overpass 查询</label>
              <pre className="whitespace-pre-wrap text-xs font-mono">{generateOverpassQuery()}</pre>
            </div>
          </div>
          <div className="flex flex-col gap-3">
            <div className="flex gap-2">
              <label className="text-sm">输出格式:</label>
              <select
                className="rounded border border-[var(--input)] px-2 py-1 text-sm"
                value={opFormat}
                onChange={e => setOpFormat(e.target.value)}
              >
                <option value="json">JSON</option>
                <option value="xml">XML</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm">保存路径</label>
              <FileSelector value={opPath} onChange={setOpPath} mode="save_file" fileTypes={[{ label: 'JSON', ext: '*.json' }, { label: 'OSM', ext: '*.osm' }]} />
            </div>
            <button
              className="rounded bg-[var(--primary)] px-4 py-2 text-sm text-[var(--primary-foreground)] hover:opacity-90 disabled:opacity-50"
              onClick={startOverpass}
              disabled={!opPath || bboxArea().oversized}
            >
              执行查询并下载
            </button>
          </div>
        </div>
      )}

      <div className="mt-4">
        <h3 className="mb-2 text-sm font-medium">下载队列</h3>
        <TaskTable tasks={tasks} onCancel={id => downloadApi.cancelTask(id)} />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: TypeScript 类型检查**

Run: `cd E:/oliver/learn/osm-download/frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/DownloadPage.tsx
git commit -m "feat: refactor DownloadPage - merge BBox into Overpass, add RegionTree, default paths"
```

---

### Task 7: 构建验证

**Files:** 无新文件

- [ ] **Step 1: 前端生产构建**

Run: `cd E:/oliver/learn/osm-download/frontend && npm run build`
Expected: 构建成功

- [ ] **Step 2: 后端导入测试**

Run: `cd E:/oliver/learn/osm-download && uv run python -c "from osm_tool.app import app; print('OK')"`
Expected: 输出 `OK`

- [ ] **Step 3: 运行现有测试**

Run: `cd E:/oliver/learn/osm-download && uv run python -m pytest tests/ -v --tb=short`
Expected: 所有测试通过
