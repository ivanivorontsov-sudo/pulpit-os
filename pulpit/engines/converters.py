"""Конвертеры, которых в проводнике нет из коробки."""

from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image


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


def convert_image(src: str | Path, dest: str | Path, quality: int = 90) -> Path:
    source = Path(src)
    target = Path(dest)
    target.parent.mkdir(parents=True, exist_ok=True)
    fmt = IMAGE_FORMATS.get(target.suffix.lower())
    if not fmt:
        raise ValueError(f"Неизвестный формат картинки: {target.suffix}")
    with Image.open(source) as image:
        frame = image.convert("RGB") if fmt in {"JPEG", "BMP"} else image
        save_kwargs = {"quality": quality} if fmt in {"JPEG", "WEBP"} else {}
        frame.save(target, format=fmt, **save_kwargs)
    return target


def json_to_csv(src: str | Path, dest: str | Path) -> Path:
    source = Path(src)
    target = Path(dest)
    data = json.loads(source.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        raise ValueError("JSON должен быть объектом или списком объектов")
    fields = list(dict.fromkeys(key for row in data for key in row))
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)
    return target


def csv_to_json(src: str | Path, dest: str | Path) -> Path:
    source = Path(src)
    target = Path(dest)
    with source.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def recode_text(src: str | Path, dest: str | Path, from_enc: str, to_enc: str) -> Path:
    source = Path(src)
    target = Path(dest)
    text = source.read_text(encoding=from_enc)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding=to_enc)
    return target


def text_between(text: str, from_enc: str, to_enc: str) -> str:
    return text.encode(from_enc, errors="replace").decode(to_enc, errors="replace")


def pack_zip(folder: str | Path, dest: str | Path) -> Path:
    root = Path(folder)
    target = Path(dest)
    if not root.is_dir():
        raise ValueError("Для zip нужна папка")
    target.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        for path in root.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(root).as_posix())
    return target


def unpack_zip(src: str | Path, dest: str | Path) -> Path:
    target = Path(dest)
    target.mkdir(parents=True, exist_ok=True)
    with ZipFile(src) as archive:
        archive.extractall(target)
    return target


def preview_table(text: str, kind: str) -> str:
    if kind == "json":
        data = json.loads(text)
        return json.dumps(data, ensure_ascii=False, indent=2)
    reader = csv.reader(StringIO(text))
    return "\n".join(" | ".join(row) for row in reader)
