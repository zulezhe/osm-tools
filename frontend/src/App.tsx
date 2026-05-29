import { useState, type ReactNode } from 'react'
import {
  ArrowDownToLine,
  Boxes,
  FileOutput,
  Globe2,
  Layers3,
  PackageOpen,
  Scissors,
  SlidersHorizontal,
} from 'lucide-react'
import { DownloadPage } from './pages/DownloadPage'
import { ExtractPage } from './pages/ExtractPage'
import { ConvertPage } from './pages/ConvertPage'
import { SplitPage } from './pages/SplitPage'
import { ProcessPage } from './pages/ProcessPage'
import { PublishPage } from './pages/PublishPage'

type PageKey = 'download' | 'extract' | 'split' | 'process' | 'convert' | 'publish'

const NAV_ITEMS: Array<{
  key: PageKey
  label: string
  desc: string
  icon: typeof ArrowDownToLine
}> = [
  { key: 'download', label: '下载', desc: '区域与 Overpass', icon: ArrowDownToLine },
  { key: 'extract', label: '提取', desc: '字段过滤', icon: Scissors },
  { key: 'split', label: '分割', desc: '行政区与属性', icon: Layers3 },
  { key: 'process', label: '处理', desc: '压缩与简化', icon: SlidersHorizontal },
  { key: 'convert', label: '转换', desc: '格式转换', icon: FileOutput },
  { key: 'publish', label: '发布', desc: '矢量切片', icon: PackageOpen },
]

const PAGES: Record<PageKey, () => ReactNode> = {
  download: DownloadPage,
  extract: ExtractPage,
  split: SplitPage,
  process: ProcessPage,
  convert: ConvertPage,
  publish: PublishPage,
}

export default function App() {
  const [page, setPage] = useState<PageKey>('download')
  const PageComponent = PAGES[page]

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--background)] text-[var(--foreground)]">
      <nav className="flex w-64 shrink-0 flex-col border-r border-[var(--border)] bg-white/88 shadow-[4px_0_32px_rgba(15,23,42,0.05)]">
        <div className="border-b border-[var(--border)] px-5 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--primary)] text-white shadow-sm">
              <Globe2 size={20} />
            </div>
            <div>
              <h1 className="text-base font-semibold leading-5">OSM Tool</h1>
              <p className="mt-0.5 text-xs text-[var(--muted-foreground)]">地图数据工作台</p>
            </div>
          </div>
        </div>

        <div className="flex-1 px-3 py-4">
          <p className="px-2 pb-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">
            工作流
          </p>
          <div className="space-y-1">
            {NAV_ITEMS.map(item => {
              const Icon = item.icon
              const active = page === item.key
              return (
                <button
                  key={item.key}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition ${
                    active
                      ? 'bg-[var(--primary)] text-white shadow-sm'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950'
                  }`}
                  onClick={() => setPage(item.key)}
                >
                  <Icon size={18} className="shrink-0" />
                  <span className="min-w-0">
                    <span className="block text-sm font-medium leading-5">{item.label}</span>
                    <span className={`block truncate text-xs ${active ? 'text-white/78' : 'text-slate-400'}`}>
                      {item.desc}
                    </span>
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        <div className="border-t border-[var(--border)] px-5 py-4">
          <div className="flex items-center gap-2 text-xs text-[var(--muted-foreground)]">
            <Boxes size={14} />
            <span>本地处理 · 可视化下载</span>
          </div>
        </div>
      </nav>

      <main className="min-w-0 flex-1 overflow-auto">
        <PageComponent />
      </main>
    </div>
  )
}
