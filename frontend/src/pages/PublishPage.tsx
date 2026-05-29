import { useState } from 'react'
import { publishApi } from '../api'
import { useTasks } from '../hooks/useTasks'
import { FileSelector } from '../components/FileSelector'
import { TaskTable } from '../components/TaskTable'

export function PublishPage() {
  const { tasks } = useTasks('publish')
  const [inputPath, setInputPath] = useState('')
  const [outputPath, setOutputPath] = useState('')
  const [minzoom, setMinzoom] = useState(0)
  const [maxzoom, setMaxzoom] = useState(14)
  const [outputFormat, setOutputFormat] = useState('mbtiles')
  const [simplify, setSimplify] = useState(true)

  const handlePublish = async () => {
    if (!inputPath || !outputPath) return alert('请选择输入和输出')
    try {
      await publishApi.start({
        input_path: inputPath,
        output_path: outputPath,
        config: { minzoom, maxzoom, output_format: outputFormat, simplify },
      })
    } catch (e: any) {
      alert(e.message)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded border border-[var(--border)] p-4">
        <div className="mb-3">
          <label className="mb-1 block text-sm">输入文件</label>
          <FileSelector
            value={inputPath}
            onChange={setInputPath}
            mode="open_file"
            fileTypes={[{ label: 'GeoJSON/PBF', ext: '*.geojson *.pbf' }]}
          />
        </div>

        <div className="mb-3 grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-sm">最小缩放</label>
            <input
              type="number"
              min={0} max={22}
              className="w-full rounded border border-[var(--input)] bg-white px-3 py-1.5 text-sm outline-none"
              value={minzoom}
              onChange={e => setMinzoom(parseInt(e.target.value))}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm">最大缩放</label>
            <input
              type="number"
              min={0} max={22}
              className="w-full rounded border border-[var(--input)] bg-white px-3 py-1.5 text-sm outline-none"
              value={maxzoom}
              onChange={e => setMaxzoom(parseInt(e.target.value))}
            />
          </div>
        </div>

        <div className="mb-3 grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-sm">输出格式</label>
            <select
              className="rounded border border-[var(--input)] px-2 py-1.5 text-sm"
              value={outputFormat}
              onChange={e => setOutputFormat(e.target.value)}
            >
              <option value="mbtiles">MBTiles</option>
              <option value="mvt_dir">MVT 目录</option>
              <option value="geojson_tiles">GeoJSON 切片</option>
            </select>
          </div>
          <div className="flex items-end gap-2">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={simplify} onChange={e => setSimplify(e.target.checked)} />
              自动简化
            </label>
          </div>
        </div>

        <div className="mb-3">
          <label className="mb-1 block text-sm">输出路径</label>
          <FileSelector
            value={outputPath}
            onChange={setOutputPath}
            mode={outputFormat === 'mbtiles' ? 'save_file' : 'open_dir'}
            fileTypes={[{ label: 'MBTiles', ext: '*.mbtiles' }]}
          />
        </div>

        <button
          className="rounded bg-[var(--primary)] px-4 py-2 text-sm text-[var(--primary-foreground)] hover:opacity-90 disabled:opacity-50"
          onClick={handlePublish}
          disabled={!inputPath || !outputPath}
        >
          生成切片
        </button>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-medium">任务列表</h3>
        <TaskTable tasks={tasks} />
      </div>
    </div>
  )
}
