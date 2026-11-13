"""Обработка растровых изображений на базе Pillow."""

from __future__ import annotations

import shutil
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps
from PIL import BmpImagePlugin, GifImagePlugin, JpegImagePlugin, PngImagePlugin, TiffImagePlugin

try:
    from PIL import WebPImagePlugin
except ImportError:  # pragma: no cover
    WebPImagePlugin = None  # type: ignore

Image.init()

IMAGE_FORMATS = {
    ".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP",
    ".bmp": "BMP", ".gif": "GIF", ".tif": "TIFF", ".tiff": "TIFF",
}


def supported_suffixes() -> list[str]:
    return [suffix for suffix, fmt in IMAGE_FORMATS.items() if fmt in Image.SAVE and fmt in Image.OPEN]


def sniff_format(path: str | Path) -> str:
    with Image.open(path) as image:
        image.load()
        return image.format or Path(path).suffix.lstrip(".").upper()


def image_info(path: str | Path) -> dict[str, object]:
    source = Path(path)
    with Image.open(source) as image:
        return {
            "name": source.name,
            "format": image.format or source.suffix.lstrip(".").upper(),
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "frames": getattr(image, "n_frames", 1),
            "animated": bool(getattr(image, "is_animated", False)),
            "bytes": source.stat().st_size,
            "megapixels": round(image.width * image.height / 1_000_000, 2),
        }


def convert_image(src: str | Path, dest: str | Path, quality: int = 90) -> Path:
    source, target = Path(src), ensure_suffix(Path(dest))
    if not source.is_file():
        raise FileNotFoundError(f"Нет файла: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    fmt = IMAGE_FORMATS[target.suffix.lower()]
    if fmt not in Image.SAVE:
        raise ValueError(f"Этот Python не умеет писать {fmt}. Доступно: {', '.join(sorted(Image.SAVE))}")
    with Image.open(source) as image:
        image.seek(0)
        image.load()
        frame = _frame_for(ImageOps.exif_transpose(image), fmt)
        payload = _encode(frame, fmt, quality)
    target.write_bytes(payload)
    if not target.is_file() or target.stat().st_size < 16:
        raise OSError(f"Файл не записался: {target}")
    return target


def edit_image(
    src: str | Path,
    dest: str | Path,
    width: int | None = None,
    height: int | None = None,
    rotate: int = 0,
    grayscale: bool = False,
    brightness: float = 1.0,
    quality: int = 90,
    fit: str = "contain",
    flip_horizontal: bool = False,
    flip_vertical: bool = False,
    crop: tuple[int, int, int, int] | None = None,
    watermark: str = "",
    watermark_opacity: int = 125,
) -> Path:
    source = Path(src)
    if not source.is_file():
        raise FileNotFoundError(source)
    target = ensure_suffix(Path(dest), fallback=source.suffix or ".png")
    target.parent.mkdir(parents=True, exist_ok=True)
    fmt = IMAGE_FORMATS[target.suffix.lower()]
    with Image.open(source) as original:
        original.seek(0)
        original.load()
        frame = ImageOps.exif_transpose(original).convert("RGBA")
        if crop:
            left, top, right, bottom = (int(value) for value in crop)
            if right <= left or bottom <= top or left < 0 or top < 0 or right > frame.width or bottom > frame.height:
                raise ValueError("Область обрезки выходит за границы изображения")
            frame = frame.crop((left, top, right, bottom))
        if flip_horizontal:
            frame = ImageOps.mirror(frame)
        if flip_vertical:
            frame = ImageOps.flip(frame)
        if rotate:
            frame = frame.rotate(-int(rotate) % 360, expand=True, resample=Image.Resampling.BICUBIC)
        if width or height:
            target_w = max(1, int(width or round(frame.width * (height / frame.height))))
            target_h = max(1, int(height or round(frame.height * (width / frame.width))))
            if fit == "stretch":
                frame = frame.resize((target_w, target_h), Image.Resampling.LANCZOS)
            elif fit == "cover":
                frame = ImageOps.fit(frame, (target_w, target_h), method=Image.Resampling.LANCZOS)
            elif fit == "contain":
                frame.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
            else:
                raise ValueError("Режим размера: contain, cover или stretch")
        if grayscale:
            alpha = frame.getchannel("A")
            gray = ImageOps.grayscale(frame.convert("RGB")).convert("RGBA")
            gray.putalpha(alpha)
            frame = gray
        if brightness <= 0 or brightness > 3:
            raise ValueError("Яркость должна быть больше 0 и не больше 3")
        if brightness != 1.0:
            frame = ImageEnhance.Brightness(frame).enhance(float(brightness))
        if watermark.strip():
            overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            font_size = max(12, frame.width // 32)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except OSError:
                font = ImageFont.load_default()
            text = watermark.strip()
            box = draw.textbbox((0, 0), text, font=font, stroke_width=1)
            pad = max(8, frame.width // 80)
            x = max(pad, frame.width - (box[2] - box[0]) - pad)
            y = max(pad, frame.height - (box[3] - box[1]) - pad)
            opacity = max(0, min(255, int(watermark_opacity)))
            draw.text((x, y), text, font=font, fill=(255, 255, 255, opacity), stroke_width=1, stroke_fill=(0, 0, 0, opacity))
            frame = Image.alpha_composite(frame, overlay)
        payload = _encode(_frame_for(frame, fmt), fmt, quality)
    target.write_bytes(payload)
    if target.stat().st_size < 16:
        raise OSError(f"Файл не записался: {target}")
    return target


def make_thumbnail(src: str | Path, dest: str | Path, size: tuple[int, int] = (320, 240), quality: int = 85) -> Path:
    source, target = Path(src), ensure_suffix(Path(dest), ".jpg")
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image.seek(0)
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail(size, Image.Resampling.LANCZOS)
        image.save(target, format="JPEG", quality=max(1, min(95, int(quality))), optimize=True)
    return target


def create_contact_sheet(
    sources: list[str | Path],
    dest: str | Path,
    thumb_size: tuple[int, int] = (220, 160),
    columns: int = 4,
    gap: int = 16,
    background: str = "#202020",
) -> Path:
    if not sources:
        raise ValueError("Добавьте хотя бы одно изображение")
    columns = max(1, int(columns))
    rows = (len(sources) + columns - 1) // columns
    cell_w, cell_h = thumb_size[0], thumb_size[1] + 34
    sheet = Image.new("RGB", (columns * cell_w + (columns + 1) * gap, rows * cell_h + (rows + 1) * gap), background)
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, source in enumerate(sources):
        with Image.open(source) as image:
            image.seek(0)
            thumb = ImageOps.contain(ImageOps.exif_transpose(image).convert("RGB"), thumb_size, Image.Resampling.LANCZOS)
        col, row = index % columns, index // columns
        x = gap + col * (cell_w + gap) + (cell_w - thumb.width) // 2
        y = gap + row * (cell_h + gap)
        sheet.paste(thumb, (x, y))
        draw.text((gap + col * (cell_w + gap), y + thumb_size[1] + 8), Path(source).name[:34], fill="white", font=font)
    target = Path(dest)
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target, format="PNG", optimize=True)
    return target


def store_image(src: str | Path, assets_dir: str | Path, stem: str) -> str:
    source = Path(src)
    if not source.is_file():
        raise FileNotFoundError(source)
    folder = Path(assets_dir)
    folder.mkdir(parents=True, exist_ok=True)
    suffix = source.suffix.lower() if source.suffix.lower() in IMAGE_FORMATS else ".png"
    name = f"{_slug(stem)}{suffix}"
    target = folder / name
    index = 2
    while target.exists():
        target = folder / f"{_slug(stem)}-{index}{suffix}"
        index += 1
    if suffix == source.suffix.lower():
        shutil.copy2(source, target)
    else:
        convert_image(source, target)
    if target.stat().st_size < 16:
        raise OSError(f"Копия пустая: {target}")
    return target.name


def ensure_suffix(path: Path, fallback: str = ".png") -> Path:
    suffix = path.suffix.lower()
    if suffix in IMAGE_FORMATS:
        return path
    return path.with_suffix(fallback if fallback in IMAGE_FORMATS else ".png")


def _encode(frame: Image.Image, fmt: str, quality: int) -> bytes:
    buffer = BytesIO()
    kwargs: dict[str, object] = {}
    if fmt in {"JPEG", "WEBP"}:
        kwargs["quality"] = max(1, min(95, int(quality)))
    if fmt in {"JPEG", "PNG", "WEBP"}:
        kwargs["optimize"] = True
    if fmt == "WEBP":
        kwargs["method"] = 4
    frame.save(buffer, format=fmt, **kwargs)
    payload = buffer.getvalue()
    if len(payload) < 16:
        raise OSError(f"Кодировщик {fmt} вернул пустоту")
    return payload


def _frame_for(image: Image.Image, fmt: str) -> Image.Image:
    if fmt in {"JPEG", "BMP"}:
        if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
            rgba = image.convert("RGBA")
            background = Image.new("RGB", rgba.size, (255, 255, 255))
            background.paste(rgba, mask=rgba.getchannel("A"))
            return background
        return image.convert("RGB")
    if fmt == "GIF":
        return image.convert("P", palette=Image.Palette.ADAPTIVE)
    if fmt == "PNG":
        return image if image.mode in {"RGB", "RGBA", "L", "P"} else image.convert("RGBA")
    if image.mode == "P":
        return image.convert("RGBA")
    return image


def _slug(stem: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in stem.strip())
    return cleaned.strip("-") or "image"
