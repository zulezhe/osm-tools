import { FolderOpen } from 'lucide-react'
import { systemApi } from '../api'
import type { ChangeEvent } from 'react'

interface Props {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  mode?: 'open_file' | 'save_file' | 'open_dir'
  title?: string
  fileTypes?: Array<{ label: string; ext: string }>
}

const DEFAULT_PLACEHOLDER: Record<NonNullable<Props['mode']>, string> = {
  open_file: '选择或输入文件路径',
  save_file: '选择或输入保存路径',
  open_dir: '选择或输入目录路径',
}

export function FileSelector({
  value,
  onChange,
  placeholder,
  mode = 'open_file',
  title,
  fileTypes,
}: Props) {
  const handleBrowse = async () => {
    try {
      const { path } = await systemApi.fileDialog({ mode, title, file_types: fileTypes })
      if (path) onChange(path)
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div className="flex min-w-0 flex-1 gap-2">
      <input
        type="text"
        className="ui-field min-w-0 flex-1 rounded-lg px-3 py-2 text-sm placeholder:text-slate-400"
        value={value}
        onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value)}
        placeholder={placeholder ?? DEFAULT_PLACEHOLDER[mode]}
      />
      <button
        className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50"
        onClick={handleBrowse}
        title="浏览"
      >
        <FolderOpen size={15} />
        浏览
      </button>
    </div>
  )
}
