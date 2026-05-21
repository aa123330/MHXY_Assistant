"""core 模块 — 每个子模块独立导入，单个失败不影响其他。"""

# window — 需要 pywin32
try:
    from .window import (
        find_window, find_window_regex, list_all_windows,
        get_window_rect, get_client_rect, get_client_size,
        activate_window, move_window, set_window_size, get_window_info,
        set_topmost, send_to_bottom, window_from_point,
        verify_click_window, enum_child_windows, get_window_process_name,
    )
except ImportError:
    pass

# capture — 需要 mss + pywin32
try:
    from .capture import capture_screen, capture_window, capture_region, capture_window_bg
except ImportError:
    pass

# input — 需要 pynput + Windows user32
try:
    from .input import (
        click, double_click, right_click, move_to, drag, press_key, hotkey, type_text,
        click_win32, move_win32, click_smart, click_away,
    )
except ImportError:
    pass

# template — 需要 cv2
try:
    from .template import load_template, match_template, match_all, get_center, match_best, \
        match_consensus, match_consensus_with_score, MATCH_METHODS
except ImportError:
    pass

# detector — 需要 ultralytics/torch。只导出类定义，不在启动时加载模型。
try:
    from .detector import YOLODetector, YOLODetectionWindow
except ImportError:
    pass

# OCR 依赖 paddle/paddleocr，体积大且导入链会触发 Cython/setuptools。
# 不在 core 包初始化时导入；需要 OCR 时直接 import core.ocr 懒加载。

# scene — 需要 cv2
try:
    from .scene import SceneDetector
except ImportError:
    pass

# hasher — 仅 PIL + numpy
try:
    from .hasher import ImageHasher, get_hasher
except ImportError:
    pass

# detect — 仅 numpy
try:
    from .detect import pixel_diff, diff_count, wait_for_change, \
        wait_for_stable, verify_disappeared
except ImportError:
    pass

# ai_model — 仅 numpy
try:
    from .ai_model import create_ai_model, BaseAIModel, encode_image
except ImportError:
    pass

# cloud — 仅 stdlib + urllib
try:
    from .cloud import CloudStorage
except ImportError:
    pass

# color_detect — 快速颜色像素检测
try:
    from .color_detect import (
        sample_pixel, sample_pixels, match_multi_point, match_any_fingerprint,
        count_color, ratio_color, has_red_text, has_battle_ui, has_dialog,
        find_red_text_center,
    )
except ImportError:
    pass
