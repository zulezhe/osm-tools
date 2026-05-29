import { useEffect, useRef, useState } from 'react'

interface SSEEvent {
  type: string
  task_id: string
  task_type: string
  status: string
  progress: number
  error?: string
}

export function useSSE(onEvent: (event: SSEEvent) => void) {
  const esRef = useRef<EventSource | null>(null)
  const [connected, setConnected] = useState(false)
  const callbackRef = useRef(onEvent)
  callbackRef.current = onEvent

  useEffect(() => {
    const es = new EventSource('/api/v1/events')
    esRef.current = es

    es.onopen = () => setConnected(true)
    es.onerror = () => setConnected(false)

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        callbackRef.current(data)
      } catch { /* ignore parse errors */ }
    }

    return () => {
      es.close()
      esRef.current = null
    }
  }, [])

  return { connected }
}
