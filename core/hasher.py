"""感知哈希图像匹配 — 借鉴 haungwanjun/mhxy_fz。

优势：
  - 极快（<1ms），纯 PIL/numpy，不依赖 OpenCV
  - 适合快速判断"某个 UI 出现了没有"
  - 搭配模板匹配使用：先哈希粗筛，再模板匹配精确定位

用法:
  from core.hasher import ImageHasher
  hasher = ImageHasher()
  screen_patch = capture(small_region)
  if hasher.matches(screen_patch, "shiyong_button"):
      click(x, y)
"""

import numpy as np
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data" / "hashes"


class ImageHasher:
    """感知哈希 — 快速图像相似度比较。"""

    def __init__(self, hash_size: int = 16):
        self.hash_size = hash_size
        self._cache: dict[str, str] = {}
        # 加载预存哈希库
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._load_cache()

    def _load_cache(self):
        for f in DATA_DIR.glob("*.hash"):
            try:
                self._cache[f.stem] = f.read_text().strip()
            except Exception:
                pass

    def compute(self, image) -> str:
        """计算图像感知哈希（十六进制字符串）。

        image: numpy BGR 数组 / PIL Image / 文件路径
        """
        if isinstance(image, np.ndarray):
            from PIL import Image
            # BGR → RGB → 灰度 → resize
            rgb = image[:, :, ::-1]  # BGR to RGB
            img = Image.fromarray(rgb).convert('L')
        elif isinstance(image, (str, Path)):
            from PIL import Image
            img = Image.open(str(image)).convert('L')
        elif hasattr(image, 'convert'):
            img = image.convert('L')
        else:
            raise TypeError(f"Unsupported image type: {type(image)}")

        img = img.resize((self.hash_size, self.hash_size), Image.Resampling.LANCZOS)
        pixels = list(img.getdata())
        avg = sum(pixels) / len(pixels)
        bits = ''.join('1' if p >= avg else '0' for p in pixels)

        # 每 4 位转十六进制
        return hex(int(bits, 2))[2:].zfill(self.hash_size * self.hash_size // 4)

    def hamming(self, h1: str, h2: str) -> int:
        """计算两个哈希字符串的汉明距离。"""
        if len(h1) != len(h2):
            # 补齐到相同长度
            max_len = max(len(h1), len(h2))
            h1 = h1.ljust(max_len, '0')
            h2 = h2.ljust(max_len, '0')
        return sum(c1 != c2 for c1, c2 in zip(h1, h2))

    def matches(self, image, template_name: str, threshold: int = 20) -> bool:
        """检查图像是否与预存模板匹配。"""
        if template_name not in self._cache:
            return False
        current_hash = self.compute(image)
        stored_hash = self._cache[template_name]
        return self.hamming(current_hash, stored_hash) < threshold

    def matches_any(self, image, template_names: list[str],
                    threshold: int = 20) -> Optional[str]:
        """检查图像是否匹配任一模板，返回匹配到的模板名。"""
        current_hash = self.compute(image)
        for name in template_names:
            if name not in self._cache:
                continue
            if self.hamming(current_hash, self._cache[name]) < threshold:
                return name
        return None

    def register(self, name: str, image) -> str:
        """注册一个模板哈希（采图后保存）。"""
        h = self.compute(image)
        self._cache[name] = h
        (DATA_DIR / f"{name}.hash").write_text(h)
        return h

    def verify_changed(self, image, template_name: str,
                       threshold: int = 20) -> bool:
        """验证 UI 是否已变化 — 返回 True 表示模板不再匹配（操作生效）。"""
        if template_name not in self._cache:
            return True  # 没有模板可对比，假定已变化
        return not self.matches(image, template_name, threshold)

    def compare_images(self, img1, img2, threshold: int = 15) -> bool:
        """比较两张图像是否相似。"""
        h1 = self.compute(img1)
        h2 = self.compute(img2)
        return self.hamming(h1, h2) < threshold

    @property
    def templates(self) -> list[str]:
        return sorted(self._cache.keys())


# 全局单例
_hasher: Optional[ImageHasher] = None


def get_hasher() -> ImageHasher:
    global _hasher
    if _hasher is None:
        _hasher = ImageHasher()
    return _hasher
