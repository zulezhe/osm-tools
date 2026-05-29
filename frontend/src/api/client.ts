const BASE = '/api/v1'

export async function api<T = unknown>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  const json = await res.json()
  if (json.code !== 0) {
    throw new Error(json.message || '请求失败')
  }
  return json.data as T
}

export async function post<T = unknown>(path: string, body: Record<string, unknown>): Promise<T> {
  return api<T>(path, { method: 'POST', body: JSON.stringify(body) })
}
