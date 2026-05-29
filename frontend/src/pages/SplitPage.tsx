import { useState } from 'react'
import { splitApi } from '../api'
import { useTasks } from '../hooks/useTasks'
import { FileSelector } from '../components/FileSelector'
import { TaskTable } from '../components/TaskTable'

export function SplitPage() {
  const { tasks } = useTasks('split')
  const [inputPath, setInputPath] = useState('')
  const [outputDir, setOutputDir] = useState('')
  const [splitType, setSplitType] = useState('admin')

  const handleSplit = async () => {
    if (!inputPath || !outputDir) return alert('请选择输入文件和输出目录')
    try {
      await splitApi.start({ input_path: inputPath, output_dir: outputDir, split_type: splitType })
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
            fileTypes={[{ label: 'OSM/PBF', ext: '*.pbf *.osm.pbf *.geojson' }]}
          />
        </div>

        <div className="mb-3">
          <label className="mb-1 block text-sm">拆分方式</label>
          <select
            className="rounded border border-[var(--input)] px-2 py-1.5 text-sm"
            value={splitType}
            onChange={e => setSplitType(e.target.value)}
          >
            <option value="admin">行政区拆分</option>
            <option value="range">范围拆分</option>
            <option value="attribute">属性拆分</option>
            <option value="type">类型拆分</option>
          </select>
        </div>

        <div className="mb-3">
          <label className="mb-1 block text-sm">输出目录</label>
          <FileSelector value={outputDir} onChange={setOutputDir} mode="open_dir" />
        </div>

        <button
          className="rounded bg-[var(--primary)] px-4 py-2 text-sm text-[var(--primary-foreground)] hover:opacity-90 disabled:opacity-50"
          onClick={handleSplit}
          disabled={!inputPath || !outputDir}
        >
          执行拆分
        </button>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-medium">任务列表</h3>
        <TaskTable tasks={tasks} />
      </div>
    </div>
  )
}
