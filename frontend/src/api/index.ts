import { api, post } from './client'

// ── 下载 ──
export const downloadApi = {
  getGeofabrikRegions: () => api<any[]>('/download/geofabrik/regions'),
  refreshGeofabrikRegions: () => post<{ count: number }>('/download/geofabrik/refresh', {}),
  startGeofabrik: (params: { url: string; save_path: string; region_name?: string }) =>
    post<{ task_id: string }>('/download/geofabrik/start', params),
  startOverpass: (params: { query: string; save_path: string; output_format?: string }) =>
    post<{ task_id: string }>('/download/overpass/start', params),
  getDefaultSavePath: () => api<{ path: string }>('/download/config/default-save-path'),
  importVector: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch('/api/v1/download/import-vector', { method: 'POST', body: formData })
    const json = await res.json()
    if (json.code !== 0) throw new Error(json.message || '解析失败')
    return json.data as { bbox: any; geojson: any; area_sqkm: number }
  },
  generateOverpassQuery: (params: Record<string, unknown>) =>
    post<{ query: string }>('/download/overpass/query', params),
  getTasks: () => api<any[]>('/download/tasks'),
  cancelTask: (id: string) => post(`/download/tasks/${id}/cancel`, {}),
  retryTask: (id: string) => post(`/download/tasks/${id}/retry`, {}),
  deleteTask: (id: string) => fetch(`/api/v1/download/tasks/${id}`, { method: 'DELETE' }).then(r => r.json()),
}

// ── 转换 ──
export const convertApi = {
  getFormats: () => api<string[]>('/convert/formats'),
  start: (params: { input_path: string; output_path: string; output_format?: string; options?: any }) =>
    post<{ task_id: string }>('/convert/start', params),
  getTasks: () => api<any[]>('/convert/tasks'),
}

// ── 分割 ──
export const splitApi = {
  start: (params: { input_path: string; output_dir: string; split_type: string; options?: any }) =>
    post<{ task_id: string }>('/split/start', params),
  getTasks: () => api<any[]>('/split/tasks'),
}

// ── 处理 ──
export const processApi = {
  start: (params: { input_path: string; output_path: string; steps: Array<{ type: string; params?: any }> }) =>
    post<{ task_id: string }>('/process/start', params),
  getTasks: () => api<any[]>('/process/tasks'),
}

// ── 发布 ──
export const publishApi = {
  start: (params: { input_path: string; output_path: string; config?: any }) =>
    post<{ task_id: string }>('/publish/start', params),
  getTasks: () => api<any[]>('/publish/tasks'),
}

// ── 提取 ──
export const extractApi = {
  scanFields: (filePath: string) => post<FieldInfo[]>('/extract/scan', { file_path: filePath }),
  start: (params: { file_path: string; output_path: string; filters: FilterItem[] }) =>
    post<{ task_id: string }>('/extract/start', params),
  tagDictionary: (query?: string) => post<TagDictItem[]>('/extract/tag-dictionary', { query: query || '' }),
  getTasks: () => api<any[]>('/extract/tasks'),
}

export interface FieldInfo {
  key: string
  count: number
  label: string
  desc: string
  sample_values: { value: string; count: number }[]
  element_types: string[]
}

export interface FilterItem {
  key: string
  values: string[]
}

export interface TagDictItem {
  key: string
  label: string
  desc: string
  values: string[]
}

// ── 系统 ──
export const systemApi = {
  health: () => api('/health'),
  getEnvironment: () => api<Record<string, { available: boolean; path: string | null }>>('/environment'),
  fileDialog: (params: { mode?: string; title?: string; file_types?: Array<{ label: string; ext: string }> }) =>
    post<{ path: string }>('/file-dialog', params),
}
