"""Картинки, которые реально пишутся на диск.

Pillow в собранном exe иногда забывает свои плагины. Импорт ниже
регистрирует их явно, иначе JPEG и WEBP «конвертируются» в никуда.
"""

from __future__ import annotations

import shutil
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps
from PIL import BmpImagePlugin, GifImagePlugin, JpegImagePlugin, PngImagePlugin, TiffImagePlugin

try:
    from PIL import WebPImagePlugin
except ImportError:  # pragma: no cover
    WebPImagePlugin = None  # type: ignore


Image.init()

IMAGE_FORMATS = {
    ".png": "PNG",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".webp": "WEBP",
    ".bmp": "BMP",
    ".gif": "GIF",
    ".tif": "TIFF",
    ".tiff": "TIFF",
}


def supported_suffixes() -> list[str]:
    ready = []
    for suffix, fmt in IMAGE_FORMATS.items():
        if fmt in Image.SAVE and fmt in Image.OPEN:
            ready.append(suffix)
    return ready


def sniff_format(path: str | Path) -> str:
    with Image.open(path) as image:
        image.load()
        return image.format or Path(path).suffix.lstrip(".").upper()


def convert_image(src: str | Path, dest: str | Path, quality: int = 90) -> Path:
    source = Path(src)
    target = ensure_suffix(Path(dest))
    if not source.is_file():
        raise FileNotFoundError(f"Нет файла: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    fmt = IMAGE_FORMATS[target.suffix.lower()]
    if fmt not in Image.SAVE:
        raise ValueError(f"Этот Python не умеет писать {fmt}. Доступно: {', '.join(sorted(Image.SAVE))}")
    with Image.open(source) as image:
        image.load()
        frame = _frame_for(image, fmt)
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
) -> Path:
    source = Path(src)
    target = ensure_suffix(Path(dest), fallback=source.suffix or ".png")
    target.parent.mkdir(parents=True, exist_ok=True)
    fmt = IMAGE_FORMATS[target.suffix.lower()]
    with Image.open(source) as image:
        image.load()
        frame = image.convert("RGBA")
        if rotate:
            frame = frame.rotate(-int(rotate), expand=True)
        if width or height:
            ratio_w = width or int(frame.width * ((height or frame.height) / frame.height))
            ratio_h = height or int(frame.height * ((width or frame.width) / frame.width))
            frame = frame.resize((max(1, ratio_w), max(1, ratio_h)), Image.Resampling.LANCZOS)
        if grayscale:
            frame = ImageOps.grayscale(frame).convert("RGBA")
        if brightness != 1.0:
            frame = ImageEnhance.Brightness(frame).enhance(brightness)
        payload = _encode(_frame_for(frame, fmt), fmt, quality)
    target.write_bytes(payload)
    if target.stat().st_size < 16:
        raise OSError(f"Файл не записался: {target}")
    return target


def store_image(src: str | Path, assets_dir: str | Path, stem: str) -> str:
    """Копирует картинку в папку проекта сразу, не оставляя её «где-то на диске»."""
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
    kwargs = {}
    if fmt in {"JPEG", "WEBP"}:
        kwargs["quality"] = max(1, min(95, int(quality)))
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
