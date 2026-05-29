import { useState } from 'react'
import { extractApi, type FieldInfo, type FilterItem } from '../api'
import { useTasks } from '../hooks/useTasks'
import { FileSelector } from '../components/FileSelector'
import { TaskTable } from '../components/TaskTable'

export function ExtractPage() {
  const { tasks } = useTasks('extract')
  const [inputPath, setInputPath] = useState('')
  const [outputPath, setOutputPath] = useState('')
  const [fields, setFields] = useState<FieldInfo[]>([])
  const [selectedFields, setSelectedFields] = useState<Map<string, FilterItem>>(new Map())
  const [scanning, setScanning] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [error, setError] = useState('')

  // 扫描文件字段
  const handleScan = async () => {
    if (!inputPath) return alert('请选择输入文件')
    setScanning(true)
    setError('')
    setFields([])
    setSelectedFields(new Map())
    try {
      const result = await extractApi.scanFields(inputPath)
      setFields(result)
    } catch (e: any) {
      setError(e.message || '扫描失败')
    } finally {
      setScanning(false)
    }
  }

  // 切换字段选择
  const toggleField = (key: string) => {
    const next = new Map(selectedFields)
    if (next.has(key)) {
      next.delete(key)
    } else {
      next.set(key, { key, values: [] })
    }
    setSelectedFields(next)
  }

  // 切换字段值选择
  const toggleValue = (key: string, value: string) => {
    const next = new Map(selectedFields)
    const existing = next.get(key)
    if (!existing) return
    const vals = existing.values.includes(value)
      ? existing.values.filter(v => v !== value)
      : [...existing.values, value]
    next.set(key, { key, values: vals })
    setSelectedFields(next)
  }

  // 全选/取消字段值
  const selectAllValues = (key: string, field: FieldInfo) => {
    const next = new Map(selectedFields)
    const existing = next.get(key)
    if (!existing) return
    const allValues = field.sample_values.map(sv => sv.value)
    const allSelected = allValues.every(v => existing.values.includes(v))
    next.set(key, { key, values: allSelected ? [] : allValues })
    setSelectedFields(next)
  }

  // 执行提取
  const handleExtract = async () => {
    if (!inputPath || !outputPath) return alert('请填写输入和输出文件路径')
    if (selectedFields.size === 0) return alert('请至少选择一个字段')
    try {
      await extractApi.start({
        file_path: inputPath,
        output_path: outputPath,
        filters: Array.from(selectedFields.values()),
      })
    } catch (e: any) {
      alert(e.message)
    }
  }

  // 过滤字段
  const filteredFields = fields.filter(f => {
    if (!searchQuery) return true
    const q = searchQuery.toLowerCase()
    return f.key.toLowerCase().includes(q)
      || f.label.toLowerCase().includes(q)
      || f.desc.toLowerCase().includes(q)
  })

  return (
    <div className="flex flex-col gap-4">
      {/* 输入文件 */}
      <div className="rounded border border-[var(--border)] bg-white p-4">
        <h3 className="mb-3 text-sm font-semibold">1. 选择数据文件</h3>
        <div className="flex gap-2">
          <FileSelector
            value={inputPath}
            onChange={setInputPath}
            mode="open_file"
            fileTypes={[
              { label: 'GeoJSON', ext: '*.geojson *.json' },
              { label: 'OSM XML', ext: '*.osm' },
            ]}
          />
          <button
            className="shrink-0 rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            onClick={handleScan}
            disabled={!inputPath || scanning}
          >
            {scanning ? '扫描中...' : '扫描字段'}
          </button>
        </div>
        {error && <p className="mt-2 text-xs text-red-500">{error}</p>}
      </div>

      {/* 字段列表 */}
      {fields.length > 0 && (
        <div className="rounded border border-[var(--border)] bg-white p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold">
              2. 选择提取字段
              <span className="ml-2 text-xs font-normal text-gray-500">
                共 {fields.length} 个字段，已选 {selectedFields.size} 个
              </span>
            </h3>
            <input
              type="text"
              placeholder="搜索字段..."
              className="w-48 rounded border border-gray-200 px-2 py-1 text-xs"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="max-h-[50vh] overflow-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-gray-50">
                <tr className="border-b">
                  <th className="w-8 px-2 py-1.5 text-left">
                    <input
                      type="checkbox"
                      checked={selectedFields.size === filteredFields.length && filteredFields.length > 0}
                      onChange={() => {
                        if (selectedFields.size === filteredFields.length) {
                          setSelectedFields(new Map())
                        } else {
                          const next = new Map<string, FilterItem>()
                          filteredFields.forEach(f => next.set(f.key, { key: f.key, values: [] }))
                          setSelectedFields(next)
                        }
                      }}
                    />
                  </th>
                  <th className="px-2 py-1.5 text-left font-medium">字段名</th>
                  <th className="px-2 py-1.5 text-left font-medium">中文说明</th>
                  <th className="px-2 py-1.5 text-right font-medium">数量</th>
                  <th className="px-2 py-1.5 text-left font-medium">类型</th>
                  <th className="px-2 py-1.5 text-left font-medium">常见值</th>
                </tr>
              </thead>
              <tbody>
                {filteredFields.map(field => {
                  const isSelected = selectedFields.has(field.key)
                  const filter = selectedFields.get(field.key)
                  return (
                    <tr key={field.key} className={`border-b hover:bg-gray-50 ${isSelected ? 'bg-blue-50' : ''}`}>
                      <td className="px-2 py-1.5">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleField(field.key)}
                        />
                      </td>
                      <td className="px-2 py-1.5">
                        <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs font-mono">{field.key}</code>
                      </td>
                      <td className="px-2 py-1.5">
                        <div className="font-medium">{field.label}</div>
                        <div className="mt-0.5 text-gray-400">{field.desc}</div>
                      </td>
                      <td className="px-2 py-1.5 text-right tabular-nums">{field.count.toLocaleString()}</td>
                      <td className="px-2 py-1.5 text-gray-500">{field.element_types.join(', ')}</td>
                      <td className="max-w-xs px-2 py-1.5">
                        {isSelected && field.sample_values.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            <button
                              className="text-[10px] text-blue-500 hover:underline"
                              onClick={() => selectAllValues(field.key, field)}
                            >
                              {filter?.values.length === field.sample_values.length ? '取消全选' : '全选'}
                            </button>
                            {field.sample_values.slice(0, 12).map(sv => (
                              <button
                                key={sv.value}
                                className={`rounded border px-1.5 py-0.5 text-[10px] transition-colors ${
                                  filter?.values.includes(sv.value)
                                    ? 'border-blue-400 bg-blue-100 text-blue-700'
                                    : 'border-gray-200 text-gray-600 hover:border-blue-300'
                                }`}
                                onClick={() => toggleValue(field.key, sv.value)}
                                title={`${sv.value} (${sv.count})`}
                              >
                                {sv.value.length > 15 ? sv.value.slice(0, 15) + '...' : sv.value}
                                <span className="ml-0.5 text-gray-400">({sv.count})</span>
                              </button>
                            ))}
                            {field.sample_values.length > 12 && (
                              <span className="text-[10px] text-gray-400">+{field.sample_values.length - 12} 更多</span>
                            )}
                          </div>
                        ) : (
                          <div className="flex flex-wrap gap-0.5">
                            {field.sample_values.slice(0, 5).map(sv => (
                              <span key={sv.value} className="rounded bg-gray-100 px-1 py-0.5 text-[10px] text-gray-500" title={sv.value}>
                                {sv.value.length > 12 ? sv.value.slice(0, 12) + '...' : sv.value}
                              </span>
                            ))}
                            {field.sample_values.length > 5 && (
                              <span className="text-[10px] text-gray-400">+{field.sample_values.length - 5}</span>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 输出和执行 */}
      <div className="rounded border border-[var(--border)] bg-white p-4">
        <h3 className="mb-3 text-sm font-semibold">
          3. 输出设置
          {selectedFields.size > 0 && (
            <span className="ml-2 text-xs font-normal text-blue-600">
              提取条件: {Array.from(selectedFields.values()).map(f =>
                f.values.length > 0 ? `${f.key}=${f.values.join('|')}` : f.key
              ).join(', ')}
            </span>
          )}
        </h3>
        <div className="flex gap-2">
          <FileSelector
            value={outputPath}
            onChange={setOutputPath}
            mode="save_file"
            fileTypes={[{ label: 'GeoJSON', ext: '*.geojson' }]}
          />
          <button
            className="shrink-0 rounded bg-green-600 px-4 py-1.5 text-sm text-white hover:bg-green-700 disabled:opacity-50"
            onClick={handleExtract}
            disabled={!inputPath || !outputPath || selectedFields.size === 0}
          >
            开始提取
          </button>
        </div>
      </div>

      {/* 任务列表 */}
      {tasks.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-medium">提取任务</h3>
          <TaskTable tasks={tasks} />
        </div>
      )}
    </div>
  )
}
