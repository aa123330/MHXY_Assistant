"""游戏常量：UI 区域、颜色阈值、YOLO 类别映射等。

所有数值基于 800×600 窗口，若窗口尺寸不同需按比例缩放。
"""

from enum import Enum, auto


class GameState(Enum):
    IDLE = auto()
    WALKING = auto()
    BATTLE = auto()
    DIALOG = auto()
    LOADING = auto()
    TRADING = auto()
    UNKNOWN = auto()


# 窗口参考尺寸
REF_WIDTH = 800
REF_HEIGHT = 600

# 小地图在窗口中的位置（客户区坐标）
MINIMAP_RECT = (600, 40, 780, 220)
MINIMAP_CENTER = (690, 130)

# 战斗 UI
BATTLE_COMMAND_RECT = (50, 400, 750, 500)
BATTLE_HP_BAR_COLOR = (0, 0, 255)
BATTLE_MP_BAR_COLOR = (0, 165, 255)

# 对话框
DIALOG_RECT = (100, 380, 700, 560)
DIALOG_NEXT_BUTTON = (400, 520)

# NPC 对话选项
NPC_OPTION_RECT = (200, 200, 600, 450)

# 聊天框
CHAT_RECT = (10, 480, 790, 595)

# 任务追踪面板
QUEST_TRACKER_RECT = (610, 240, 790, 370)

# 角色状态区
PLAYER_STATUS_RECT = (0, 0, 200, 60)

# YOLO 类别映射（默认值，实际以训练模型为准）
YOLO_CLASSES = {
    0: "cursor",       # 光标/鼠标指针
    1: "npc",          # NPC
    2: "monster",      # 怪物
    3: "button",       # 按钮/UI元素
    4: "dialog_box",   # 对话框
    5: "item",         # 物品
}

# 师门常用快捷键
HOTKEY_BACK_MASTER = "f8"         # 回师门
HOTKEY_ATTACK = ("alt", "a")      # 物理攻击
HOTKEY_SKILL = ("alt", "w")       # 法术
HOTKEY_DEFEND = ("alt", "d")      # 防御


def scale_rect(rect: tuple, actual_size: tuple) -> tuple:
    """按实际窗口尺寸等比缩放矩形坐标。"""
    w_scale = actual_size[0] / REF_WIDTH
    h_scale = actual_size[1] / REF_HEIGHT
    return tuple(
        int(v * (w_scale if i % 2 == 0 else h_scale))
        for i, v in enumerate(rect)
    )
