"""任务基类：基于状态机的任务执行框架。

借鉴参考项目:
  - lua-touchsprite: dealUnusual() 异常处理前置、dispatch table、retry 限制
  - mhxy-escort: 多策略验证、分级回退
  - mhxy_fz: 简单轮询 is_start 停止标志
"""

import time
import random
from enum import Enum
from abc import ABC, abstractmethod
from pathlib import Path


class TaskState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class Step:
    """单个任务步骤。

    action 返回 True 表示步骤成功。
    verify 可选，用于二次验证步骤是否真正完成。
    """

    def __init__(self, name: str, action, timeout: float = 30.0, retries: int = 3,
                 verify=None, backoff: float = 0.5):
        self.name = name
        self.action = action
        self.timeout = timeout
        self.retries = retries
        self.verify = verify
        self.backoff = backoff  # 每次重试递增等待时间
        self._last_error = None
        self._attempt_count = 0

    def execute(self) -> bool:
        self._attempt_count = 0
        for attempt in range(self.retries):
            self._attempt_count = attempt + 1
            try:
                deadline = time.time() + self.timeout
                while time.time() < deadline:
                    if self.action():
                        if self.verify and not self.verify():
                            time.sleep(0.3)
                            continue
                        return True
                    time.sleep(self.backoff * (attempt + 1))  # 递增回退
            except Exception as e:
                self._last_error = str(e)
                time.sleep(self.backoff * (attempt + 1))
        return False


class BaseTask(ABC):
    """任务基类。子类需实现 build_steps()。

    模式:
      - 每轮 tick() 前调用 handle_anomalies() 检查异常弹窗
      - 步骤失败自动回退 + 重试
      - 支持暂停/恢复/取消
    """

    name: str = "base"
    description: str = ""
    MAX_CONSECUTIVE_ERRORS = 5  # 连续错误上限

    def __init__(self, game_context: dict):
        self.ctx = game_context
        self.state = TaskState.IDLE
        self._current_step = 0
        self._steps: list[Step] = []
        self._start_time = 0
        self._error_count = 0

    @abstractmethod
    def build_steps(self) -> list[Step]:
        """子类实现：返回任务步骤列表。"""
        ...

    def start(self) -> None:
        self._steps = self.build_steps()
        self._current_step = 0
        self._start_time = time.time()
        self._error_count = 0
        self.state = TaskState.RUNNING

    def handle_anomalies(self) -> bool:
        """处理异常弹窗/对话框等非预期 UI。

        返回 True 表示处理了一个异常（调用方应 sleep 后重试）。
        子类可重写添加任务特定的异常处理。
        """
        detector = self.ctx.get("state_detector")
        click = self.ctx.get("click")
        hotkey = self.ctx.get("input_hotkey")

        handled = False

        # 通用对话框处理：点击"下一步"推进
        if detector and detector.current.name == "DIALOG":
            if click:
                click(400, 520)
            time.sleep(0.5)
            handled = True

        # 战斗状态：不处理（由 battle_handler 负责）
        # if detector and detector.current.name == "BATTLE":
        #     return False  # 让任务自己的战斗处理接管

        return handled

    def run_action_script(self, script_path: str | Path) -> bool:
        """执行 YAML 动作脚本，便于把重复点击/等待流程外置配置。"""
        from core.action_script import run_action_script

        return run_action_script(script_path, self.ctx)

    def tick(self) -> TaskState:
        if self.state != TaskState.RUNNING:
            return self.state

        # 每次 tick 先处理异常
        if self.handle_anomalies():
            time.sleep(0.3)
            return self.state

        if self._current_step >= len(self._steps):
            self.state = TaskState.COMPLETED
            return self.state

        step = self._steps[self._current_step]
        if step.execute():
            self._current_step += 1
            self._error_count = 0
            if self._current_step >= len(self._steps):
                self.state = TaskState.COMPLETED
        else:
            self._error_count += 1
            if self._error_count >= self.MAX_CONSECUTIVE_ERRORS:
                print(f"[{self.name}] 连续 {self._error_count} 次失败，任务终止")
                self.state = TaskState.ERROR
            else:
                print(f"[{self.name}] 步骤 '{step.name}' 失败 "
                      f"(第 {step._attempt_count}/{step.retries} 次), "
                      f"错误: {step._last_error}")

        return self.state

    def pause(self) -> None:
        self.state = TaskState.PAUSED

    def resume(self) -> None:
        if self.state == TaskState.PAUSED:
            self.state = TaskState.RUNNING

    def cancel(self) -> None:
        self.state = TaskState.CANCELLED

    @property
    def progress(self) -> float:
        total = len(self._steps)
        return self._current_step / total if total else 1.0

    @property
    def current_step_name(self) -> str:
        if 0 <= self._current_step < len(self._steps):
            return self._steps[self._current_step].name
        return "完成"

    @property
    def elapsed(self) -> float:
        return time.time() - self._start_time


# ====== 任务调度器（dispatch table 模式，借鉴 lua-touchsprite） ======

TASK_REGISTRY: dict[str, type] = {}


def register_task(name: str):
    """装饰器：注册任务到全局调度表。"""
    def decorator(cls):
        TASK_REGISTRY[name] = cls
        return cls
    return decorator


def get_task(name: str, game_context: dict) -> BaseTask | None:
    """从注册表中创建任务实例。"""
    cls = TASK_REGISTRY.get(name)
    if cls:
        return cls(game_context)
    return None


def list_tasks() -> list[str]:
    """列出所有已注册的任务名称。"""
    return list(TASK_REGISTRY.keys())
