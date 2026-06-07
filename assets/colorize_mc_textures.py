"""
Minecraft 材质灰阶着色脚本
将灰阶材质图按 MC 标准的乘法混合模式着色为指定颜色。

用法：直接运行即可，输出文件与原文件同目录，后缀为 _colored.png
依赖：pip install Pillow numpy
"""

from pathlib import Path
import numpy as np
from PIL import Image


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """将 #RRGGBB 格式的颜色字符串解析为 (R, G, B) 元组。"""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        raise ValueError(f"无效的颜色格式：{hex_color}，应为 #RRGGBB")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def colorize(input_path: str | Path, tint_hex: str, output_suffix: str = "_colored") -> Path:
    """
    对灰阶 PNG 图像进行 MC 风格的乘法着色。

    MC 的群系着色原理：output = (grayscale / 255) × tint_color
    即把灰度值当作亮度因子，乘以 biome 色彩，Alpha 通道原样保留。

    Args:
        input_path:    输入灰阶图像路径
        tint_hex:      目标颜色，如 "#59C93C"
        output_suffix: 追加在主文件名末尾的后缀（不含扩展名）

    Returns:
        输出文件的 Path 对象
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"文件不存在：{input_path}")

    # 强制转为 RGBA，保证有 4 个通道
    img = Image.open(input_path).convert("RGBA")
    arr = np.array(img, dtype=np.float32)  # shape: (H, W, 4)

    tint_r, tint_g, tint_b = hex_to_rgb(tint_hex)

    # 灰阶图像 R=G=B，取 R 通道作为亮度因子（归一化到 [0, 1]）
    luminance = arr[:, :, 0] / 255.0  # shape: (H, W)

    # 乘法混合：各颜色通道 = 亮度 × 目标色
    result = np.empty_like(arr)
    result[:, :, 0] = luminance * tint_r
    result[:, :, 1] = luminance * tint_g
    result[:, :, 2] = luminance * tint_b
    result[:, :, 3] = arr[:, :, 3]          # Alpha 通道原样保留

    result = np.clip(result, 0, 255).astype(np.uint8)

    # 构造输出路径：同目录，主文件名追加 suffix
    output_path = input_path.with_stem(input_path.stem + output_suffix)
    Image.fromarray(result, "RGBA").save(output_path, optimize=False)

    print(f"[OK] {input_path.name}  →  tint {tint_hex}  →  {output_path.name}")
    return output_path


# ──────────────────────────────────────────────
# 任务配置：(文件路径, 标准着色颜色)
# ──────────────────────────────────────────────
TASKS = [
    (r"assets\textures\block\grass_block_top.png", "#59C93C"),
    (r"assets\textures\block\oak_leaves.png",      "#48b518"),
]

if __name__ == "__main__":
    print("=== Minecraft 材质灰阶着色 ===\n")
    for path, tint in TASKS:
        try:
            colorize(path, tint)
        except FileNotFoundError as e:
            print(f"[SKIP] {e}")
        except Exception as e:
            print(f"[ERROR] {path}: {e}")
    print("\n完成。")
