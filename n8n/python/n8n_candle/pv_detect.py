"""Pure-Python port of ben-arnao Peak_valley_detection (pv_detect.py).

Original: https://github.com/ben-arnao/Peak_valley_detection/blob/master/pv_detect.py
Adapted to stdlib only (no pandas/numpy) for the n8n task runner sandbox.
"""

from __future__ import annotations

from enum import Enum


def get_event_indexes(
    signal: list[float],
    com: float,
    beta: float,
    min_periods: int,
    condense_events: bool = True,
    backwards: bool = True,
) -> tuple[list[int], list[int]]:
    """
    Return (peak_indexes, valley_indexes) for a 1-D float signal.

    - com: EWM center-of-mass (pandas ewm(com=...))
    - beta: relative threshold vs moving average (val/ma - 1)
    - min_periods: warmup length; early points are incomplete
    - condense_events: keep only the most extreme event in consecutive runs
    - backwards: also mark events using a forward-looking EWM
    """
    if not signal:
        return [], []
    if min_periods < 1:
        raise ValueError("min_periods must be >= 1")
    if len(signal) <= min_periods:
        return [], []

    n = len(signal)
    flipped = list(reversed(signal))
    forward_ma = list(reversed(_exp_weighted_avg(flipped, com, min_periods)))

    # Forward pass: signal[:-min_periods] vs forward_ma (same length)
    fwd_signal = signal[: n - min_periods]
    fwd_ma = forward_ma[: len(fwd_signal)]
    forward_peaks, forward_valleys = _get_all_indexes_above_threshold(fwd_signal, fwd_ma, beta)

    if backwards:
        backward_ma = _exp_weighted_avg(signal, com, min_periods)
        # Original aligns signal[min_periods:] with full backward_ma list length n;
        # compare against ma[min_periods:] so indices are offset by min_periods.
        bwd_signal = signal[min_periods:]
        bwd_ma = backward_ma[min_periods:]
        bp, bv = _get_all_indexes_above_threshold(bwd_signal, bwd_ma, beta)
        backward_peaks = [i + min_periods for i in bp]
        backward_valleys = [i + min_periods for i in bv]
        all_peaks = sorted(set(forward_peaks + backward_peaks))
        all_valleys = sorted(set(forward_valleys + backward_valleys))
    else:
        all_peaks = forward_peaks
        all_valleys = forward_valleys

    if condense_events:
        return _condense_events(signal, all_peaks, all_valleys)
    return all_peaks, all_valleys


def local_extrema(signal: list[float], k: int = 3, *, kind: str) -> list[int]:
    """
    Confirmed local pivots: bar i is extreme vs k bars on both sides.

    kind='peak'  → strict local maximum
    kind='valley' → strict local minimum
    End bars (fewer than k neighbors) are never confirmed.
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    n = len(signal)
    if n < 2 * k + 1:
        return []
    out: list[int] = []
    want_peak = kind == "peak"
    for i in range(k, n - k):
        v = float(signal[i])
        if want_peak:
            if all(v > float(signal[i - j]) for j in range(1, k + 1)) and all(
                v > float(signal[i + j]) for j in range(1, k + 1)
            ):
                out.append(i)
        else:
            if all(v < float(signal[i - j]) for j in range(1, k + 1)) and all(
                v < float(signal[i + j]) for j in range(1, k + 1)
            ):
                out.append(i)
    return out


def local_peaks(highs: list[float], k: int = 3) -> list[int]:
    return local_extrema(highs, k, kind="peak")


def local_valleys(lows: list[float], k: int = 3) -> list[int]:
    return local_extrema(lows, k, kind="valley")


def condense_events_hl(
    highs: list[float],
    lows: list[float],
    all_peaks: list[int],
    all_valleys: list[int],
) -> tuple[list[int], list[int]]:
    """
    Alternate peak/valley runs; within a peak run keep highest High,
    within a valley run keep lowest Low.
    """
    if len(highs) != len(lows):
        raise ValueError("highs and lows must be the same length")
    n = len(highs)
    peak_set = {int(i) for i in all_peaks if 0 <= int(i) < n}
    valley_set = {int(i) for i in all_valleys if 0 <= int(i) < n}

    class Env(Enum):
        PEAK = 1
        VALLEY = 2

    mode: Env | None = None
    best_event: tuple[int | None, float | None] = (None, None)
    best_peaks: list[int] = []
    best_valleys: list[int] = []

    for idx in range(n):
        is_peak = idx in peak_set
        is_valley = idx in valley_set
        high = float(highs[idx])
        low = float(lows[idx])

        if mode is None:
            if is_peak:
                mode = Env.PEAK
                best_event = (idx, high)
            elif is_valley:
                mode = Env.VALLEY
                best_event = (idx, low)
            continue

        if mode == Env.PEAK and is_peak:
            if best_event[1] is None or high > best_event[1]:
                best_event = (idx, high)
        elif mode == Env.VALLEY and is_valley:
            if best_event[1] is None or low < best_event[1]:
                best_event = (idx, low)
        elif mode == Env.PEAK and is_valley:
            if best_event[0] is not None:
                best_peaks.append(best_event[0])
            mode = Env.VALLEY
            best_event = (idx, low)
        elif mode == Env.VALLEY and is_peak:
            if best_event[0] is not None:
                best_valleys.append(best_event[0])
            mode = Env.PEAK
            best_event = (idx, high)

    if mode == Env.PEAK and best_event[0] is not None:
        best_peaks.append(best_event[0])
    elif mode == Env.VALLEY and best_event[0] is not None:
        best_valleys.append(best_event[0])

    return best_peaks, best_valleys


def _exp_weighted_avg(signal: list[float], com: float, min_periods: int) -> list[float | None]:
    """Pandas-compatible EWM mean with adjust=True (default)."""
    alpha = 1.0 / (1.0 + float(com))
    out: list[float | None] = []
    num = 0.0
    den = 0.0
    for i, x in enumerate(signal):
        x = float(x)
        num = x + (1.0 - alpha) * num
        den = 1.0 + (1.0 - alpha) * den
        if i + 1 < min_periods:
            out.append(None)
        else:
            out.append(num / den)
    return out


def _get_all_indexes_above_threshold(
    signal: list[float],
    moving_average: list[float | None],
    beta: float,
) -> tuple[list[int], list[int]]:
    peaks: list[int] = []
    valleys: list[int] = []
    for idx, val in enumerate(signal):
        ma = moving_average[idx] if idx < len(moving_average) else None
        if ma is None or ma == 0:
            continue
        diff = float(val) / float(ma) - 1.0
        if diff > beta:
            peaks.append(idx)
        elif diff < -beta:
            valleys.append(idx)
    return peaks, valleys


def _condense_events(
    signal: list[float],
    all_peaks: list[int],
    all_valleys: list[int],
) -> tuple[list[int], list[int]]:
    class Env(Enum):
        PEAK = 1
        VALLEY = 2

    peak_set = set(all_peaks)
    valley_set = set(all_valleys)
    mode: Env | None = None
    best_event: tuple[int | None, float | None] = (None, None)
    best_peaks: list[int] = []
    best_valleys: list[int] = []

    for idx, val in enumerate(signal):
        val = float(val)
        is_peak = idx in peak_set
        is_valley = idx in valley_set

        if mode is None:
            if is_peak:
                mode = Env.PEAK
                best_event = (idx, val)
            elif is_valley:
                mode = Env.VALLEY
                best_event = (idx, val)
            continue

        if mode == Env.PEAK and is_peak:
            if best_event[1] is None or val > best_event[1]:
                best_event = (idx, val)
        elif mode == Env.VALLEY and is_valley:
            if best_event[1] is None or val < best_event[1]:
                best_event = (idx, val)
        elif mode == Env.PEAK and is_valley:
            if best_event[0] is not None:
                best_peaks.append(best_event[0])
            mode = Env.VALLEY
            best_event = (idx, val)
        elif mode == Env.VALLEY and is_peak:
            if best_event[0] is not None:
                best_valleys.append(best_event[0])
            mode = Env.PEAK
            best_event = (idx, val)

    # Flush last open run
    if mode == Env.PEAK and best_event[0] is not None:
        best_peaks.append(best_event[0])
    elif mode == Env.VALLEY and best_event[0] is not None:
        best_valleys.append(best_event[0])

    return best_peaks, best_valleys
