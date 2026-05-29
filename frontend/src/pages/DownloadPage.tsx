import { useState, useEffect, useRef, useCallback } from 'react'
import {
  ChevronDown,
  ChevronUp,
  Circle,
  Database,
  Download,
  Eraser,
  FileUp,
  Loader2,
  MapPinned,
  Pentagon,
  RefreshCw,
  Square,
} from 'lucide-react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { downloadApi } from '../api'
import { useTasks } from '../hooks/useTasks'
import { FileSelector } from '../components/FileSelector'
import { TaskTable } from '../components/TaskTable'
import { RegionTree } from '../components/RegionTree'

export interface DrawGeometry {
  type: 'bbox' | 'polygon' | 'circle'
  bbox?: { left: number; bottom: number; right: number; top: number }
  coordinates?: number[][]
  center_lat?: number
  center_lng?: number
  radius?: number
  area_sqkm?: number
}

type Tool = 'region' | 'import' | 'draw'
type DrawShape = 'rect' | 'polygon' | 'circle' | null

interface GeoRegion {
  id: string
  name: string
  parent_id: string | null
  url: string
  size_bytes: number
}

interface ImportResult {
  area_sqkm: number
  bbox: { left: number; bottom: number; right: number; top: number }
}

interface ImportVectorResponse {
  code: number
  data: ImportResult
  message?: string
}

const TOOL_ITEMS: Array<{ key: Tool; label: string; desc: string; icon: typeof Square }> = [
  { key: 'draw', label: '自定义绘制', desc: '框选、圆形或多边形', icon: Square },
  { key: 'region', label: '区域选择', desc: 'Geofabrik 数据源', icon: MapPinned },
  { key: 'import', label: '导入矢量', desc: '从文件读取范围', icon: FileUp },
]

const DRAW_SHAPES: Array<{ key: DrawShape; label: string; title: string; icon: typeof Square }> = [
  { key: 'rect', label: '矩形', title: '按住 Ctrl 并拖拽绘制矩形', icon: Square },
  { key: 'circle', label: '圆形', title: '按住 Ctrl 从圆心拖拽绘制圆形', icon: Circle },
  { key: 'polygon', label: '多边形', title: '按住 Ctrl 单击添加顶点，双击结束', icon: Pentagon },
]

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

export function DownloadPage() {
  const { tasks } = useTasks('download')
  const [tool, setTool] = useState<Tool>('draw')
  const [drawShape, setDrawShape] = useState<DrawShape>('rect')
  const [defaultSavePath, setDefaultSavePath] = useState('')
  const [outputFormat, setOutputFormat] = useState('json')
  const [savePath, setSavePath] = useState('')

  const [geoRegions, setGeoRegions] = useState<GeoRegion[]>([])
  const [geoSelected, setGeoSelected] = useState<GeoRegion | null>(null)
  const [geoRefreshing, setGeoRefreshing] = useState(false)

  const [drawGeom, setDrawGeom] = useState<DrawGeometry | null>(null)
  const [importResult, setImportResult] = useState<ImportResult | null>(null)
  const [importLoading, setImportLoading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [taskPanelOpen, setTaskPanelOpen] = useState(false)
  const [regionPanelOpen, setRegionPanelOpen] = useState(false)

  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const drawnItemsRef = useRef<L.FeatureGroup | null>(null)
  const drawingRef = useRef(false)
  const drawShapeRef = useRef<DrawShape>('rect')
  const toolRef = useRef<Tool>('draw')
  const startPosRef = useRef<L.LatLng | null>(null)
  const tempLayerRef = useRef<L.Layer | null>(null)
  const polyPointsRef = useRef<L.LatLng[]>([])
  const polyMarkersRef = useRef<L.CircleMarker[]>([])
  const polyLineRef = useRef<L.Polyline | null>(null)

  const defaultSavePathRef = useRef('')
  const outputFormatRef = useRef(outputFormat)

  useEffect(() => {
    drawShapeRef.current = drawShape
  }, [drawShape])

  useEffect(() => {
    toolRef.current = tool
  }, [tool])

  useEffect(() => {
    defaultSavePathRef.current = defaultSavePath
  }, [defaultSavePath])

  useEffect(() => {
    outputFormatRef.current = outputFormat
  }, [outputFormat])

  useEffect(() => {
    downloadApi.getDefaultSavePath().then(d => setDefaultSavePath(d.path)).catch(() => {})
  }, [])

  useEffect(() => {
    downloadApi.getGeofabrikRegions().then(setGeoRegions).catch(() => {})
  }, [])

  const refreshRegions = async () => {
    setGeoRefreshing(true)
    try {
      await downloadApi.refreshGeofabrikRegions()
      setGeoRegions(await downloadApi.getGeofabrikRegions())
    } catch (e: unknown) {
      alert(getErrorMessage(e, '更新区域失败'))
    } finally {
      setGeoRefreshing(false)
    }
  }

  const handleGeoSelect = (region: GeoRegion) => {
    setGeoSelected(region)
    if (region.url) {
      const basePath = defaultSavePath || 'outdata'
      setSavePath(basePath + '/' + region.id.split('/').pop() + '.pbf')
    }
  }

  const autoSetSavePath = useCallback((prefix: string) => {
    const basePath = defaultSavePathRef.current || 'outdata'
    const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
    const ext = outputFormatRef.current === 'xml' ? '.osm' : '.json'
    setSavePath(basePath + '/' + prefix + '_' + ts + ext)
  }, [])

  const getAreaDisplay = () => {
    if (tool === 'region' && geoSelected?.size_bytes) return `${(geoSelected.size_bytes / 1024 / 1024).toFixed(0)} MB`
    if (drawGeom?.area_sqkm) return `${drawGeom.area_sqkm} km²`
    if (importResult?.area_sqkm) return `${importResult.area_sqkm} km²`
    return '未选择'
  }

  const getQueryPreview = () => {
    if (drawGeom) {
      if (drawGeom.type === 'bbox' && drawGeom.bbox) {
        const b = drawGeom.bbox
        return `[out:${outputFormat}];\nnode(${b.bottom},${b.left},${b.top},${b.right});\nout body;\n>;\nout skel qt;`
      }
      if (drawGeom.type === 'polygon' && drawGeom.coordinates) {
        const poly = drawGeom.coordinates.slice(0, -1).map(([lng, lat]) => `${lat} ${lng}`).join(' ')
        return `[out:${outputFormat}];\nnode(poly:"${poly}");\nout body;\n>;\nout skel qt;`
      }
      if (drawGeom.type === 'circle' && drawGeom.center_lat != null) {
        return `[out:${outputFormat}];\nnode(around:${drawGeom.radius},${drawGeom.center_lat},${drawGeom.center_lng});\nout body;\n>;\nout skel qt;`
      }
    }
    if (importResult?.bbox) {
      const b = importResult.bbox
      return `[out:${outputFormat}];\nnode(${b.bottom},${b.left},${b.top},${b.right});\nout body;\n>;\nout skel qt;`
    }
    return null
  }

  const buildOverpassQuery = async (): Promise<string | null> => {
    if (tool === 'region' && geoSelected) return null
    if (drawGeom) {
      const body: Record<string, unknown> = { type: drawGeom.type, output_format: outputFormat }
      if (drawGeom.type === 'bbox') Object.assign(body, drawGeom.bbox)
      if (drawGeom.type === 'polygon') body.coordinates = drawGeom.coordinates?.slice(0, -1)
      if (drawGeom.type === 'circle') {
        body.center_lat = drawGeom.center_lat
        body.center_lng = drawGeom.center_lng
        body.radius = drawGeom.radius
      }
      try {
        return (await downloadApi.generateOverpassQuery(body)).query
      } catch {
        return null
      }
    }
    if (importResult?.bbox) {
      const b = importResult.bbox
      return `[out:${outputFormat}];\nnode(${b.bottom},${b.left},${b.top},${b.right});\nout body;\n>;\nout skel qt;`
    }
    return null
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImportLoading(true)
    setImportResult(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch('/api/v1/download/import-vector', { method: 'POST', body: formData })
      const json = await res.json() as ImportVectorResponse
      if (json.code === 0) {
        setImportResult(json.data)
        if (mapRef.current && json.data.bbox) {
          const b = json.data.bbox
          drawnItemsRef.current?.clearLayers()
          drawnItemsRef.current?.addLayer(L.rectangle([[b.bottom, b.left], [b.top, b.right]], {
            color: '#1f6f5b',
            weight: 2,
            fillOpacity: 0.14,
          }))
          mapRef.current.fitBounds([[b.bottom, b.left], [b.top, b.right]])
        }
        autoSetSavePath('import')
      } else {
        alert(json.message || '解析失败')
      }
    } catch (err: unknown) {
      alert(getErrorMessage(err, '上传失败'))
    } finally {
      setImportLoading(false)
    }
  }

  const startDownload = async () => {
    if (!savePath) return alert('请选择保存路径')
    if (tool === 'region' && geoSelected?.url) {
      try {
        await downloadApi.startGeofabrik({ url: geoSelected.url, save_path: savePath, region_name: geoSelected.name })
        setTaskPanelOpen(true)
      } catch (e: unknown) {
        alert(getErrorMessage(e, '下载失败'))
      }
      return
    }
    const query = await buildOverpassQuery()
    if (!query) return alert('无法生成查询，请先选择下载范围')
    try {
      await downloadApi.startOverpass({ query, save_path: savePath, output_format: outputFormat })
      setTaskPanelOpen(true)
    } catch (e: unknown) {
      alert(getErrorMessage(e, '下载失败'))
    }
  }

  const canDownload = () => {
    if (!savePath) return false
    if (tool === 'region') return !!geoSelected
    if (tool === 'draw') return !!drawGeom
    if (tool === 'import') return !!importResult
    return false
  }

  const clearDrawing = useCallback(() => {
    drawingRef.current = false
    startPosRef.current = null
    if (tempLayerRef.current && mapRef.current) {
      mapRef.current.removeLayer(tempLayerRef.current)
      tempLayerRef.current = null
    }
    polyPointsRef.current = []
    polyMarkersRef.current.forEach(m => m.remove())
    polyMarkersRef.current = []
    if (polyLineRef.current && mapRef.current) {
      mapRef.current.removeLayer(polyLineRef.current)
      polyLineRef.current = null
    }
    if (mapRef.current) mapRef.current.dragging.enable()
  }, [])

  const handleToolChange = useCallback((t: Tool) => {
    setTool(t)
    setDrawGeom(null)
    setImportResult(null)
    setRegionPanelOpen(false)
    drawnItemsRef.current?.clearLayers()
    clearDrawing()
    if (t === 'region') setRegionPanelOpen(true)
  }, [clearDrawing])

  const handleDrawShapeChange = useCallback((s: DrawShape) => {
    setDrawShape(s)
    setDrawGeom(null)
    drawnItemsRef.current?.clearLayers()
    clearDrawing()
  }, [clearDrawing])

  const finishRect = useCallback((start: L.LatLng, end: L.LatLng) => {
    if (!mapRef.current) return
    const sw = L.latLng(Math.min(start.lat, end.lat), Math.min(start.lng, end.lng))
    const ne = L.latLng(Math.max(start.lat, end.lat), Math.max(start.lng, end.lng))
    drawnItemsRef.current?.clearLayers()
    drawnItemsRef.current?.addLayer(L.rectangle([[sw.lat, sw.lng], [ne.lat, ne.lng]], { color: '#1d4ed8', weight: 2, fillOpacity: 0.14 }))
    const area = estimateArea(sw, ne)
    setDrawGeom({
      type: 'bbox',
      bbox: { left: sw.lng, bottom: sw.lat, right: ne.lng, top: ne.lat },
      area_sqkm: area,
    })
    autoSetSavePath('rect')
    mapRef.current.dragging.enable()
  }, [autoSetSavePath])

  const finishCircle = useCallback((center: L.LatLng, point: L.LatLng) => {
    if (!mapRef.current) return
    const radius = center.distanceTo(point)
    drawnItemsRef.current?.clearLayers()
    drawnItemsRef.current?.addLayer(L.circle(center, { radius, color: '#c27803', weight: 2, fillOpacity: 0.14 }))
    const area = Math.PI * (radius / 1000) ** 2
    setDrawGeom({
      type: 'circle',
      center_lat: center.lat,
      center_lng: center.lng,
      radius: Math.round(radius),
      area_sqkm: Math.round(area * 100) / 100,
    })
    autoSetSavePath('circle')
    mapRef.current.dragging.enable()
  }, [autoSetSavePath])

  const finishPolygon = useCallback(() => {
    if (!mapRef.current || polyPointsRef.current.length < 3) return
    const pts = polyPointsRef.current.slice()
    drawnItemsRef.current?.clearLayers()
    drawnItemsRef.current?.addLayer(L.polygon(pts, { color: '#15803d', weight: 2, fillOpacity: 0.14 }))
    const coords = pts.map(ll => [ll.lng, ll.lat])
    coords.push(coords[0])
    const bounds = L.latLngBounds(pts)
    const area = estimateArea(bounds.getSouthWest(), bounds.getNorthEast())
    setDrawGeom({ type: 'polygon', coordinates: coords, area_sqkm: area })
    autoSetSavePath('polygon')
    polyMarkersRef.current.forEach(m => m.remove())
    polyMarkersRef.current = []
    if (polyLineRef.current) {
      mapRef.current.removeLayer(polyLineRef.current)
      polyLineRef.current = null
    }
    mapRef.current.dragging.enable()
  }, [autoSetSavePath])

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const map = L.map(containerRef.current, {
      center: [39.9, 116.4],
      zoom: 10,
      zoomControl: false,
      doubleClickZoom: false,
    })

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '',
      maxZoom: 19,
    }).addTo(map)

    L.control.zoom({ position: 'bottomleft' }).addTo(map)

    const drawnItems = new L.FeatureGroup()
    map.addLayer(drawnItems)
    drawnItemsRef.current = drawnItems
    mapRef.current = map

    map.on('mousedown', (e: L.LeafletMouseEvent) => {
      if (toolRef.current !== 'draw') return
      if (!e.originalEvent.ctrlKey) return
      const shape = drawShapeRef.current
      if (shape === 'rect' || shape === 'circle') {
        drawingRef.current = true
        startPosRef.current = e.latlng
        map.dragging.disable()
      }
    })

    map.on('mousemove', (e: L.LeafletMouseEvent) => {
      if (!drawingRef.current || !startPosRef.current) return
      const shape = drawShapeRef.current

      if (shape === 'rect') {
        const bounds = L.latLngBounds(startPosRef.current, e.latlng)
        if (tempLayerRef.current) {
          (tempLayerRef.current as L.Rectangle).setBounds(bounds)
        } else {
          tempLayerRef.current = L.rectangle(bounds, {
            color: '#1d4ed8',
            weight: 2,
            dashArray: '6 3',
            fillOpacity: 0.1,
          }).addTo(map)
        }
      }

      if (shape === 'circle') {
        const radius = startPosRef.current.distanceTo(e.latlng)
        if (tempLayerRef.current) {
          (tempLayerRef.current as L.Circle).setRadius(radius)
        } else {
          tempLayerRef.current = L.circle(startPosRef.current, {
            radius,
            color: '#c27803',
            weight: 2,
            dashArray: '6 3',
            fillOpacity: 0.1,
          }).addTo(map)
        }
      }

      if (shape === 'polygon' && polyPointsRef.current.length > 0) {
        const pts = [...polyPointsRef.current, e.latlng]
        if (polyLineRef.current) {
          polyLineRef.current.setLatLngs(pts)
        } else {
          polyLineRef.current = L.polyline(pts, {
            color: '#15803d',
            weight: 2,
            dashArray: '6 3',
          }).addTo(map)
        }
      }
    })

    map.on('mouseup', (e: L.LeafletMouseEvent) => {
      if (!drawingRef.current || !startPosRef.current) return
      drawingRef.current = false

      const shape = drawShapeRef.current
      if (tempLayerRef.current) {
        map.removeLayer(tempLayerRef.current)
        tempLayerRef.current = null
      }

      if (shape === 'rect') {
        finishRect(startPosRef.current, e.latlng)
      } else if (shape === 'circle') {
        finishCircle(startPosRef.current, e.latlng)
      }
      startPosRef.current = null
    })

    map.on('click', (e: L.LeafletMouseEvent) => {
      if (toolRef.current !== 'draw' || drawShapeRef.current !== 'polygon') return
      if (!e.originalEvent.ctrlKey) return
      map.dragging.disable()
      const pt = e.latlng
      polyPointsRef.current.push(pt)
      const marker = L.circleMarker(pt, { radius: 4, color: '#15803d', fillColor: '#15803d', fillOpacity: 1 }).addTo(map)
      polyMarkersRef.current.push(marker)
    })

    map.on('dblclick', () => {
      if (toolRef.current !== 'draw' || drawShapeRef.current !== 'polygon') return
      finishPolygon()
    })

    return () => {
      map.remove()
      mapRef.current = null
      drawnItemsRef.current = null
    }
  }, [finishRect, finishCircle, finishPolygon])

  const handleOutputFormatChange = (value: string) => {
    setOutputFormat(value)
    outputFormatRef.current = value
    if (!drawGeom) return
    const basePath = defaultSavePath || 'outdata'
    const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
    const ext = value === 'xml' ? '.osm' : '.json'
    setSavePath(basePath + '/draw_' + ts + ext)
  }

  const queryPreview = getQueryPreview()

  return (
    <div className="relative h-screen min-h-[640px] overflow-hidden">
      <div ref={containerRef} className="absolute inset-0" />

      <div className="absolute left-4 top-4 z-[1000] flex w-[260px] flex-col gap-3">
        <section className="ui-panel overflow-hidden rounded-lg">
          <div className="border-b border-slate-200/80 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-400">下载范围</p>
          </div>
          <div className="p-2">
            {TOOL_ITEMS.map(t => {
              const Icon = t.icon
              const active = tool === t.key
              return (
                <button
                  key={t.key}
                  className={`flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left transition ${
                    active ? 'bg-[var(--primary)] text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100'
                  }`}
                  onClick={() => handleToolChange(t.key)}
                >
                  <Icon size={17} className="shrink-0" />
                  <span className="min-w-0">
                    <span className="block text-sm font-medium">{t.label}</span>
                    <span className={`block truncate text-xs ${active ? 'text-white/75' : 'text-slate-400'}`}>{t.desc}</span>
                  </span>
                </button>
              )
            })}
          </div>
        </section>

        {tool === 'draw' && (
          <section className="ui-panel rounded-lg p-2">
            <div className="grid grid-cols-3 gap-1.5">
              {DRAW_SHAPES.map(s => {
                const Icon = s.icon
                const active = drawShape === s.key
                return (
                  <button
                    key={s.key}
                    className={`flex h-16 flex-col items-center justify-center gap-1 rounded-md text-xs font-medium transition ${
                      active ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'
                    }`}
                    onClick={() => handleDrawShapeChange(s.key)}
                    title={s.title}
                  >
                    <Icon size={17} />
                    {s.label}
                  </button>
                )
              })}
            </div>
            <div className="mt-2 flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-500">
              <span>
                {drawShape === 'rect' && '按住 Ctrl 并拖拽绘制矩形'}
                {drawShape === 'circle' && '按住 Ctrl 从圆心拖拽'}
                {drawShape === 'polygon' && 'Ctrl 单击加点，双击结束'}
              </span>
              <button
                className="rounded p-1 text-slate-400 hover:bg-white hover:text-red-600"
                onClick={() => { drawnItemsRef.current?.clearLayers(); setDrawGeom(null); clearDrawing() }}
                title="清除绘制"
              >
                <Eraser size={15} />
              </button>
            </div>
          </section>
        )}
      </div>

      {regionPanelOpen && tool === 'region' && (
        <section className="ui-panel absolute left-[288px] top-4 z-[1000] flex max-h-[68vh] w-80 flex-col overflow-hidden rounded-lg">
          <div className="flex items-center justify-between border-b border-slate-200/80 px-4 py-3">
            <div>
              <h2 className="text-sm font-semibold">Geofabrik 数据</h2>
              <p className="text-xs text-slate-400">选择一个可下载区域</p>
            </div>
            <button className="rounded-md p-2 text-slate-500 hover:bg-slate-100" onClick={refreshRegions} disabled={geoRefreshing} title="更新区域">
              <RefreshCw size={15} className={geoRefreshing ? 'animate-spin' : ''} />
            </button>
          </div>
          <div className="min-h-0 flex-1 overflow-auto p-2">
            <RegionTree regions={geoRegions} selectedId={geoSelected?.id ?? null} onSelect={handleGeoSelect} />
          </div>
        </section>
      )}

      {tool === 'import' && (
        <section className="ui-panel absolute left-[288px] top-4 z-[1000] w-80 overflow-hidden rounded-lg">
          <button
            className="flex w-full flex-col items-center justify-center p-7 text-center transition hover:bg-slate-50"
            onClick={() => fileInputRef.current?.click()}
          >
            {importLoading ? (
              <>
                <Loader2 className="mb-3 animate-spin text-[var(--primary)]" size={28} />
                <p className="text-sm font-medium">正在解析文件</p>
                <p className="mt-1 text-xs text-slate-400">请稍候，完成后会自动定位到范围</p>
              </>
            ) : importResult ? (
              <>
                <Database className="mb-3 text-emerald-600" size={28} />
                <p className="text-sm font-medium text-emerald-700">解析成功</p>
                <p className="mt-1 text-xs text-slate-500">
                  {importResult.area_sqkm} km² · {importResult.bbox.left.toFixed(2)} 至 {importResult.bbox.right.toFixed(2)}
                </p>
                <p className="mt-3 text-xs text-[var(--primary)]">点击重新上传</p>
              </>
            ) : (
              <>
                <FileUp className="mb-3 text-[var(--primary)]" size={30} />
                <p className="text-sm font-medium">上传矢量文件</p>
                <p className="mt-1 text-xs text-slate-400">支持 GeoJSON / Shapefile / KML / GPKG</p>
              </>
            )}
          </button>
          <input ref={fileInputRef} type="file" className="hidden" accept=".geojson,.json,.kml,.gpkg,.zip,.shp" onChange={handleFileUpload} />
        </section>
      )}

      <section className="ui-panel absolute right-4 top-4 z-[1000] w-80 overflow-hidden rounded-lg">
        <div className="border-b border-slate-200/80 px-4 py-3">
          <h2 className="text-sm font-semibold">下载设置</h2>
          <p className="mt-0.5 text-xs text-slate-400">确认范围、格式和保存位置</p>
        </div>
        <div className="space-y-3 p-4">
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-lg bg-slate-50 p-3">
              <p className="text-xs text-slate-400">范围大小</p>
              <p className="mt-1 text-sm font-semibold">{getAreaDisplay()}</p>
            </div>
            <div className="rounded-lg bg-slate-50 p-3">
              <p className="text-xs text-slate-400">数据源</p>
              <p className="mt-1 truncate text-sm font-semibold">
                {tool === 'region' ? (geoSelected?.name ?? '未选择') : tool === 'import' ? '导入范围' : 'Overpass'}
              </p>
            </div>
          </div>

          {drawGeom?.type === 'circle' && (
            <p className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-700">
              圆形半径 {(drawGeom.radius! / 1000).toFixed(1)} km
            </p>
          )}

          <label className="block">
            <span className="mb-1.5 block text-xs font-medium text-slate-500">输出格式</span>
            <select className="ui-field w-full rounded-lg px-3 py-2 text-sm" value={outputFormat} onChange={e => handleOutputFormatChange(e.target.value)}>
              <option value="json">JSON</option>
              <option value="xml">XML</option>
            </select>
          </label>

          <label className="block">
            <span className="mb-1.5 block text-xs font-medium text-slate-500">保存路径</span>
            <FileSelector
              value={savePath}
              onChange={setSavePath}
              mode="save_file"
              fileTypes={[{ label: 'PBF', ext: '*.pbf' }, { label: 'JSON', ext: '*.json' }, { label: 'OSM', ext: '*.osm' }]}
            />
          </label>

          {queryPreview && (
            <details className="rounded-lg border border-slate-200 bg-slate-50">
              <summary className="cursor-pointer px-3 py-2 text-xs font-medium text-slate-500">查询预览</summary>
              <pre className="max-h-32 overflow-auto border-t border-slate-200 px-3 py-2 text-[11px] leading-5 text-slate-600">{queryPreview}</pre>
            </details>
          )}

          <button
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[var(--primary)] px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#185947] disabled:bg-slate-300 disabled:text-white"
            onClick={startDownload}
            disabled={!canDownload()}
            title={!savePath ? '请先选择保存路径' : !canDownload() ? '请先选择下载范围' : ''}
          >
            <Download size={17} />
            {tool === 'region' && geoSelected ? '下载 Geofabrik 数据' : '查询并下载'}
          </button>
        </div>
      </section>

      <div className="absolute bottom-0 left-0 right-0 z-[1000]">
        <section className="ui-panel mx-4 mb-4 overflow-hidden rounded-lg">
          <button
            className="flex w-full items-center justify-between px-4 py-3 text-sm transition hover:bg-slate-50"
            onClick={() => setTaskPanelOpen(!taskPanelOpen)}
          >
            <span className="flex items-center gap-2 font-semibold">
              下载任务
              {tasks.length > 0 && (
                <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-[var(--primary)] px-1.5 text-xs font-semibold text-white">
                  {tasks.length}
                </span>
              )}
            </span>
            <span className="inline-flex items-center gap-1 text-xs text-slate-400">
              {taskPanelOpen ? '收起' : '展开'}
              {taskPanelOpen ? <ChevronDown size={15} /> : <ChevronUp size={15} />}
            </span>
          </button>
          {taskPanelOpen && (
            <div className="max-h-72 overflow-auto border-t border-slate-200/80 p-3">
              <TaskTable tasks={tasks} onCancel={id => downloadApi.cancelTask(id)} onDelete={id => downloadApi.deleteTask(id)} onRetry={id => downloadApi.retryTask(id)} />
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

function estimateArea(sw: L.LatLng, ne: L.LatLng): number {
  const latKm = (ne.lat - sw.lat) * 111
  const centerLat = (ne.lat + sw.lat) / 2
  const lngKm = (ne.lng - sw.lng) * 111 * Math.abs(Math.cos(centerLat * Math.PI / 180))
  return Math.round(latKm * lngKm * 100) / 100
}
