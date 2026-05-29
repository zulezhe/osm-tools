import { useState, useCallback, useEffect } from 'react'
import { useSSE } from './useSSE'
import { downloadApi } from '../api'

interface Task {
  task_id: string
  task_type: string
  status: string
  progress: number
  error?: string
  params?: Record<string, any>
  result?: any
  downloaded_bytes?: number
  total_bytes?: number
  speed?: number
}

export function useTasks(taskType: string) {
  const [tasks, setTasks] = useState<Task[]>([])

  // 页面加载时拉取已有任务
  useEffect(() => {
    const fetchers: Record<string, () => Promise<any[]>> = {
      download: downloadApi.getTasks,
    }
    const fetcher = fetchers[taskType]
    if (fetcher) {
      fetcher().then(data => { if (data?.length) setTasks(data) }).catch(() => {})
    }
  }, [taskType])

  const handleEvent = useCallback((event: any) => {
    if (event.task_type === taskType) {
      setTasks(prev => {
        const idx = prev.findIndex(t => t.task_id === event.task_id)
        const task: Task = {
          task_id: event.task_id,
          task_type: event.task_type,
          status: event.status,
          progress: event.progress,
          error: event.error,
          params: event.params,
          result: event.result,
          downloaded_bytes: event.downloaded_bytes ?? 0,
          total_bytes: event.total_bytes ?? 0,
          speed: event.speed ?? 0,
        }
        if (idx >= 0) {
          const updated = [...prev]
          updated[idx] = task
          return updated
        }
        return [task, ...prev]
      })
    }
  }, [taskType])

  const { connected } = useSSE(handleEvent)

  return { tasks, connected }
}
