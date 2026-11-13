"""Инструменты для данных и архивов: конвертация, проверка и безопасная распаковка."""

from __future__ import annotations

import csv
import json
import re
import xml.etree.ElementTree as ET
from io import StringIO
from pathlib import Path, PurePosixPath, PureWindowsPath
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from pulpit.engines.images import IMAGE_FORMATS, convert_image

__all__ = [
    "convert_image", "IMAGE_FORMATS", "json_to_csv", "csv_to_json",
    "json_format", "validate_json", "json_to_xml", "xml_to_json",
    "csv_to_tsv", "recode_text", "text_between", "pack_zip", "unpack_zip",
    "inspect_zip", "preview_table", "detect_delimiter",
]

MAX_ARCHIVE_FILES = 10000
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024


def json_format(text: str, indent: int | None = 2, sort_keys: bool = False) -> str:
    """Проверяет JSON и возвращает отформатированный или компактный результат."""
    data = json.loads(text)
    return json.dumps(data, ensure_ascii=False, indent=indent, sort_keys=sort_keys)


def validate_json(text: str) -> tuple[bool, str]:
    try:
        json.loads(text)
    except json.JSONDecodeError as exc:
        return False, f"{exc.msg} · строка {exc.lineno}, столбец {exc.colno}"
    except (TypeError, ValueError) as exc:
        return False, str(exc)
    return True, "JSON корректен"


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def json_to_csv(src: str | Path, dest: str | Path, delimiter: str = ",") -> Path:
    source, target = Path(src), Path(dest)
    data = json.loads(source.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise ValueError("JSON должен содержать объект или список объектов")
    fields = list(dict.fromkeys(key for row in data for key in row))
    if not fields:
        raise ValueError("В JSON нет полей для таблицы")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", delimiter=delimiter)
        writer.writeheader()
        for row in data:
            writer.writerow({key: _cell(value) for key, value in row.items()})
    return target


def detect_delimiter(text: str) -> str:
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        return "\t" if "\t" in sample else (";" if ";" in sample else ",")


def csv_to_json(src: str | Path, dest: str | Path, delimiter: str | None = None) -> Path:
    source, target = Path(src), Path(dest)
    raw = source.read_text(encoding="utf-8-sig")
    separator = delimiter or detect_delimiter(raw)
    reader = csv.DictReader(StringIO(raw), delimiter=separator)
    if not reader.fieldnames:
        raise ValueError("CSV пустой или в нём нет строки заголовков")
    rows = [{str(key): value for key, value in row.items() if key is not None} for row in reader]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def csv_to_tsv(src: str | Path, dest: str | Path, delimiter: str | None = None) -> Path:
    source, target = Path(src), Path(dest)
    text = source.read_text(encoding="utf-8-sig")
    reader = csv.reader(StringIO(text), delimiter=delimiter or detect_delimiter(text))
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle, delimiter="\t").writerows(reader)
    return target


def _xml_tag(value: object) -> str:
    raw = str(value)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", raw)
    if not safe or not re.match(r"[A-Za-z_]", safe):
        safe = "item_" + safe
    return safe


def _json_to_element(parent: ET.Element, value: object, name: str = "item") -> None:
    node = ET.SubElement(parent, _xml_tag(name))
    if isinstance(value, dict):
        for key, item in value.items():
            _json_to_element(node, item, str(key))
    elif isinstance(value, list):
        for item in value:
            _json_to_element(node, item, "item")
    elif value is not None:
        node.text = str(value).lower() if isinstance(value, bool) else str(value)


def json_to_xml(src: str | Path, dest: str | Path, root_name: str = "root") -> Path:
    data = json.loads(Path(src).read_text(encoding="utf-8-sig"))
    root = ET.Element(_xml_tag(root_name))
    if isinstance(data, dict):
        for key, value in data.items():
            _json_to_element(root, value, str(key))
    elif isinstance(data, list):
        for value in data:
            _json_to_element(root, value)
    else:
        root.text = _cell(data)
    ET.indent(root, space="  ")
    target = Path(dest)
    target.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(target, encoding="utf-8", xml_declaration=True)
    return target


def _element_to_value(node: ET.Element) -> object:
    children = list(node)
    attrs = {f"@{key}": value for key, value in node.attrib.items()}
    if not children:
        value: object = node.text or ""
        return {**attrs, "#text": value} if attrs else value
    result: dict[str, object] = dict(attrs)
    for child in children:
        value = _element_to_value(child)
        if child.tag in result:
            current = result[child.tag]
            if not isinstance(current, list):
                result[child.tag] = [current]
            result[child.tag].append(value)
        else:
            result[child.tag] = value
    if node.text and node.text.strip():
        result["#text"] = node.text.strip()
    return result


def xml_to_json(src: str | Path, dest: str | Path) -> Path:
    root = ET.parse(src).getroot()
    target = Path(dest)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({root.tag: _element_to_value(root)}, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def recode_text(src: str | Path, dest: str | Path, from_enc: str, to_enc: str) -> Path:
    source, target = Path(src), Path(dest)
    text = source.read_text(encoding=from_enc)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding=to_enc)
    return target


def text_between(text: str, from_enc: str, to_enc: str) -> str:
    return text.encode(from_enc, errors="replace").decode(to_enc, errors="replace")


def pack_zip(folder: str | Path, dest: str | Path, compression: int = 6) -> Path:
    root, target = Path(folder).resolve(), Path(dest).resolve()
    if not root.is_dir():
        raise ValueError("Для ZIP нужна существующая папка")
    if target == root or root in target.parents:
        raise ValueError("Нельзя создавать архив внутри архивируемой папки")
    target.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(target, "w", ZIP_DEFLATED, compresslevel=max(0, min(9, int(compression)))) as archive:
        for path in root.rglob("*"):
            if path.is_file() and not path.is_symlink() and path.resolve() != target:
                archive.write(path, path.relative_to(root).as_posix())
    return target


def _safe_member_name(name: str) -> PurePosixPath:
    normalized = name.replace("\\", "/")
    posix, windows = PurePosixPath(normalized), PureWindowsPath(name)
    if not normalized or posix.is_absolute() or windows.is_absolute() or windows.drive:
        raise ValueError(f"Небезопасный путь в ZIP: {name}")
    if any(part in {"", ".", ".."} for part in posix.parts):
        raise ValueError(f"Небезопасный путь в ZIP: {name}")
    return posix


def inspect_zip(src: str | Path) -> dict[str, object]:
    with ZipFile(src) as archive:
        infos = archive.infolist()
        files = [item for item in infos if not item.is_dir()]
        return {
            "files": len(files),
            "folders": len(infos) - len(files),
            "uncompressed_bytes": sum(item.file_size for item in files),
            "compressed_bytes": sum(item.compress_size for item in files),
            "names": [item.filename for item in infos[:100]],
        }


def unpack_zip(
    src: str | Path,
    dest: str | Path,
    max_files: int = MAX_ARCHIVE_FILES,
    max_bytes: int = MAX_ARCHIVE_BYTES,
) -> Path:
    """Извлекает ZIP после проверки путей, симлинков и предельного размера."""
    target = Path(dest).resolve()
    target.mkdir(parents=True, exist_ok=True)
    try:
        with ZipFile(src) as archive:
            infos = archive.infolist()
            files = [item for item in infos if not item.is_dir()]
            if len(files) > max_files:
                raise ValueError(f"Слишком много файлов в архиве: {len(files)}")
            total = sum(item.file_size for item in files)
            if total > max_bytes:
                raise ValueError(f"Распакованный архив слишком велик: {total} байт")
            checked: list[tuple[object, Path]] = []
            for item in infos:
                relative = _safe_member_name(item.filename)
                mode = (item.external_attr >> 16) & 0xFFFF
                if mode & 0o170000 == 0o120000:
                    raise ValueError(f"Символические ссылки в ZIP запрещены: {item.filename}")
                output = (target / Path(*relative.parts)).resolve()
                if output != target and target not in output.parents:
                    raise ValueError(f"Выход за пределы папки распаковки: {item.filename}")
                if item.file_size > 0 and item.compress_size == 0:
                    raise ValueError(f"Подозрительная запись в ZIP: {item.filename}")
                if item.compress_size and item.file_size / item.compress_size > 1000:
                    raise ValueError(f"Слишком высокая степень сжатия: {item.filename}")
                checked.append((item, output))
            for item, output in checked:
                if item.is_dir():
                    output.mkdir(parents=True, exist_ok=True)
                    continue
                output.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(item, "r") as source, output.open("wb") as destination:
                    while chunk := source.read(1024 * 1024):
                        destination.write(chunk)
    except BadZipFile as exc:
        raise ValueError("Файл повреждён или не является ZIP-архивом") from exc
    return target


def preview_table(text: str, kind: str) -> str:
    if kind.lower() == "json":
        return json_format(text)
    rows = list(csv.reader(StringIO(text), delimiter=detect_delimiter(text)))
    if not rows:
        return "Таблица пуста"
    return "\n".join(" | ".join(row) for row in rows[:500])
