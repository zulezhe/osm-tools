import { useState } from 'react'
import { processApi } from '../api'
import { useTasks } from '../hooks/useTasks'
import { FileSelector } from '../components/FileSelector'
import { TaskTable } from '../components/TaskTable'

const STEP_TYPES = [
  { value: 'compress', label: '压缩', defaultParams: { level: 6 } },
  { value: 'transform', label: '坐标转换', defaultParams: { target_crs: 'EPSG:3857' } },
  { value: 'simplify', label: '抽稀', defaultParams: { algorithm: 'dp', tolerance: 1.0 } },
  { value: 'field_remove', label: '字段删除', defaultParams: { fields: [] } },
]

export function ProcessPage() {
  const { tasks } = useTasks('process')
  const [inputPath, setInputPath] = useState('')
  const [outputPath, setOutputPath] = useState('')
  const [steps, setSteps] = useState<Array<{ type: string; params: any }>>([])

  const addStep = (type: string) => {
    const def = STEP_TYPES.find(s => s.value === type)
    if (def) setSteps([...steps, { type, params: { ...def.defaultParams } }])
  }

  const removeStep = (idx: number) => {
    setSteps(steps.filter((_, i) => i !== idx))
  }

  const handleProcess = async () => {
    if (!inputPath || !outputPath || steps.length === 0) return alert('请填写完整信息')
    try {
      await processApi.start({ input_path: inputPath, output_path: outputPath, steps })
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
            fileTypes={[{ label: 'GeoJSON', ext: '*.geojson *.json' }]}
          />
        </div>

        <div className="mb-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium">处理管道</span>
            <select
              className="rounded border border-[var(--input)] px-2 py-1 text-xs"
              onChange={e => { addStep(e.target.value); e.target.value = '' }}
              defaultValue=""
            >
              <option value="" disabled>添加步骤...</option>
              {STEP_TYPES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>
          {steps.length === 0 && <p className="py-2 text-center text-sm text-[var(--muted-foreground)]">点击上方添加处理步骤</p>}
          {steps.map((step, idx) => (
            <div key={idx} className="mb-1 flex items-center justify-between rounded border border-[var(--border)] px-3 py-2 text-sm">
              <span>{idx + 1}. {STEP_TYPES.find(s => s.value === step.type)?.label}</span>
              <button className="text-xs text-red-500 hover:underline" onClick={() => removeStep(idx)}>移除</button>
            </div>
          ))}
          {steps.length > 0 && (
            <button className="mt-1 text-xs text-[var(--muted-foreground)] hover:underline" onClick={() => setSteps([])}>清空管道</button>
          )}
        </div>

        <div className="mb-3">
          <label className="mb-1 block text-sm">输出文件</label>
          <FileSelector value={outputPath} onChange={setOutputPath} mode="save_file" fileTypes={[{ label: 'GeoJSON', ext: '*.geojson' }]} />
        </div>

        <button
          className="rounded bg-[var(--primary)] px-4 py-2 text-sm text-[var(--primary-foreground)] hover:opacity-90 disabled:opacity-50"
          onClick={handleProcess}
          disabled={!inputPath || !outputPath || steps.length === 0}
        >
          执行
        </button>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-medium">任务列表</h3>
        <TaskTable tasks={tasks} />
      </div>
    </div>
  )
}
