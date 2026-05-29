.PHONY: install start run dev dev-frontend test clean build-frontend build pack release

# ── 配置 ──────────────────────────────────────
APP_NAME      := osm-tool
APP_VERSION   := 0.1.0
PYTHON        := python
UV            := uv
DIST_DIR      := dist
BUILD_DIR     := build
FRONTEND_DIR  := frontend

# ── 一键启动（不重装依赖）────────────────────
start:
	$(UV) run $(PYTHON) src/osm_tool/main.py

# ── 一键安装 + 启动 ──────────────────────────
run: install start

# ── 安装全部依赖 ──────────────────────────────
install:
	$(UV) sync
	cd $(FRONTEND_DIR) && npm install

# ── 开发模式：后端（热重载，固定 8000 端口）──
dev:
	OSM_DEV=1 $(UV) run $(PYTHON) src/osm_tool/main.py

# ── 开发模式：前端 dev server ────────────────
dev-frontend:
	cd $(FRONTEND_DIR) && npm run dev

# ── 运行测试 ──────────────────────────────────
test:
	$(UV) run pytest tests/ -v

# ── 构建前端 ──────────────────────────────────
build-frontend:
	cd $(FRONTEND_DIR) && npm install && npm run build

# ── 清理构建产物 ──────────────────────────────
clean:
	-rm -rf $(DIST_DIR) $(BUILD_DIR)
	-rm -rf .pytest_cache
	-rm -rf src/osm_tool/web
	-find . -type d -name __pycache__ | xargs rm -rf 2>/dev/null; true
	-find . -type f -name "*.pyc" -delete 2>/dev/null; true

# ── PyInstaller 打包 ─────────────────────────
build: build-frontend
	$(UV) run pyinstaller osm-tool.spec --noconfirm

# ── 打包并显示结果 ────────────────────────────
pack: build
	@ls -lh $(DIST_DIR)/$(APP_NAME).exe
	@echo "打包完成: $(DIST_DIR)/$(APP_NAME).exe"

# ── 全流程: 测试 → 清理 → 打包 ───────────────
release: test clean build
	@echo "发布完成: $(DIST_DIR)/$(APP_NAME).exe"
