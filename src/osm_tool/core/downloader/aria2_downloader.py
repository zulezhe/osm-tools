"""aria2c 多线程下载器

优先使用 aria2c 进行多连接分段下载，不支持时降级到 Python 多线程下载。
- aria2c: 16 连接分段下载，支持断点续传
- Python fallback: 多线程 Range 分段下载
"""
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

from osm_tool.core.downloader.base import BaseDownloader
from osm_tool.models.download_task import DownloadTask
from osm_tool.models.task_state import TaskState
from osm_tool.utils.logger import setup_logger

logger = setup_logger("osm_tool.aria2")


def is_aria2_available() -> bool:
    """检测 aria2c 是否可用"""
    return shutil.which("aria2c") is not None


class Aria2Downloader(BaseDownloader):
    """使用 aria2c 的多连接下载器

    Features:
    - 多连接分段下载 (--split=16, --max-connection-per-server=8)
    - 断点续传 (--continue=true)
    - HTTP pipelining
    - 进度解析
    """

    def __init__(self, task: DownloadTask, split: int = 16, max_conn: int = 8, **kwargs):
        super().__init__(task, **kwargs)
        self._split = split
        self._max_conn = max_conn
        self._process: subprocess.Popen | None = None
        self._monitor_thread: threading.Thread | None = None

    MAX_RETRIES = 3
    RETRY_DELAYS = [5, 10, 20]

    def download(self) -> None:
        self._set_state(TaskState.DOWNLOADING)
        save_path = Path(self._task.save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        last_error = None
        for attempt in range(self.MAX_RETRIES + 1):
            if self._is_cancelled:
                return
            try:
                if is_aria2_available():
                    if attempt == 0:
                        logger.info(f"使用 aria2c 下载: {self._task.url}")
                    self._download_with_aria2(save_path)
                else:
                    if attempt == 0:
                        logger.info("aria2c 不可用，使用 Python 多线程下载")
                    self._download_with_threaded(save_path)
                return  # 成功则退出
            except Exception as e:
                last_error = e
                if self._is_cancelled:
                    return
                if attempt < self.MAX_RETRIES:
                    delay = self.RETRY_DELAYS[attempt]
                    logger.warning(f"下载失败 (第{attempt + 1}次)，{delay}秒后重试: {e}")
                    for _ in range(delay * 10):
                        if self._is_cancelled:
                            return
                        time.sleep(0.1)
                else:
                    self._report_error(f"下载失败（已重试{self.MAX_RETRIES}次）: {last_error}")

    def cancel(self) -> None:
        self._is_cancelled = True
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._set_state(TaskState.CANCELLED)

    # ── aria2c 下载 ──

    def _download_with_aria2(self, save_path: Path) -> None:
        cmd = [
            "aria2c",
            "--split", str(self._split),
            "--max-connection-per-server", str(self._max_conn),
            "--min-split-size", "10M",
            "--continue=true",
            "--allow-overwrite=true",
            "--auto-file-renaming=false",
            "--enable-http-pipelining=true",
            "--file-allocation=prealloc",
            "--max-tries=5",
            "--retry-wait=5",
            "--timeout=60",
            "--connect-timeout=30",
            "--user-agent=OSM-Tool/0.1",
            "--summary-interval=1",
            f"--dir={save_path.parent}",
            f"--out={save_path.name}",
            self._task.url,
        ]

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )

            self._monitor_aria2_output()

            ret = self._process.wait()
            self._process = None

            if self._is_cancelled:
                return

            if ret == 0 and save_path.exists():
                self._task.downloaded_bytes = save_path.stat().st_size
                self._task.total_bytes = self._task.downloaded_bytes
                self._task.to_meta_file()
                self._set_state(TaskState.COMPLETED)
            else:
                self._report_error(f"aria2c 退出码: {ret}")

        except Exception as e:
            self._report_error(str(e))

    def _monitor_aria2_output(self) -> None:
        """解析 aria2c 输出获取进度"""
        progress_re = re.compile(r'\((\d+)%\)')
        size_re = re.compile(r'([\d.]+[KMGT]?B)\s*/\s*([\d.]+[KMGT]?B)')
        speed_re = re.compile(r'([\d.]+[KMGT]?B/s)')
        done_re = re.compile(r'\(100%\)')
        downloading_re = re.compile(r'\((\d+)%\)')
        waiting_re = re.compile(r'FILE:')

        def _parse_size(s: str) -> int:
            s = s.strip()
            units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
            for suffix, mult in sorted(units.items(), key=lambda x: -len(x[0])):
                if s.upper().endswith(suffix):
                    return int(float(s[:-len(suffix)]) * mult)
            return int(float(s))

        if not self._process or not self._process.stdout:
            return

        for line in self._process.stdout:
            if self._is_cancelled:
                break
            line = line.strip()
            if not line:
                continue

            # 解析进度百分比
            m = downloading_re.search(line)
            if m:
                pct = int(m.group(1))
                # 尝试解析大小
                sm = size_re.search(line)
                if sm:
                    try:
                        dl_size = _parse_size(sm.group(1))
                        total_size = _parse_size(sm.group(2))
                        self._task.downloaded_bytes = dl_size
                        self._task.total_bytes = total_size
                        speed_m = speed_re.search(line)
                        speed = _parse_size(speed_m.group(1).replace('/s', '')) if speed_m else 0
                        self._report_progress(dl_size, total_size, speed)
                    except (ValueError, IndexError):
                        self._report_progress(pct, 100, 0)
                else:
                    self._report_progress(pct, 100, 0)

    # ── Python 多线程降级下载 ──

    def _download_with_threaded(self, save_path: Path) -> None:
        """多线程 Range 分段下载（aria2c 不可用时降级）"""
        import requests
        from concurrent.futures import ThreadPoolExecutor, as_completed

        try:
            # 获取文件大小
            head = requests.head(self._task.url, headers={"User-Agent": "OSM-Tool/0.1", "Accept-Encoding": "gzip, deflate"}, timeout=30, allow_redirects=True)
            head.raise_for_status()
            total = int(head.headers.get("content-length", 0))
            accept_ranges = head.headers.get("accept-ranges", "")

            if total <= 0 or "bytes" not in accept_ranges.lower():
                # 服务器不支持 Range，回退到单线程
                logger.info("服务器不支持 Range，使用单线程下载")
                self._download_single(save_path)
                return

            self._task.total_bytes = total

            # 计算分段
            num_threads = min(8, max(1, total // (5 * 1024 * 1024)))  # 每 5MB 一段，最多 8 线程
            chunk_size = total // num_threads
            parts = []
            for i in range(num_threads):
                start = i * chunk_size
                end = total - 1 if i == num_threads - 1 else (i + 1) * chunk_size - 1
                parts.append((i, start, end))

            logger.info(f"多线程下载: {num_threads} 线程, 总大小 {total / 1024 / 1024:.1f} MB")

            # 下载各段到临时文件
            temp_files = [None] * num_threads
            downloaded_per_thread = [0] * num_threads
            errors = []
            lock = threading.Lock()

            def download_part(idx: int, start: int, end: int) -> None:
                tmp_path = save_path.parent / f"{save_path.name}.part{idx}"
                temp_files[idx] = tmp_path
                headers = {
                    "Range": f"bytes={start}-{end}",
                    "User-Agent": "OSM-Tool/0.1", "Accept-Encoding": "gzip, deflate",
                }
                try:
                    resp = requests.get(self._task.url, headers=headers, stream=True, timeout=300)
                    resp.raise_for_status()
                    part_dl = 0
                    with open(tmp_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=256 * 1024):
                            if self._is_cancelled:
                                return
                            f.write(chunk)
                            part_dl += len(chunk)
                            with lock:
                                downloaded_per_thread[idx] = part_dl
                    downloaded_per_thread[idx] = part_dl
                except Exception as e:
                    errors.append(f"线程 {idx} 失败: {e}")

            start_time = time.time()

            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = {executor.submit(download_part, i, s, e): i for i, s, e in parts}

                # 进度监控
                while not all(f.done() for f in futures):
                    if self._is_cancelled:
                        for f in futures:
                            f.cancel()
                        return
                    with lock:
                        total_dl = sum(downloaded_per_thread)
                    elapsed = time.time() - start_time
                    speed = total_dl / elapsed if elapsed > 0 else 0
                    self._report_progress(total_dl, total, speed)
                    time.sleep(0.3)

                # 等待所有完成
                for f in as_completed(futures):
                    if f.exception():
                        errors.append(str(f.exception()))

            if self._is_cancelled:
                return

            if errors:
                self._report_error("; ".join(errors))
                return

            # 合并分段文件
            total_dl = 0
            with open(save_path, "wb") as out:
                for i in range(num_threads):
                    tmp_path = temp_files[i]
                    if tmp_path and tmp_path.exists():
                        data = tmp_path.read_bytes()
                        out.write(data)
                        total_dl += len(data)
                        tmp_path.unlink()

            self._task.downloaded_bytes = total_dl
            self._task.to_meta_file()
            self._set_state(TaskState.COMPLETED)

        except Exception as e:
            self._report_error(str(e))

    def _download_single(self, save_path: Path) -> None:
        """单线程下载（服务器不支持 Range 时的最终降级）"""
        import requests

        try:
            resp = requests.get(
                self._task.url,
                headers={"User-Agent": "OSM-Tool/0.1", "Accept-Encoding": "gzip, deflate"},
                stream=True,
                timeout=900,
            )
            resp.raise_for_status()

            total = int(resp.headers.get("content-length", 0))
            self._task.total_bytes = total
            downloaded = 0
            start_time = time.time()

            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=256 * 1024):
                    if self._is_cancelled:
                        return
                    f.write(chunk)
                    downloaded += len(chunk)
                    elapsed = time.time() - start_time
                    speed = downloaded / elapsed if elapsed > 0 else 0
                    self._report_progress(downloaded, total, speed)

            self._task.downloaded_bytes = downloaded
            self._task.to_meta_file()
            self._set_state(TaskState.COMPLETED)

        except Exception as e:
            self._report_error(str(e))
