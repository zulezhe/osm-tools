import { useState, useEffect } from 'react'
import { convertApi } from '../api'
import { useTasks } from '../hooks/useTasks'
import { FileSelector } from '../components/FileSelector'
import { TaskTable } from '../components/TaskTable'

export function ConvertPage() {
  const { tasks } = useTasks('convert')
  const [inputPath, setInputPath] = useState('')
  const [outputPath, setOutputPath] = useState('')
  const [outputFormat, setOutputFormat] = useState('geojson')
  const [formats, setFormats] = useState<string[]>([])

  useEffect(() => {
    convertApi.getFormats().then(setFormats).catch(() => {})
  }, [])

  const handleConvert = async () => {
    if (!inputPath || !outputPath) return alert('请选择输入和输出文件')
    try {
      await convertApi.start({ input_path: inputPath, output_path: outputPath, output_format: outputFormat })
    } catch (e: any) {
      alert(e.message)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded border border-[var(--border)] p-4">
        <h3 className="mb-3 text-sm font-medium">单文件转换</h3>
        <div className="flex flex-col gap-3">
          <div>
            <label className="mb-1 block text-sm">输入文件</label>
            <FileSelector
              value={inputPath}
              onChange={setInputPath}
              mode="open_file"
              fileTypes={[
                { label: '支持格式', ext: '*.pbf *.osm *.geojson *.json *.shp *.gpkg' },
              ]}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm">输出格式</label>
            <select
              className="rounded border border-[var(--input)] px-2 py-1.5 text-sm"
              value={outputFormat}
              onChange={e => setOutputFormat(e.target.value)}
            >
              {formats.map(f => <option key={f} value={f}>{f}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm">输出文件</label>
            <FileSelector value={outputPath} onChange={setOutputPath} mode="save_file" />
          </div>
          <button
            className="rounded bg-[var(--primary)] px-4 py-2 text-sm text-[var(--primary-foreground)] hover:opacity-90 disabled:opacity-50"
            onClick={handleConvert}
            disabled={!inputPath || !outputPath}
          >
            开始转换
          </button>
        </div>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-medium">转换历史</h3>
        <TaskTable tasks={tasks} />
      </div>
    </div>
  )
}
