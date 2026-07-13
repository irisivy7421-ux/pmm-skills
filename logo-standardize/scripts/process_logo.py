import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, PngImagePlugin

try:
    import fitz
except ImportError:
    fitz = None

RASTER_EXTENSIONS = {".png", ".jpg", ".jpeg"}
POPPLER_FALLBACK = Path(
    "/Users/bytedance/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/pdftoppm"
)


def find_pdftoppm() -> str:
    command = shutil.which("pdftoppm")
    if command:
        return command
    if POPPLER_FALLBACK.is_file():
        return str(POPPLER_FALLBACK)
    raise RuntimeError("PDF rendering needs PyMuPDF or Poppler (pdftoppm), but neither is available")


def load_logo_image(path: Path, zoom: int = 6, page_number: int = 1) -> tuple[Image.Image, str]:
    if path.suffix.lower() in RASTER_EXTENSIONS:
        return Image.open(path).convert("RGBA"), "raster"

    if fitz is not None:
        doc = fitz.open(str(path))
        if not 1 <= page_number <= len(doc):
            doc.close()
            raise ValueError(f"--page must be between 1 and {len(doc)}")
        page = doc[page_number - 1]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=True, annots=False)
        img = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
        doc.close()
        return img, "PyMuPDF"

    with tempfile.TemporaryDirectory(prefix="logo-standardize-") as tmp:
        rendered = Path(tmp) / "selected-page"
        subprocess.run(
            [
                find_pdftoppm(), "-f", str(page_number), "-l", str(page_number),
                "-singlefile", "-r", str(max(300, round(72 * zoom))), "-png",
                str(path), str(rendered),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        image_path = rendered.with_suffix(".png")
        if not image_path.is_file():
            raise RuntimeError("Poppler did not render the requested PDF page")
        return Image.open(image_path).convert("RGBA"), "Poppler"


def parse_crop(value: str) -> tuple[float, float, float, float]:
    try:
        x, y, w, h = (float(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--crop must be x,y,width,height") from exc
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > 1 or y + h > 1:
        raise argparse.ArgumentTypeError("--crop values must fit within the normalized 0–1 image bounds")
    return x, y, w, h


def crop_normalized(img: Image.Image, crop: tuple[float, float, float, float]) -> Image.Image:
    x, y, w, h = crop
    iw, ih = img.size
    box = (round(x * iw), round(y * ih), round((x + w) * iw), round((y + h) * ih))
    return img.crop(box)


def content_bbox(img: Image.Image):
    rgba = img.convert("RGBA")
    white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    comp = Image.alpha_composite(white, rgba)
    r, g, b, _ = comp.split()
    ink_mask = Image.eval(
        ImageChops.darker(ImageChops.darker(r, g), b),
        lambda p: 255 if p < 248 else 0,
    )
    alpha_mask = Image.eval(rgba.getchannel("A"), lambda p: 255 if p > 10 else 0)
    mask = ImageChops.lighter(ink_mask, alpha_mask)
    return mask.getbbox()


def scale_logo(logo: Image.Image, safe_w: int, safe_h: int, force_square: bool = False):
    lw, lh = logo.size
    ratio = lw / lh

    if force_square or ratio < 1.25:
        scale = safe_h / lh
        shape = "square-forced" if force_square and ratio >= 1.25 else "square"
    elif ratio > 4.0:
        scale = safe_w / lw
        shape = "long"
    else:
        scale = 400 / lh
        if lw * scale > safe_w:
            scale = safe_w / lw
        if lh * scale > safe_h:
            scale = safe_h / lh
        shape = "normal"

    nw, nh = max(1, round(lw * scale)), max(1, round(lh * scale))
    return logo.resize((nw, nh), Image.Resampling.LANCZOS), ratio, shape


def apply_round_mask(canvas: Image.Image, radius: int) -> Image.Image:
    w, h = canvas.size
    mask = Image.new("L", (w, h), 0)
    drawer = ImageDraw.Draw(mask)
    drawer.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    canvas.putalpha(mask)
    return canvas


def save_with_padding(canvas: Image.Image, out: Path, min_size: int, max_size: int):
    def _save_image(img: Image.Image, pad_len: int = 0):
        meta = PngImagePlugin.PngInfo()
        if pad_len > 0:
            meta.add_text("padding", "0" * pad_len)
        img.save(out, "PNG", optimize=True, compress_level=9, pnginfo=meta)

    def _save(pad_len: int = 0):
        _save_image(canvas, pad_len=pad_len)

    _save(0)
    size = out.stat().st_size
    if size > max_size:
        # Large, detailed logos can exceed the target after square-rule upscaling.
        # Palette quantization keeps the flat brand colors and alpha mask while reducing PNG size.
        reduced = canvas.quantize(colors=64, method=Image.Quantize.FASTOCTREE)
        _save_image(reduced, pad_len=0)
        size = out.stat().st_size
        if min_size <= size <= max_size:
            return size
        if size < min_size:
            canvas_to_pad = reduced
        else:
            return size
    else:
        canvas_to_pad = canvas

    if size >= min_size:
        return size

    pad = min_size - size + 512
    for _ in range(5):
        _save_image(canvas_to_pad, pad_len=pad)
        size = out.stat().st_size
        if min_size <= size <= max_size:
            return size
        if size < min_size:
            pad += min_size - size + 256
        else:
            pad = max(0, pad - (size - max_size + 256))
    return out.stat().st_size


def process_logo(src: Path, out: Path, zoom: int, page_number: int, crop: tuple[float, float, float, float] | None, canvas_w: int, canvas_h: int, safe_w: int, safe_h: int, radius: int, force_square: bool = False):
    logo, renderer = load_logo_image(src, zoom=zoom, page_number=page_number)
    if crop:
        logo = crop_normalized(logo, crop)
    bbox = content_bbox(logo)
    if not bbox:
        raise RuntimeError("No logo content detected")
    logo = logo.crop(bbox)
    bbox2 = content_bbox(logo)
    if bbox2:
        logo = logo.crop(bbox2)

    cropped_size = logo.size
    logo_resized, ratio, shape = scale_logo(logo, safe_w=safe_w, safe_h=safe_h, force_square=force_square)
    nw, nh = logo_resized.size

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 255))
    x = (canvas_w - nw) // 2
    y = (canvas_h - nh) // 2
    canvas.alpha_composite(logo_resized, (x, y))
    canvas = apply_round_mask(canvas, radius=radius)

    size = save_with_padding(canvas, out, min_size=90 * 1024, max_size=140 * 1024)

    extrema = canvas.getchannel("A").getextrema()
    print(out)
    print("renderer", renderer)
    print("page", page_number)
    print("crop", crop)
    print("size_bytes", size)
    print("cropped_size", cropped_size)
    print("ratio", ratio)
    print("shape", shape)
    print("final_size", (nw, nh))
    print("position", (x, y))
    print("alpha_extrema", extrema)


def main():
    parser = argparse.ArgumentParser(description="Standardize a logo into a white rounded PNG.")
    parser.add_argument("input_file", type=Path)
    parser.add_argument("output_file", type=Path)
    parser.add_argument("--zoom", type=int, default=6)
    parser.add_argument("--page", type=int, default=1, help="1-based PDF page number; ignored for raster input")
    parser.add_argument("--crop", type=parse_crop, help="Normalized crop: x,y,width,height (each relative to 0–1)")
    parser.add_argument("--canvas-width", type=int, default=2000)
    parser.add_argument("--canvas-height", type=int, default=1000)
    parser.add_argument("--safe-width", type=int, default=1600)
    parser.add_argument("--safe-height", type=int, default=680)
    parser.add_argument("--radius", type=int, default=100)
    parser.add_argument(
        "--force-square",
        action="store_true",
        help="Use square scaling (height=safe-height) even when the cropped ratio is in the normal range.",
    )
    args = parser.parse_args()

    process_logo(
        src=args.input_file,
        out=args.output_file,
        zoom=args.zoom,
        page_number=args.page,
        crop=args.crop,
        canvas_w=args.canvas_width,
        canvas_h=args.canvas_height,
        safe_w=args.safe_width,
        safe_h=args.safe_height,
        radius=args.radius,
        force_square=args.force_square,
    )


if __name__ == "__main__":
    main()
