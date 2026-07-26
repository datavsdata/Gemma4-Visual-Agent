"""OHLC(+volume) JSON → TradingView-style Pillow chart + exact pixel OHLC points."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .chart_themes import MAX_BARS, get_theme


@dataclass
class ChartLayout:
    """Shared transforms for render + later overlays."""

    width: int
    height: int
    plot_left: int
    plot_top: int
    plot_right: int
    plot_bottom: int
    vol_top: int
    vol_bottom: int
    n: int
    price_min: float
    price_max: float
    volume_max: float
    has_volume: bool

    @property
    def plot_width(self) -> int:
        return max(self.plot_right - self.plot_left, 1)

    @property
    def plot_height(self) -> int:
        return max(self.plot_bottom - self.plot_top, 1)

    @property
    def vol_height(self) -> int:
        return max(self.vol_bottom - self.vol_top, 1)

    def index_to_x(self, index: int) -> int:
        if self.n <= 1:
            return (self.plot_left + self.plot_right) // 2
        slot = self.plot_width / self.n
        return int(self.plot_left + slot * (index + 0.5))

    def price_to_y(self, price: float) -> int:
        span = max(self.price_max - self.price_min, 1e-9)
        t = (price - self.price_min) / span
        return int(self.plot_bottom - t * self.plot_height)

    def volume_to_y(self, volume: float) -> int:
        """Top y of a volume bar (bars grow upward from vol_bottom)."""
        vmax = max(self.volume_max, 1e-9)
        t = max(0.0, min(float(volume), vmax)) / vmax
        return int(self.vol_bottom - t * self.vol_height)

    def candle_half_width(self) -> int:
        slot = self.plot_width / max(self.n, 1)
        return max(1, int(slot * 0.35))


def _as_float(v: Any, key: str) -> float:
    try:
        return float(v)
    except (TypeError, ValueError) as e:
        raise ValueError(f"candle.{key} must be numeric, got {v!r}") from e


def normalize_ohlc(candles: list[dict[str, Any]], max_bars: int = MAX_BARS) -> list[dict[str, Any]]:
    """Validate OHLC(+optional volume/date) rows and keep the last max_bars."""
    if not candles:
        raise ValueError("candles must be a non-empty list")
    rows: list[dict[str, Any]] = []
    for i, raw in enumerate(candles):
        if not isinstance(raw, dict):
            raise ValueError(f"candles[{i}] must be an object")
        o = _as_float(raw.get("open"), "open")
        h = _as_float(raw.get("high"), "high")
        l = _as_float(raw.get("low"), "low")
        c = _as_float(raw.get("close"), "close")
        hi = max(h, o, c)
        lo = min(l, o, c)
        vol = 0.0
        if raw.get("volume") is not None:
            vol = max(0.0, _as_float(raw.get("volume"), "volume"))
        row: dict[str, Any] = {"open": o, "high": hi, "low": lo, "close": c, "volume": vol}
        if raw.get("date") is not None:
            row["date"] = str(raw["date"])
        if raw.get("sma150") is not None and raw.get("sma150") != "":
            try:
                row["sma150"] = float(raw["sma150"])
            except (TypeError, ValueError):
                pass
        swing = str(raw.get("swing") or "").strip().upper()
        if swing in {"H", "L", "HH", "HL", "LH", "LL"}:
            row["swing"] = swing
        rows.append(row)
    if len(rows) > max_bars:
        rows = rows[-max_bars:]
    return rows


def build_layout(
    rows: list[dict[str, Any]],
    theme: dict[str, Any],
    width: int | None = None,
    height: int | None = None,
) -> ChartLayout:
    w = int(width or theme["width"])
    h = int(height or theme["height"])
    m = theme["plot_margin"]
    left = int(m["left"])
    top = int(m["top"])
    right = w - int(m["right"])
    outer_bottom = h - int(m["bottom"])

    prices = [p for r in rows for p in (r["open"], r["high"], r["low"], r["close"])]
    for r in rows:
        sma = r.get("sma150")
        if sma is not None:
            try:
                prices.append(float(sma))
            except (TypeError, ValueError):
                pass
    pmin, pmax = min(prices), max(prices)
    pad = max((pmax - pmin) * 0.05, abs(pmax) * 1e-6, 1e-6)

    volumes = [float(r.get("volume", 0.0)) for r in rows]
    vmax = max(volumes) if volumes else 0.0
    has_volume = vmax > 0.0

    if has_volume:
        inner_h = max(outer_bottom - top, 1)
        vol_h = max(int(inner_h * float(theme.get("volume_ratio", 0.18))), 24)
        gap = 10
        vol_bottom = outer_bottom
        vol_top = vol_bottom - vol_h
        plot_bottom = vol_top - gap
    else:
        vol_top = vol_bottom = outer_bottom
        plot_bottom = outer_bottom

    return ChartLayout(
        width=w,
        height=h,
        plot_left=left,
        plot_top=top,
        plot_right=right,
        plot_bottom=plot_bottom,
        vol_top=vol_top,
        vol_bottom=vol_bottom,
        n=len(rows),
        price_min=pmin - pad,
        price_max=pmax + pad,
        volume_max=vmax,
        has_volume=has_volume,
    )


def _load_font(theme: dict[str, Any]) -> ImageFont.ImageFont:
    size = int(theme.get("font_size", 12))
    for path in theme.get("font_paths") or []:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _nice_ticks(vmin: float, vmax: float, target: int = 6) -> list[float]:
    """Nice round tick values between vmin and vmax (inclusive-ish)."""
    if not math.isfinite(vmin) or not math.isfinite(vmax):
        return [0.0]
    if vmax <= vmin:
        return [vmin]
    span = vmax - vmin
    raw = span / max(target, 1)
    exp = math.floor(math.log10(raw)) if raw > 0 else 0
    base = 10**exp
    step = base
    for mult in (1.0, 2.0, 2.5, 5.0, 10.0):
        cand = mult * base
        if cand >= raw * 0.85:
            step = cand
            break
    start = math.ceil(vmin / step) * step
    ticks: list[float] = []
    x = start
    # Avoid float drift
    for _ in range(target * 3):
        if x > vmax + step * 1e-9:
            break
        if x >= vmin - step * 1e-9:
            ticks.append(round(x, 10))
        x += step
    if not ticks:
        ticks = [vmin, vmax]
    return ticks


def _fmt_price(v: float) -> str:
    av = abs(v)
    if av >= 1000:
        return f"{v:,.2f}"
    if av >= 100:
        return f"{v:.2f}"
    if av >= 10:
        return f"{v:.2f}"
    if av >= 1:
        return f"{v:.3f}"
    return f"{v:.4f}"


def _fmt_volume(v: float) -> str:
    """TradingView-like compact volume (K / M / B)."""
    av = abs(v)
    if av >= 1_000_000_000:
        return f"{v / 1_000_000_000:.2f}B"
    if av >= 1_000_000:
        return f"{v / 1_000_000:.2f}M"
    if av >= 1_000:
        return f"{v / 1_000:.2f}K"
    return f"{v:.0f}"


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    s = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _fmt_date(dt: datetime | None, prev: datetime | None) -> str:
    if dt is None:
        return ""
    # Show year when it changes or on first label
    if prev is None or dt.year != prev.year:
        return dt.strftime("%b '%y")
    return dt.strftime("%d %b")


def _date_indices(n: int, target: int = 8) -> list[int]:
    if n <= 0:
        return []
    if n == 1:
        return [0]
    step = max(1, n // target)
    idxs = list(range(0, n, step))
    # Only pin the last bar if it is far enough from the previous tick
    # (avoids bunched "17 Jul" / "20 Jul" at the right edge).
    min_gap = max(step // 2, 2)
    if idxs[-1] != n - 1 and (n - 1 - idxs[-1]) >= min_gap:
        idxs.append(n - 1)
    elif idxs[-1] != n - 1:
        idxs[-1] = n - 1  # replace near-last with true last
    return idxs


def _draw_grid(
    draw: ImageDraw.ImageDraw,
    layout: ChartLayout,
    theme: dict[str, Any],
) -> list[float]:
    """Draw price/volume/date grid lines (behind series). Returns price tick levels."""
    grid_fallback = tuple(theme["grid"])
    grid_price = tuple(theme.get("grid_price", grid_fallback))
    grid_volume = tuple(theme.get("grid_volume", grid_fallback))
    grid_date = tuple(theme.get("grid_date", grid_fallback))
    y_bot = layout.vol_bottom if layout.has_volume else layout.plot_bottom

    price_ticks = _nice_ticks(layout.price_min, layout.price_max, target=6)
    for price in price_ticks:
        y = layout.price_to_y(price)
        if y < layout.plot_top - 2 or y > layout.plot_bottom + 2:
            continue
        draw.line([(layout.plot_left, y), (layout.plot_right, y)], fill=grid_price, width=1)

    for i in _date_indices(layout.n, target=8):
        x = layout.index_to_x(i)
        draw.line([(x, layout.plot_top), (x, y_bot)], fill=grid_date, width=1)

    if layout.has_volume:
        vol_ticks = _nice_ticks(0.0, layout.volume_max, target=3)
        # Skip exact 0 — baseline is the axis line; labeling it crowds the date row
        vol_ticks = [v for v in vol_ticks if v > 0]
        for vol in vol_ticks:
            y = layout.volume_to_y(vol)
            if y < layout.vol_top - 2 or y > layout.vol_bottom - 4:
                continue
            draw.line([(layout.plot_left, y), (layout.plot_right, y)], fill=grid_volume, width=1)
        sep = tuple(theme.get("volume_sep", grid_fallback))
        draw.line(
            [(layout.plot_left, layout.vol_top - 5), (layout.plot_right, layout.vol_top - 5)],
            fill=sep,
            width=1,
        )
    return price_ticks


def _draw_axis_labels(
    draw: ImageDraw.ImageDraw,
    layout: ChartLayout,
    rows: list[dict[str, Any]],
    theme: dict[str, Any],
    font: ImageFont.ImageFont,
) -> None:
    """TradingView-style scales: price on the right, volume on the left, date at bottom."""
    axis = tuple(theme["axis"])
    axis_line = tuple(theme.get("axis_line", theme["grid"]))
    y_bot = layout.vol_bottom if layout.has_volume else layout.plot_bottom
    label_pad = 4  # min gap between adjacent date labels

    # Price scale — right (keep clear of volume separator)
    for price in _nice_ticks(layout.price_min, layout.price_max, target=6):
        y = layout.price_to_y(price)
        if y < layout.plot_top + 4 or y > layout.plot_bottom - 10:
            continue
        draw.text((layout.plot_right + 8, y - 6), _fmt_price(price), fill=axis, font=font)

    # Volume scale — left (volume pane only; skip 0 baseline)
    if layout.has_volume:
        vol_ticks = [v for v in _nice_ticks(0.0, layout.volume_max, target=3) if v > 0]
        for vol in vol_ticks:
            y = layout.volume_to_y(vol)
            if y < layout.vol_top + 4 or y > layout.vol_bottom - 10:
                continue
            label = _fmt_volume(vol)
            bbox = draw.textbbox((0, 0), label, font=font)
            tw = bbox[2] - bbox[0]
            draw.text((layout.plot_left - 8 - tw, y - 6), label, fill=axis, font=font)
        draw.line(
            [(layout.plot_left, layout.vol_top), (layout.plot_left, layout.vol_bottom)],
            fill=axis_line,
            width=1,
        )

    # Right spine (price) + bottom spine (date)
    draw.line([(layout.plot_right, layout.plot_top), (layout.plot_right, y_bot)], fill=axis_line, width=1)
    draw.line([(layout.plot_left, y_bot), (layout.plot_right, y_bot)], fill=axis_line, width=1)

    # Date axis — collision-aware placement inside plot x-range
    prev_dt: datetime | None = None
    prev_right = layout.plot_left - label_pad
    for i in _date_indices(layout.n, target=8):
        x = layout.index_to_x(i)
        dt = _parse_date(str(rows[i].get("date") or "")) if i < len(rows) else None
        label = _fmt_date(dt, prev_dt) if dt else str(i)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        # Prefer centered under tick; keep clear of right price gutter / left edge
        tx = x - tw // 2
        max_tx = layout.plot_right - tw - 10
        min_tx = layout.plot_left + 2
        if max_tx < min_tx:
            continue
        tx = max(min_tx, min(tx, max_tx))
        if tx < prev_right + label_pad:
            # Near-right: left-align to tick if that still fits without collision
            tx_alt = min(max_tx, max(min_tx, x - tw))
            if tx_alt < prev_right + label_pad:
                continue  # drop this label
            tx = tx_alt
        draw.text((tx, y_bot + 6), label, fill=axis, font=font)
        prev_right = tx + tw
        if dt:
            prev_dt = dt


def _draw_volumes(
    base: Image.Image,
    layout: ChartLayout,
    rows: list[dict[str, Any]],
    theme: dict[str, Any],
) -> None:
    if not layout.has_volume:
        return
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    half_w = layout.candle_half_width()
    vg = tuple(theme["volume_green"])
    vr = tuple(theme["volume_red"])

    for i, row in enumerate(rows):
        vol = float(row.get("volume", 0.0))
        if vol <= 0:
            continue
        color_name = "green" if row["close"] >= row["open"] else "red"
        fill = vg if color_name == "green" else vr
        cx = layout.index_to_x(i)
        y_top = layout.volume_to_y(vol)
        y_bot = layout.vol_bottom
        if y_bot <= y_top:
            y_top = y_bot - 1
        draw.rectangle(
            [cx - half_w, y_top, cx + half_w, y_bot],
            fill=fill,
        )

    composed = Image.alpha_composite(base.convert("RGBA"), overlay)
    base.paste(composed.convert("RGB"))


def _draw_sma(
    draw: ImageDraw.ImageDraw,
    layout: ChartLayout,
    rows: list[dict[str, Any]],
    theme: dict[str, Any],
) -> None:
    color = tuple(theme.get("sma_line") or theme.get("overlay_line", (41, 98, 255)))
    width = int(theme.get("sma_width", 2))
    pts: list[tuple[int, int]] = []
    for i, row in enumerate(rows):
        sma = row.get("sma150")
        if sma is None:
            if len(pts) >= 2:
                draw.line(pts, fill=color, width=width)
            pts = []
            continue
        pts.append((layout.index_to_x(i), layout.price_to_y(float(sma))))
    if len(pts) >= 2:
        draw.line(pts, fill=color, width=width)


def _draw_swing_labels(
    draw: ImageDraw.ImageDraw,
    layout: ChartLayout,
    rows: list[dict[str, Any]],
    theme: dict[str, Any],
    font: ImageFont.ImageFont,
) -> None:
    """Place H/L/HH/… at the candle high (peaks) or low (valleys) tip."""
    peak_color = tuple(theme.get("swing_peak") or theme.get("overlay_label", (80, 80, 90)))
    valley_color = tuple(theme.get("swing_valley") or theme.get("overlay_label", (80, 80, 90)))
    peak_labels = {"H", "HH", "LH"}
    valley_labels = {"L", "HL", "LL"}
    half_w = layout.candle_half_width()
    for i, row in enumerate(rows):
        label = str(row.get("swing") or "").strip().upper()
        if not label:
            continue
        cx = layout.index_to_x(i)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        # Anchor to the candle tip: peaks above high, valleys below low.
        # Nudge slightly right of center so text clears the wick.
        tip_x = cx + max(2, half_w // 2)
        if label in peak_labels:
            y_tip = layout.price_to_y(float(row["high"]))
            color = peak_color
            tx = tip_x - tw // 2
            ty = y_tip - th - 4
        elif label in valley_labels:
            y_tip = layout.price_to_y(float(row["low"]))
            color = valley_color
            tx = tip_x - tw // 2
            ty = y_tip + 4
        else:
            continue
        tx = max(layout.plot_left + 2, min(tx, layout.plot_right - tw - 2))
        ty = max(layout.plot_top + 2, min(ty, layout.plot_bottom - th - 2))
        draw.text((tx, ty), label, fill=color, font=font)


def render(
    candles: list[dict[str, Any]],
    theme_name: str | None = None,
    width: int | None = None,
    height: int | None = None,
    max_bars: int = MAX_BARS,
) -> dict[str, Any]:
    """
    Draw a TradingView-style candle chart with price / volume / date scales.

    Returns image (PIL RGB), layout, theme, and candles with pixel {o,h,l,c}.
    """
    theme_key, theme = get_theme(theme_name)
    rows = normalize_ohlc(candles, max_bars=max_bars)
    layout = build_layout(rows, theme, width=width, height=height)
    font = _load_font(theme)

    img = Image.new("RGB", (layout.width, layout.height), theme["bg"])
    draw = ImageDraw.Draw(img)
    _draw_grid(draw, layout, theme)

    if layout.has_volume:
        _draw_volumes(img, layout, rows, theme)
        draw = ImageDraw.Draw(img)  # refresh after paste

    half_w = layout.candle_half_width()
    out_candles: list[dict[str, Any]] = []

    for i, row in enumerate(rows):
        o, h, l, c = row["open"], row["high"], row["low"], row["close"]
        vol = float(row.get("volume", 0.0))
        color_name = "green" if c >= o else "red"
        body_rgb = tuple(theme[color_name])
        wick_rgb = tuple(theme["wick"]) if theme.get("wick") else body_rgb

        cx = layout.index_to_x(i)
        y_h = layout.price_to_y(h)
        y_l = layout.price_to_y(l)
        y_o = layout.price_to_y(o)
        y_c = layout.price_to_y(c)

        draw.line([(cx, y_h), (cx, y_l)], fill=wick_rgb, width=1)

        top, bot = min(y_o, y_c), max(y_o, y_c)
        if bot <= top:
            bot = top + 1
        draw.rectangle(
            [cx - half_w, top, cx + half_w, bot],
            fill=body_rgb,
            outline=body_rgb,
        )

        points = {
            "o": [cx, y_o],
            "h": [cx, y_h],
            "l": [cx, y_l],
            "c": [cx, y_c],
        }
        ohlc: dict[str, Any] = {"open": o, "high": h, "low": l, "close": c}
        if layout.has_volume:
            ohlc["volume"] = vol
        if row.get("date"):
            ohlc["date"] = row["date"]
        if row.get("sma150") is not None:
            ohlc["sma150"] = row["sma150"]
        if row.get("swing"):
            ohlc["swing"] = row["swing"]
        out_candles.append(
            {
                "index": i,
                "color": color_name,
                "points": points,
                "ohlc": ohlc,
            }
        )
        if row.get("swing"):
            out_candles[-1]["swing"] = row["swing"]

    _draw_sma(draw, layout, rows, theme)
    _draw_swing_labels(draw, layout, rows, theme, font)
    _draw_axis_labels(draw, layout, rows, theme, font)

    return {
        "image": img,
        "theme": theme_key,
        "layout": layout,
        "image_width": layout.width,
        "image_height": layout.height,
        "candle_count": len(out_candles),
        "candles": out_candles,
        "has_volume": layout.has_volume,
    }
