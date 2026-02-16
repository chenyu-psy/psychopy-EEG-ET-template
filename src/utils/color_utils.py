"""Utilities for converting HEX colors to formats required by backends."""

from __future__ import annotations


def _normalize_hex(hex_color: str) -> str:
    """Normalize #RGB/#RRGGBB input to uppercase #RRGGBB."""
    if not isinstance(hex_color, str):
        raise TypeError("HEX color must be a string.")

    color = hex_color.strip()
    if not color.startswith("#"):
        raise ValueError("HEX color must start with '#'.")

    value = color[1:]
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError("HEX color must be in #RGB or #RRGGBB format.")

    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError("HEX color contains invalid characters.") from exc

    return "#" + value.upper()


def hex_to_rgb255(hex_color: str) -> tuple[int, int, int]:
    """Convert HEX color to 0..255 RGB tuple."""
    color = _normalize_hex(hex_color)
    value = color[1:]
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def hex_to_psychopy_rgb(hex_color: str) -> tuple[float, float, float]:
    """Convert HEX color to PsychoPy `rgb` color space (-1..1)."""
    r, g, b = hex_to_rgb255(hex_color)
    return (r / 127.5 - 1.0, g / 127.5 - 1.0, b / 127.5 - 1.0)


def to_psychopy_rgb(color: str | tuple[float, float, float] | list[float]) -> tuple[float, float, float]:
    """Return a PsychoPy `rgb` color tuple; accepts HEX or existing numeric tuples."""
    if isinstance(color, str):
        return hex_to_psychopy_rgb(color)

    if len(color) != 3:
        raise ValueError("Color tuple/list must have exactly 3 values.")

    values = tuple(float(v) for v in color)
    if all(0.0 <= v <= 255.0 for v in values):
        return tuple(v / 127.5 - 1.0 for v in values)
    return values


def to_rgb255(color: str | tuple[float, float, float] | list[float]) -> tuple[int, int, int]:
    """Return an RGB 0..255 tuple; accepts HEX or PsychoPy `rgb` tuples."""
    if isinstance(color, str):
        return hex_to_rgb255(color)

    if len(color) != 3:
        raise ValueError("Color tuple/list must have exactly 3 values.")

    values = tuple(float(v) for v in color)
    if all(-1.0 <= v <= 1.0 for v in values):
        return tuple(int(round((v + 1.0) * 127.5)) for v in values)
    return tuple(int(round(v)) for v in values)
