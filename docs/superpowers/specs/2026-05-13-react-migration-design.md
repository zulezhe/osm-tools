# OSM Tool: PySide6 → React + FastAPI 迁移设计

**日期**: 2026-05-13
**状态**: 已批准

## 1. 目标

将 OSM Tool 的 GUI 从 PySide6 桌面应用迁移为 Web 架构：
- 前端：React + Vite + TypeScript + shadcn/ui + TailwindCSS
- 后端：FastAPI + uvicorn
- 通信：REST API + SSE（Server-Sent Events）
- 打包：前端构建产物嵌入 Python 包，PyInstaller 单 exe 分发

原因：PySide6 包体积过大（~200MB），实际使用不便。

## 2. 整体架构

```
用户启动 osm-tool
  → Python FastAPI 启动 (localhost:随机端口)
  → 自动打开浏览器
  → React SPA 加载
  → 前端通过 REST API + SSE 与后端通信
```

### 项目结构

```
osm-download/
├── src/osm_tool/
│   ├── main.py              # 改造：启动 FastAPI + 打开浏览器
│   ├── app.py               # 改造：FastAPI 应用
│   ├── api/                 # 新增：API 路由层
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── download.py
│   │   │   ├── split.py
│   │   │   ├── process.py
│   │   │   ├── convert.py
│   │   │   └── publish.py
│   │   ├── deps.py          # 依赖注入
│   │   └── events.py        # SSE 事件推送
│   ├── core/                # 保留不变
│   ├── models/              # 保留不变
│   ├── workers/             # 改造：QThread → threading.Thread
│   ├── utils/               # 保留不变
│   └── web/                 # 新增：React 构建产物（gitignore）
├── frontend/                # 新增：React 开发目录
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── api/
│   │   └── lib/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
├── pyproject.toml           # 更新依赖
└── Makefile                 # 更新构建流程
```

### 删除的文件

- `src/osm_tool/ui/` 整个目录（PySide6 UI）

## 3. API 设计

统一前缀 `/api/v1`。

### 通用响应格式

```json
{ "code": 0, "data": {...} }    // 成功
{ "code": 1, "message": "..." } // 失败
```

### SSE 事件格式

```
event: task_progress
data: {"task_id": "xxx", "task_type": "download", "progress": 45.2, "status": "downloading"}
```

统一 SSE 端点 `/api/v1/events`，前端按 `task_type` 字段过滤分发。

### 下载 `/api/v1/download`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /geofabrik/regions | 获取 Geofabrik 区域树 |
| POST | /geofabrik/start | 开始 Geofabrik 下载 |
| POST | /overpass/start | 开始 Overpass 查询下载 |
| POST | /bbox/start | 开始 BBox 范围下载 |
| GET | /tasks | 获取下载任务列表 |
| POST | /tasks/{id}/cancel | 取消下载 |
| POST | /tasks/{id}/pause | 暂停下载 |
| POST | /tasks/{id}/resume | 恢复下载 |

### 转换 `/api/v1/convert`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /formats | 获取支持的格式列表 |
| POST | /start | 开始转换 |
| GET | /tasks | 转换任务列表 |

### 分割 `/api/v1/split`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /start | 开始分割 |
| GET | /tasks | 分割任务列表 |

### 处理 `/api/v1/process`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /start | 开始处理 |
| GET | /tasks | 处理任务列表 |

### 发布 `/api/v1/publish`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /start | 开始发布 |
| GET | /tasks | 发布任务列表 |

### 系统 `/api/v1`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 健康检查 |
| GET | /environment | 检测外部工具 |
| GET | /events | SSE 端点 |
| POST | /file-dialog | 弹出原生文件选择对话框 |

## 4. Python 后端改造

### 4.1 入口改造

**app.py** — FastAPI 应用：
- 挂载所有 API 路由
- 生产模式：`StaticFiles` 托管 `web/` 目录
- 开发模式：仅提供 API

**main.py** — 启动逻辑：
- `find_free_port()` 找可用端口
- `webbrowser.open()` 打开浏览器
- `uvicorn.run()` 启动服务

### 4.2 Workers 改造

QThread → `threading.Thread`，Qt Signal → 回调函数：

```python
class DownloadWorker:
    def __init__(self, downloader, on_progress, on_complete, on_error):
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._on_error = on_error

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            result = self._do_work()
            self._on_complete(result)
        except Exception as e:
            self._on_error(str(e))
```

5 个 Worker（download, convert, split, process, publish）统一采用此模式。

### 4.3 任务管理器

```python
class TaskManager:
    """管理所有后台任务，通过 SSE 推送进度"""

    def __init__(self):
        self._tasks: dict[str, TaskInfo] = {}
        self._subscribers: list[Queue] = []

    def create_task(self, task_type, **params) -> str  # 返回 task_id
    def cancel_task(self, task_id: str) -> bool
    def subscribe(self) -> Queue        # SSE 订阅
    def _emit(self, event: dict)        # 推送事件
```

TaskManager 为单例，通过 FastAPI 依赖注入提供给各路由。

## 5. 前端设计

技术栈：React + Vite + TypeScript + shadcn/ui + TailwindCSS

### 5.1 页面布局

左侧导航栏 + 右侧内容区 + 底部可折叠日志面板：

```
┌──────────────────────────────────────┐
│  OSM Tool                    日志 ▼  │
├──────┬───────────────────────────────┤
│ 下载 │                               │
│ 分割 │                               │
│ 处理 │      当前页面内容              │
│ 转换 │                               │
│ 发布 │                               │
│      │                               │
├──────┴───────────────────────────────┤
│  日志面板（可折叠）                    │
└──────────────────────────────────────┘
```

### 5.2 组件结构

```
frontend/src/
├── App.tsx
├── pages/
│   ├── DownloadPage.tsx
│   ├── SplitPage.tsx
│   ├── ProcessPage.tsx
│   ├── ConvertPage.tsx
│   └── PublishPage.tsx
├── components/
│   ├── Layout.tsx
│   ├── TaskTable.tsx       # 通用任务列表（带进度条）
│   ├── FileSelector.tsx    # 文件/目录选择器
│   └── LogPanel.tsx        # 日志面板
├── hooks/
│   ├── useSSE.ts           # SSE 连接
│   └── useTasks.ts         # 任务状态管理
├── api/
│   ├── client.ts           # fetch 封装
│   ├── download.ts
│   ├── convert.ts
│   ├── split.ts
│   ├── process.ts
│   └── publish.ts
└── lib/
    └── utils.ts
```

### 5.3 状态管理

React useState + Context，不引入 Redux。每个页面管理自己的任务列表，通过 SSE 事件实时更新。

### 5.4 文件选择

前端无法直接访问文件系统，两种方式：
- `POST /api/v1/file-dialog`：后端调用 `tkinter.filedialog` 弹出原生对话框，返回路径
- 用户手动在输入框输入路径

## 6. 构建与打包

### 6.1 开发模式

```bash
# 终端 1：FastAPI（热重载）
uv run python -m osm_tool.main --dev

# 终端 2：前端 dev server
cd frontend && npm run dev
```

Vite proxy 配置将 `/api` 转发到 FastAPI。

### 6.2 依赖变更

**移除**：`PySide6`

**新增 Python**：`fastapi`, `uvicorn`, `sse-starlette`

**前端**：React, TypeScript, Vite, shadcn/ui, TailwindCSS, `@tanstack/react-query`

### 6.3 构建流程

```makefile
build-frontend:
	cd frontend && npm install && npm run build

build: build-frontend
	pyinstaller osm-tool.spec
```

前端构建产物输出到 `src/osm_tool/web/`，PyInstaller 打包时作为 datas 收集。

### 6.4 分发

PyInstaller 打包为单个 exe，用户双击 → 启动 FastAPI → 自动打开浏览器。
