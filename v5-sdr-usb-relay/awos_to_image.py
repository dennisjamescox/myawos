#!/usr/bin/env python3
"""Render the current MyAWOS text product to a PNG atomically."""

from __future__ import annotations

import argparse
import os
import tempfile
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def wrap_advisory(text: str, width: int) -> str:
    wrapped: list[str] = []
    for line in text.splitlines():
        wrapped.extend(textwrap.wrap(line, width=width, break_long_words=False) or [""])
    return "\n".join(wrapped)


def render(
    input_path: Path,
    output_path: Path,
    font_path: Path,
    font_size: int = 20,
    wrap_width: int = 62,
) -> None:
    text = wrap_advisory(input_path.read_text(encoding="utf-8"), wrap_width)
    try:
        font = ImageFont.truetype(str(font_path), font_size)
    except OSError:
        font = ImageFont.load_default()

    probe = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(probe)
    spacing = 4
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing)
    width = max(1, bbox[2] - bbox[0]) + 20
    height = max(1, bbox[3] - bbox[1]) + 20

    image = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(image)
    draw.multiline_text((10, 10), text, font=font, fill="black", spacing=spacing, align="left")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{output_path.stem}.", suffix=".png", dir=output_path.parent)
    os.close(fd)
    try:
        image.save(temp_name, format="PNG")
        os.replace(temp_name, output_path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("/home/user/weather_station/current_sms.txt"))
    parser.add_argument("--output", type=Path, default=Path("/home/user/weather_camera/rwj_awos.png"))
    parser.add_argument("--font", type=Path, default=Path("/usr/share/fonts/truetype/freefont/FreeMono.ttf"))
    parser.add_argument("--wrap-width", type=int, default=62)
    args = parser.parse_args()
    render(args.input, args.output, args.font, wrap_width=args.wrap_width)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
