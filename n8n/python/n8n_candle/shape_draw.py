"""Pillow geometry drawer — shapes only; no LLM / no chart semantics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .chart_themes import get_theme
from .point_index import resolve_ref


def _parse_color(raw: Any, default: tuple[int, int, int]) -> tuple[int, int, int]:
    if raw is None:
        return default
    if isinstance(raw, (list, tuple)) and len(raw) >= 3:
        return int(raw[0]), int(raw[1]), int(raw[2])
    s = str(raw).strip()
    if s.startswith("#") and len(s) == 7:
        return int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16)
    return default


def _load_font(theme: dict[str, Any], size: int | None = None) -> ImageFont.ImageFont:
    sz = int(size or theme.get("font_size", 12))
    for path in theme.get("font_paths") or []:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, sz)
            except OSError:
                continue
    return ImageFont.load_default()


def _midpoint(a: list[int], b: list[int]) -> tuple[int, int]:
    return (a[0] + b[0]) // 2, (a[1] + b[1]) // 2


def _draw_label(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    color: tuple[int, int, int],
) -> None:
    if not text:
        return
    x, y = xy
    draw.text((x + 4, y - 14), text, fill=color, font=font)


def draw_shapes(
    image: Image.Image,
    commands: list[dict[str, Any]],
    point_index: dict[str, list[int]],
    *,
    plot_bbox: list[int] | None = None,
    theme_name: str | None = None,
) -> tuple[Image.Image, list[dict[str, Any]], list[str]]:
    """
    Overlay geometry from draw_commands onto a copy of image.

    Returns (image, applied_commands, errors).
    Invalid refs / unknown shapes are skipped and listed in errors.
    """
    _, theme = get_theme(theme_name)
    img = image.copy().convert("RGB")
    draw = ImageDraw.Draw(img)
    font = _load_font(theme)
    default_line = tuple(theme.get("overlay_line", (41, 98, 255)))
    default_label = tuple(theme.get("overlay_label", (80, 80, 90)))

    if plot_bbox and len(plot_bbox) >= 4:
        x0, _y0, x1, _y1 = (int(v) for v in plot_bbox[:4])
    else:
        x0, x1 = 0, img.width - 1

    applied: list[dict[str, Any]] = []
    errors: list[str] = []

    for i, cmd in enumerate(commands or []):
        if not isinstance(cmd, dict):
            errors.append(f"command[{i}]: not an object")
            continue
        # Agents sometimes emit "type" instead of locked "shape"
        shape = str(cmd.get("shape") or cmd.get("type") or "").strip().lower()
        color = _parse_color(cmd.get("color"), default_line)
        width = max(1, int(cmd.get("width") or 2))
        label = str(cmd.get("label") or "")

        try:
            if shape == "line":
                a = resolve_ref(str(cmd["from"]), point_index)
                b = resolve_ref(str(cmd["to"]), point_index)
                draw.line([tuple(a), tuple(b)], fill=color, width=width)
                _draw_label(draw, _midpoint(a, b), label, font, default_label)
                applied.append({**cmd, "_resolved": {"from": a, "to": b}})

            elif shape == "hline":
                at = resolve_ref(str(cmd["at"]), point_index)
                y = at[1]
                draw.line([(x0, y), (x1, y)], fill=color, width=width)
                _draw_label(draw, (x0 + 8, y), label, font, default_label)
                applied.append({**cmd, "_resolved": {"at": at, "y": y}})

            elif shape == "polyline":
                refs = cmd.get("points") or []
                if not isinstance(refs, list) or len(refs) < 2:
                    raise ValueError("polyline needs points[] with ≥2 refs")
                pts = [resolve_ref(str(r), point_index) for r in refs]
                for j in range(len(pts) - 1):
                    draw.line([tuple(pts[j]), tuple(pts[j + 1])], fill=color, width=width)
                mid = pts[len(pts) // 2]
                _draw_label(draw, (mid[0], mid[1]), label, font, default_label)
                applied.append({**cmd, "_resolved": {"points": pts}})

            else:
                errors.append(f"command[{i}]: unknown shape {shape!r}")
        except (KeyError, TypeError, ValueError) as e:
            errors.append(f"command[{i}]: {e}")

    return img, applied, errors
