import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet-draw/dist/leaflet.draw.css'
import 'leaflet-draw'

export interface DrawGeometry {
  type: 'bbox' | 'polygon' | 'circle'
  bbox?: { left: number; bottom: number; right: number; top: number }
  coordinates?: number[][]  // [[lng,lat], ...] for polygon
  center_lat?: number
  center_lng?: number
  radius?: number  // meters
  area_sqkm?: number
  geojson?: any
}

interface Props {
  onGeometryChange: (geom: DrawGeometry | null) => void
  height?: string
  drawMode?: 'rectangle' | 'polygon' | 'circle' | 'all'
}

export function DrawMap({ onGeometryChange, height = '400px', drawMode = 'all' }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const drawnItemsRef = useRef<L.FeatureGroup | null>(null)

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const map = L.map(containerRef.current, {
      center: [39.9, 116.4],
      zoom: 10,
    })

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OSM contributors',
      maxZoom: 19,
    }).addTo(map)

    const drawnItems = new L.FeatureGroup()
    map.addLayer(drawnItems)
    drawnItemsRef.current = drawnItems

    // 构建绘制控件选项
    const drawOptions: any = {
      position: 'topright',
      draw: {
        polyline: false,
        marker: false,
        circlemarker: false,
      },
      edit: {
        featureGroup: drawnItems,
        remove: true,
      },
    }

    if (drawMode === 'all' || drawMode === 'rectangle') {
      drawOptions.draw.rectangle = {
        shapeOptions: { color: '#3b82f6', weight: 2, fillOpacity: 0.15 },
      }
    }
    if (drawMode === 'all' || drawMode === 'polygon') {
      drawOptions.draw.polygon = {
        shapeOptions: { color: '#10b981', weight: 2, fillOpacity: 0.15 },
        allowIntersection: false,
      }
    }
    if (drawMode === 'all' || drawMode === 'circle') {
      drawOptions.draw.circle = {
        shapeOptions: { color: '#f59e0b', weight: 2, fillOpacity: 0.15 },
      }
    }

    const drawControl = new (L.Control as any).Draw(drawOptions)
    map.addControl(drawControl)

    // 绘制完成事件
    map.on((L as any).Draw.Event.CREATED, (e: any) => {
      drawnItems.clearLayers()
      const layer = e.layer
      drawnItems.addLayer(layer)
      const geom = layerToGeometry(layer, e.layerType)
      onGeometryChange(geom)
    })

    // 编辑/删除事件
    map.on((L as any).Draw.Event.DELETED, () => {
      onGeometryChange(null)
    })

    mapRef.current = map

    return () => {
      map.remove()
      mapRef.current = null
      drawnItemsRef.current = null
    }
  }, [drawMode, onGeometryChange])

  return (
    <div className="relative rounded border border-[var(--border)] overflow-hidden">
      <div ref={containerRef} style={{ height }} />
      <div className="absolute bottom-2 left-2 rounded bg-white/90 px-2 py-1 text-xs text-gray-600 shadow">
        使用右上角工具绘制选区
      </div>
    </div>
  )
}

function layerToGeometry(layer: any, layerType: string): DrawGeometry {
  if (layerType === 'rectangle') {
    const bounds = layer.getBounds()
    const sw = bounds.getSouthWest()
    const ne = bounds.getNorthEast()
    const area = _estimateBboxArea(sw, ne)
    return {
      type: 'bbox',
      bbox: { left: sw.lng, bottom: sw.lat, right: ne.lng, top: ne.lat },
      area_sqkm: area,
    }
  } else if (layerType === 'polygon') {
    const latlngs = layer.getLatLngs()[0]
    const coords = latlngs.map((ll: any) => [ll.lng, ll.lat])
    // 关闭多边形
    coords.push(coords[0])
    const bounds = layer.getBounds()
    const area = _estimateBboxArea(bounds.getSouthWest(), bounds.getNorthEast())
    return {
      type: 'polygon',
      coordinates: coords,
      area_sqkm: area,
    }
  } else if (layerType === 'circle') {
    const center = layer.getLatLng()
    const radius = layer.getRadius()
    const area = Math.PI * (radius / 1000) ** 2
    return {
      type: 'circle',
      center_lat: center.lat,
      center_lng: center.lng,
      radius: Math.round(radius),
      area_sqkm: Math.round(area * 100) / 100,
    }
  }
  return { type: 'bbox' }
}

function _estimateBboxArea(sw: any, ne: any): number {
  const lat_km = (ne.lat - sw.lat) * 111
  const center_lat = (ne.lat + sw.lat) / 2
  const lng_km = (ne.lng - sw.lng) * 111 * Math.abs(Math.cos(center_lat * Math.PI / 180))
  return Math.round(lat_km * lng_km * 100) / 100
}
