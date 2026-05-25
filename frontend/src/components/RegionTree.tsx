import { useState, useMemo } from 'react'

interface Region {
  id: string
  name: string
  parent_id: string | null
  url: string
  size_bytes: number
}

interface RegionTreeProps {
  regions: Region[]
  selectedId: string | null
  onSelect: (region: Region) => void
}

export function RegionTree({ regions, selectedId, onSelect }: RegionTreeProps) {
  const [search, setSearch] = useState('')

  // 构建父级路径映射
  const parentMap = useMemo(() => {
    const m = new Map<string, Region>()
    for (const r of regions) m.set(r.id, r)
    return m
  }, [regions])

  // 获取区域完整路径，如 "亚洲 / 中国 / 北京"
  const getPath = (region: Region): string => {
    const parts: string[] = [region.name]
    let current = parentMap.get(region.parent_id ?? '')
    while (current) {
      parts.unshift(current.name)
      current = parentMap.get(current.parent_id ?? '')
    }
    return parts.join(' / ')
  }

  // 搜索过滤
  const searchResults = useMemo(() => {
    if (!search.trim()) return []
    const q = search.trim().toLowerCase()
    return regions
      .filter(r => r.name.toLowerCase().includes(q))
      .slice(0, 50)
  }, [regions, search])

  const isSearching = search.trim().length > 0

  const roots = regions.filter(r => r.parent_id === null)

  return (
    <div className="flex flex-col max-h-80">
      {/* 搜索框 */}
      <div className="px-2 py-1.5 border-b border-gray-100">
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="搜索区域..."
          className="w-full rounded border border-gray-200 px-2 py-1 text-xs outline-none focus:border-blue-400"
        />
      </div>

      {/* 搜索结果 / 树形结构 */}
      <div className="overflow-auto flex-1">
        {isSearching ? (
          searchResults.length === 0 ? (
            <p className="py-4 text-center text-sm text-[var(--muted-foreground)]">
              未找到 "{search.trim()}"
            </p>
          ) : (
            searchResults.map(region => (
              <div
                key={region.id}
                className={`flex cursor-pointer items-center gap-1 rounded px-2 py-1 text-sm hover:bg-[var(--muted)] ${selectedId === region.id ? 'bg-[var(--muted)]' : ''}`}
                onClick={() => region.url && onSelect(region)}
              >
                <span className="flex-1 min-w-0">
                  <span className="font-medium">{highlightMatch(region.name, search.trim())}</span>
                  {getPath(region).split(' / ').length > 1 && (
                    <span className="block text-[10px] text-[var(--muted-foreground)] truncate">
                      {getPath(region).split(' / ').slice(0, -1).join(' / ')}
                    </span>
                  )}
                </span>
                {region.size_bytes > 0 && (
                  <span className="text-xs text-[var(--muted-foreground)] whitespace-nowrap">
                    {(region.size_bytes / 1024 / 1024).toFixed(0)} MB
                  </span>
                )}
              </div>
            ))
          )
        ) : (
          <>
            {roots.map(region => (
              <TreeNode
                key={region.id}
                region={region}
                allRegions={regions}
                selectedId={selectedId}
                onSelect={onSelect}
                depth={0}
              />
            ))}
            {regions.length === 0 && (
              <p className="py-4 text-center text-sm text-[var(--muted-foreground)]">
                点击更新加载区域列表
              </p>
            )}
          </>
        )}
      </div>
    </div>
  )
}

/** 高亮匹配文字 */
function highlightMatch(text: string, query: string) {
  const idx = text.toLowerCase().indexOf(query.toLowerCase())
  if (idx < 0) return text
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-yellow-200 text-inherit rounded-sm px-0.5">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  )
}

function TreeNode({ region, allRegions, selectedId, onSelect, depth }: {
  region: Region
  allRegions: Region[]
  selectedId: string | null
  onSelect: (region: Region) => void
  depth: number
}) {
  const [open, setOpen] = useState(false)
  const children = allRegions.filter(r => r.parent_id === region.id)
  const hasChildren = children.length > 0
  const isSelected = selectedId === region.id
  const sizeStr = region.size_bytes ? `${(region.size_bytes / 1024 / 1024).toFixed(0)} MB` : ''

  return (
    <div>
      <div
        className={`flex cursor-pointer items-center gap-1 rounded px-2 py-1 text-sm hover:bg-[var(--muted)] ${isSelected ? 'bg-[var(--muted)]' : ''}`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={() => {
          if (hasChildren) setOpen(!open)
          if (region.url) onSelect(region)
        }}
      >
        {hasChildren ? (
          <span className="w-4 text-center text-xs text-[var(--muted-foreground)]">
            {open ? '▼' : '▶'}
          </span>
        ) : (
          <span className="w-4" />
        )}
        <span className="flex-1">{region.name}</span>
        {sizeStr && (
          <span className="text-xs text-[var(--muted-foreground)]">{sizeStr}</span>
        )}
      </div>
      {hasChildren && open && children.map(child => (
        <TreeNode
          key={child.id}
          region={child}
          allRegions={allRegions}
          selectedId={selectedId}
          onSelect={onSelect}
          depth={depth + 1}
        />
      ))}
    </div>
  )
}
