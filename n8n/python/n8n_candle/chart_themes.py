"""TradingView-style RGB draw tokens for Pillow chart rendering."""

from __future__ import annotations

from typing import Any

ThemeSpec = dict[str, Any]

# RGB tuples (R, G, B). TradingView defaults: up #26a69a, down #ef5350.
THEMES: dict[str, ThemeSpec] = {
    "tradingview_light": {
        "bg": (255, 255, 255),
        "grid": (232, 232, 232),  # fallback
        "grid_price": (210, 220, 235),  # soft blue — price horizontals
        "grid_volume": (230, 218, 210),  # soft warm — volume horizontals
        "grid_date": (220, 220, 225),  # neutral — vertical date guides
        "axis": (120, 123, 134),
        "axis_line": (210, 210, 215),
        "green": (38, 166, 154),
        "red": (239, 83, 80),
        "wick": None,  # None → same as body color
        "volume_green": (38, 166, 154, 140),
        "volume_red": (239, 83, 80, 140),
        "volume_sep": (220, 220, 220),
        "volume_ratio": 0.18,
        # Left volume scale + right price scale + bottom date axis
        "plot_margin": {"top": 20, "bottom": 40, "left": 64, "right": 72},
        "font_size": 12,
        "font_paths": [
            "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
            "/usr/share/fonts/google-noto-vf/NotoSans[wght].ttf",
        ],
        "width": 1600,
        "height": 900,
        "overlay_line": (41, 98, 255),  # #2962ff
        "overlay_label": (80, 80, 90),
        "sma_line": (255, 152, 0),  # amber MA
        "sma_width": 2,
        "swing_peak": (198, 40, 40),
        "swing_valley": (21, 101, 192),
    },
    "tradingview_dark": {
        "bg": (19, 23, 34),
        "grid": (42, 46, 57),
        "grid_price": (38, 52, 78),  # blue-tinted
        "grid_volume": (58, 46, 42),  # warm-tinted
        "grid_date": (48, 52, 62),  # neutral
        "axis": (138, 146, 160),
        "axis_line": (42, 46, 57),
        "green": (38, 166, 154),
        "red": (239, 83, 80),
        "wick": None,
        "volume_green": (38, 166, 154, 140),
        "volume_red": (239, 83, 80, 140),
        "volume_sep": (42, 46, 57),
        "volume_ratio": 0.18,
        "plot_margin": {"top": 20, "bottom": 40, "left": 64, "right": 72},
        "font_size": 12,
        "font_paths": [
            "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
            "/usr/share/fonts/google-noto-vf/NotoSans[wght].ttf",
        ],
        "width": 1600,
        "height": 900,
        "overlay_line": (100, 181, 246),
        "overlay_label": (180, 185, 195),
        "sma_line": (255, 183, 77),
        "sma_width": 2,
        "swing_peak": (239, 154, 154),
        "swing_valley": (144, 202, 249),
    },
}

DEFAULT_THEME = "tradingview_light"
MAX_BARS = 200


def get_theme(name: str | None) -> tuple[str, ThemeSpec]:
    """Return (theme_name, theme_spec). Falls back to tradingview_light."""
    key = (name or DEFAULT_THEME).strip().lower()
    if key not in THEMES:
        key = DEFAULT_THEME
    return key, THEMES[key]
