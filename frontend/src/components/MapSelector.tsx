import { useEffect, useRef, useCallback } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

interface BBox {
  left: number
  bottom: number
  right: number
  top: number
}

interface Props {
  bbox: BBox
  onBboxChange: (bbox: BBox) => void
  height?: string
}

export function MapSelector({ bbox, onBboxChange, height = '400px' }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const rectRef = useRef<L.Rectangle | null>(null)
  const drawingRef = useRef(false)
  const startLatLngRef = useRef<L.LatLng | null>(null)
  const tempRectRef = useRef<L.Rectangle | null>(null)
  // 保存最新的 bbox 和 onBboxChange 到 ref，避免闭包问题
  const bboxRef = useRef(bbox)
  const onBboxChangeRef = useRef(onBboxChange)
  bboxRef.current = bbox
  onBboxChangeRef.current = onBboxChange

  const updateRect = useCallback((b: BBox) => {
    if (!mapRef.current) return
    const bounds = L.latLngBounds(
      [b.bottom, b.left],
      [b.top, b.right]
    )
    if (rectRef.current) {
      rectRef.current.setBounds(bounds)
    } else {
      rectRef.current = L.rectangle(bounds, {
        color: '#3b82f6',
        weight: 2,
        fillOpacity: 0.15,
      }).addTo(mapRef.current)
    }
  }, [])

  // 初始化地图
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const map = L.map(containerRef.current, {
      center: [39.9, 116.4],
      zoom: 10,
    })

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(map)

    mapRef.current = map

    // 绘制初始矩形
    updateRect(bboxRef.current)

    // 鼠标绘制事件
    map.on('mousedown', (e: L.LeafletMouseEvent) => {
      // 仅在非输入框区域触发
      drawingRef.current = true
      startLatLngRef.current = e.latlng
      if (tempRectRef.current) {
        map.removeLayer(tempRectRef.current)
        tempRectRef.current = null
      }
      map.dragging.disable()
    })

    map.on('mousemove', (e: L.LeafletMouseEvent) => {
      if (!drawingRef.current || !startLatLngRef.current) return
      const bounds = L.latLngBounds(startLatLngRef.current, e.latlng)
      if (tempRectRef.current) {
        tempRectRef.current.setBounds(bounds)
      } else {
        tempRectRef.current = L.rectangle(bounds, {
          color: '#ef4444',
          weight: 2,
          dashArray: '6 3',
          fillOpacity: 0.1,
        }).addTo(map)
      }
    })

    map.on('mouseup', (e: L.LeafletMouseEvent) => {
      if (!drawingRef.current || !startLatLngRef.current) return
      drawingRef.current = false
      map.dragging.enable()

      if (tempRectRef.current) {
        map.removeLayer(tempRectRef.current)
        tempRectRef.current = null
      }

      const sw = startLatLngRef.current
      const ne = e.latlng
      const newBbox: BBox = {
        left: Math.min(sw.lng, ne.lng),
        bottom: Math.min(sw.lat, ne.lat),
        right: Math.max(sw.lng, ne.lng),
        top: Math.max(sw.lat, ne.lat),
      }
      onBboxChangeRef.current(newBbox)
      startLatLngRef.current = null
    })

    return () => {
      map.remove()
      mapRef.current = null
      rectRef.current = null
    }
  }, [updateRect])

  // 当外部 bbox 变化时更新矩形
  useEffect(() => {
    updateRect(bbox)
  }, [bbox, updateRect])

  return (
    <div className="relative rounded border border-[var(--border)] overflow-hidden">
      <div ref={containerRef} style={{ height }} />
      <div className="absolute bottom-2 left-2 rounded bg-white/90 px-2 py-1 text-xs text-gray-600 shadow">
        在地图上拖拽框选区域
      </div>
    </div>
  )
}
