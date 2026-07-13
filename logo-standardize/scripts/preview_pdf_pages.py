#!/usr/bin/env python3
"""Render a compact, low-resolution PDF page contact sheet for fast page selection."""

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw


POPPLER_FALLBACK = Path(
    "/Users/bytedance/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/pdftoppm"
)


def find_pdftoppm() -> str:
    command = shutil.which("pdftoppm")
    if command:
        return command
    if POPPLER_FALLBACK.is_file():
        return str(POPPLER_FALLBACK)
    raise RuntimeError("PDF preview needs Poppler (pdftoppm), but it is unavailable")


def page_sort_key(path: Path):
    try:
        return int(path.stem.rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return path.name


def make_preview(source: Path, output: Path, dpi: int, columns: int):
    with tempfile.TemporaryDirectory(prefix="logo-preview-") as tmp:
        prefix = Path(tmp) / "page"
        subprocess.run(
            [find_pdftoppm(), "-r", str(dpi), "-png", str(source), str(prefix)],
            check=True,
            capture_output=True,
            text=True,
        )
        pages = sorted(Path(tmp).glob("page-*.png"), key=page_sort_key)
        if not pages:
            raise RuntimeError("No PDF pages were rendered")

        thumb_w, thumb_h, label_h, gap = 420, 300, 34, 24
        rows = (len(pages) + columns - 1) // columns
        canvas = Image.new("RGB", (gap + columns * (thumb_w + gap), gap + rows * (thumb_h + label_h + gap)), "#f4f5f7")
        draw = ImageDraw.Draw(canvas)
        for index, page in enumerate(pages):
            image = Image.open(page).convert("RGB")
            image.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            col, row = index % columns, index // columns
            x = gap + col * (thumb_w + gap) + (thumb_w - image.width) // 2
            y = gap + row * (thumb_h + label_h + gap) + (thumb_h - image.height) // 2
            canvas.paste(image, (x, y))
            draw.text((gap + col * (thumb_w + gap), y + thumb_h + 6), f"Page {index + 1}", fill="#1f2329")
        output.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output, "PNG", optimize=True)
        print(output)
        print("page_count", len(pages))
        print("dpi", dpi)


def main():
    parser = argparse.ArgumentParser(description="Create a low-resolution PDF page contact sheet.")
    parser.add_argument("input_file", type=Path)
    parser.add_argument("output_file", type=Path)
    parser.add_argument("--dpi", type=int, default=72)
    parser.add_argument("--columns", type=int, default=2)
    args = parser.parse_args()
    if args.dpi <= 0 or args.columns <= 0:
        parser.error("--dpi and --columns must be positive")
    make_preview(args.input_file, args.output_file, args.dpi, args.columns)


if __name__ == "__main__":
    main()
