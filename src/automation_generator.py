"""
Automation Curve Generator
オートメーションカーブのポイントを生成する
"""

import math
from typing import List, Tuple


def generate_automation_points(
    shape: str,
    start_val: float,
    end_val: float,
    start_time: float,
    duration_beats: float,
    resolution: int = 32
) -> List[Tuple[float, float, float]]:
    """
    オートメーションカーブのポイントを生成する。

    Args:
        shape: カーブ形状 ("linear", "exponential", "s_curve", "sine", "step")
        start_val: 開始値 (0.0-1.0)
        end_val: 終了値 (0.0-1.0)
        start_time: 開始位置（拍）
        duration_beats: 長さ（拍）
        resolution: ポイント数（デフォルト32）

    Returns:
        list of (time, value, step_duration) タプル
    """
    if resolution < 2:
        resolution = 2

    step_duration = duration_beats / resolution
    points = []

    for i in range(resolution):
        t = i / (resolution - 1)  # 0.0 ~ 1.0 の正規化位置
        time_pos = start_time + i * step_duration

        if shape == "linear":
            value = _linear(t, start_val, end_val)
        elif shape == "exponential":
            value = _exponential(t, start_val, end_val)
        elif shape == "s_curve":
            value = _s_curve(t, start_val, end_val)
        elif shape == "sine":
            value = _sine(t, start_val, end_val)
        elif shape == "step":
            value = _step(t, start_val, end_val, resolution)
        else:
            value = _linear(t, start_val, end_val)

        value = max(0.0, min(1.0, value))
        points.append((time_pos, value, step_duration))

    return points


def _linear(t: float, start: float, end: float) -> float:
    """直線的な変化"""
    return start + (end - start) * t


def _exponential(t: float, start: float, end: float) -> float:
    """指数的な変化（フィルタースイープ向き）"""
    return start + (end - start) * (t ** 3)


def _s_curve(t: float, start: float, end: float) -> float:
    """S字カーブ（滑らかなフェード）"""
    # Smoothstep: 3t^2 - 2t^3
    s = 3 * t * t - 2 * t * t * t
    return start + (end - start) * s


def _sine(t: float, start: float, end: float) -> float:
    """サイン波（揺らぎ）- 1サイクル"""
    mid = (start + end) / 2
    amplitude = abs(end - start) / 2
    return mid + amplitude * math.sin(2 * math.pi * t)


def _step(t: float, start: float, end: float, resolution: int) -> float:
    """階段状の変化"""
    num_steps = max(4, resolution // 4)
    step_index = int(t * num_steps)
    step_index = min(step_index, num_steps - 1)
    return start + (end - start) * (step_index / (num_steps - 1))
