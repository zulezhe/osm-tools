import { RefreshCw, Trash2, XCircle } from 'lucide-react'

interface Task {
  task_id: string
  status: string
  progress: number
  error?: string
  params?: Record<string, unknown>
  result?: unknown
  downloaded_bytes?: number
  total_bytes?: number
  speed?: number
}

interface Props {
  tasks: Task[]
  onCancel?: (id: string) => void
  onDelete?: (id: string) => void
  onRetry?: (id: string) => void
  columns?: Array<{ key: string; label: string; render?: (task: Task) => React.ReactNode }>
}

function formatBytes(bytes: number): string {
  if (bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

function formatSpeed(bytesPerSec: number): string {
  if (bytesPerSec <= 0) return ''
  return `${formatBytes(bytesPerSec)}/s`
}

function formatETA(downloaded: number, total: number, speed: number): string {
  if (speed <= 0 || total <= 0 || downloaded >= total) return ''
  const remaining = (total - downloaded) / speed
  if (remaining < 60) return `${Math.ceil(remaining)} 秒`
  if (remaining < 3600) return `${Math.ceil(remaining / 60)} 分钟`
  return `${(remaining / 3600).toFixed(1)} 小时`
}

const STATUS_LABELS: Record<string, string> = {
  pending: '等待中',
  downloading: '下载中',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
}

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-slate-100 text-slate-600',
  downloading: 'bg-blue-50 text-blue-700',
  running: 'bg-blue-50 text-blue-700',
  completed: 'bg-emerald-50 text-emerald-700',
  failed: 'bg-red-50 text-red-700',
  cancelled: 'bg-slate-100 text-slate-500',
}

export function TaskTable({ tasks, onCancel, onDelete, onRetry, columns }: Props) {
  const defaultColumns = [
    {
      key: 'task_id',
      label: '任务',
      render: (t: Task) => (
        <div className="max-w-[220px] truncate font-mono text-xs text-slate-600" title={t.task_id}>
          {t.task_id}
        </div>
      ),
    },
    {
      key: 'progress',
      label: '进度',
      render: (t: Task) => {
        const dl = t.downloaded_bytes ?? 0
        const total = t.total_bytes ?? 0
        const speed = t.speed ?? 0
        return (
          <div className="flex min-w-[180px] flex-col gap-1.5">
            <div className="flex items-center gap-2">
              <div className="h-2 w-28 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-[var(--primary)] transition-all"
                  style={{ width: `${Math.min(Math.max(t.progress, 0), 100)}%` }}
                />
              </div>
              <span className="w-12 text-right text-xs tabular-nums text-slate-500">{t.progress.toFixed(1)}%</span>
            </div>
            {(dl > 0 || total > 0 || speed > 0) && (
              <div className="text-xs text-slate-500">
                {dl > 0 || total > 0 ? `${formatBytes(dl)}${total > 0 ? ` / ${formatBytes(total)}` : ''}` : ''}
                {speed > 0 ? ` · ${formatSpeed(speed)}` : ''}
                {speed > 0 && dl > 0 && total > 0 ? ` · 剩余 ${formatETA(dl, total, speed)}` : ''}
              </div>
            )}
          </div>
        )
      },
    },
    {
      key: 'status',
      label: '状态',
      render: (t: Task) => (
        <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${STATUS_STYLES[t.status] ?? 'bg-slate-100 text-slate-600'}`}>
          {STATUS_LABELS[t.status] || t.status}
        </span>
      ),
    },
    {
      key: 'actions',
      label: '操作',
      render: (t: Task) => {
        const isActive = t.status === 'downloading' || t.status === 'pending' || t.status === 'running'
        const canRetry = t.status === 'failed' || t.status === 'cancelled'
        const canDelete = t.status === 'completed' || t.status === 'failed' || t.status === 'cancelled'
        return (
          <div className="flex justify-end gap-1.5">
            {isActive && (
              <button className="rounded-md p-1.5 text-red-600 hover:bg-red-50" onClick={() => onCancel?.(t.task_id)} title="取消">
                <XCircle size={15} />
              </button>
            )}
            {canRetry && (
              <button className="rounded-md p-1.5 text-blue-600 hover:bg-blue-50" onClick={() => onRetry?.(t.task_id)} title="重试">
                <RefreshCw size={15} />
              </button>
            )}
            {canDelete && (
              <button className="rounded-md p-1.5 text-slate-500 hover:bg-red-50 hover:text-red-600" onClick={() => onDelete?.(t.task_id)} title="删除">
                <Trash2 size={15} />
              </button>
            )}
          </div>
        )
      },
    },
  ]

  const cols = columns ?? defaultColumns

  return (
    <div className="overflow-hidden rounded-lg border border-[var(--border)] bg-white">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--border)] bg-slate-50/80">
            {cols.map(c => (
              <th key={c.key} className="px-3 py-2.5 text-left text-xs font-semibold text-slate-500">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tasks.length === 0 && (
            <tr>
              <td colSpan={cols.length} className="px-3 py-10 text-center text-sm text-slate-400">
                暂无任务
              </td>
            </tr>
          )}
          {tasks.map(t => (
            <tr key={t.task_id} className="border-b border-[var(--border)] last:border-0 hover:bg-slate-50/60">
              {cols.map(c => (
                <td key={c.key} className="px-3 py-2.5 align-middle">
                  {c.render ? c.render(t) : String((t as unknown as Record<string, unknown>)[c.key] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
