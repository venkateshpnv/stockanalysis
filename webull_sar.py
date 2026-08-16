"""Readable Python equivalent of Webull WebTrade's captured SAR routine.

This preserves Webull's nonstandard compiled behavior. It is not a generic
Wilder Parabolic SAR implementation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def webull_sar(
    bars: Sequence[Mapping[str, Any]],
    *,
    acceleration_factor: float = 0.02,
    max_acceleration_factor: float = 0.20,
) -> list[float]:
    """Calculate SAR values matching the recovered Webull implementation.

    Args:
        bars: Candles in chronological order (oldest to newest). Each candle
            must provide numeric ``high`` and ``low`` values.
        acceleration_factor: Increment applied after a qualifying new
            one-bar high/low. Webull's default is 0.02.
        max_acceleration_factor: Threshold after which Webull resets the
            acceleration to 0.02. Webull's default is 0.20.

    Returns:
        One SAR value per input candle. An empty input returns an empty list.
    """
    if not bars:
        return []

    highs = [float(bar["high"]) for bar in bars]
    lows = [float(bar["low"]) for bar in bars]

    size = len(bars)
    sar = [0.0] * size
    direction = [0] * size  # 1 = rising, 2 = falling
    acceleration = [0.0] * size
    extreme = [0.0] * size

    # This value is independently hard-coded in Webull's JS-to-WASM call.
    initial_acceleration_factor = 0.02

    # Webull always initializes the first bar as rising.
    direction[0] = 1
    sar[0] = lows[0]
    acceleration[0] = initial_acceleration_factor
    extreme[0] = highs[0]

    for index in range(1, size):
        previous_direction = direction[index - 1]
        previous_sar = sar[index - 1]

        # Webull checks reversal against the previous SAR before projection.
        if previous_direction == 1:
            direction[index] = 2 if previous_sar > lows[index] else 1
        else:
            direction[index] = 1 if previous_sar < highs[index] else 2

        same_direction = direction[index] == previous_direction
        next_acceleration = initial_acceleration_factor

        if same_direction and direction[index] == 1:
            next_acceleration = (
                acceleration[index - 1] + acceleration_factor
                if highs[index] > highs[index - 1]
                else acceleration[index - 1]
            )
        elif same_direction and direction[index] == 2:
            next_acceleration = (
                acceleration[index - 1] + acceleration_factor
                if lows[index] < lows[index - 1]
                else acceleration[index - 1]
            )

        # Exact recovered behavior: reset to 0.02 when the threshold is
        # exceeded instead of clamping to max_acceleration_factor.
        acceleration[index] = (
            next_acceleration
            if next_acceleration <= max_acceleration_factor
            else initial_acceleration_factor
        )

        # Webull projects toward the preceding candle's high/low, not the
        # accumulated trend extreme.
        target = highs[index - 1] if direction[index] == 1 else lows[index - 1]
        projected = previous_sar + acceleration[index] * (target - previous_sar)

        if direction[index] == 1:
            if not same_direction:
                extreme[index] = highs[index]
                projected = extreme[index - 1]
            else:
                extreme[index] = max(extreme[index - 1], highs[index])
                projected = min(projected, lows[index], lows[index - 1])
        elif not same_direction:
            extreme[index] = lows[index]
            projected = extreme[index - 1]
        else:
            extreme[index] = min(extreme[index - 1], lows[index])
            projected = max(projected, highs[index], highs[index - 1])

        sar[index] = projected

    return sar


if __name__ == "__main__":
    sample_bars = [
        {"high": 10, "low": 8},
        {"high": 11, "low": 9},
        {"high": 12, "low": 10},
        {"high": 9, "low": 7},
    ]
    print(webull_sar(sample_bars))

