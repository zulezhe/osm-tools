"""处理管道基类"""
import json
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable


class ProcessingStep(ABC):
    """处理步骤抽象基类"""
    name: str = "base"

    @abstractmethod
    def process_feature(self, feature: dict) -> dict:
        ...

    def execute(self, input_path: str, output_path: str) -> None:
        data = json.loads(Path(input_path).read_text(encoding="utf-8"))
        features = data.get("features", [])

        processed = []
        for feat in features:
            processed.append(self.process_feature(feat))

        data["features"] = processed
        Path(output_path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class ProcessingPipeline:
    """处理管道"""

    def __init__(self):
        self._steps: list[ProcessingStep] = []
        self._on_step_progress: Callable[[str, int], None] | None = None

    def add_step(self, step: ProcessingStep) -> None:
        self._steps.append(step)

    def remove_step(self, index: int) -> None:
        if 0 <= index < len(self._steps):
            self._steps.pop(index)

    def clear(self) -> None:
        self._steps.clear()

    @property
    def steps(self) -> list[ProcessingStep]:
        return self._steps

    def execute(self, input_path: str, output_path: str) -> None:
        current_input = input_path
        for i, step in enumerate(self._steps):
            if i == len(self._steps) - 1:
                step.execute(current_input, output_path)
            else:
                tmp = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False, mode="w")
                tmp_path = tmp.name
                tmp.close()
                step.execute(current_input, tmp_path)
                if current_input != input_path:
                    Path(current_input).unlink(missing_ok=True)
                current_input = tmp_path

            if self._on_step_progress:
                self._on_step_progress(step.name, int((i + 1) / len(self._steps) * 100))

        if current_input != input_path and current_input != output_path:
            Path(current_input).unlink(missing_ok=True)
