"""Текстовые инструменты и безопасный Markdown."""

from __future__ import annotations

import difflib
import html
import re
from pathlib import Path
from urllib.parse import urlsplit

from pulpit.engines.images import edit_image as _edit_image

from pulpit.engines.images import edit_image


def text_stats(text: str) -> dict[str, int]:
    words = re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE)
    paragraphs = [item for item in re.split(r"\n\s*\n", text.strip()) if item.strip()]
    sentences = len(re.findall(r"[.!?…]+(?:\s|$)", text))
    return {
        "symbols": len(text),
        "symbols_no_space": len(re.sub(r"\s+", "", text)),
        "words": len(words),
        "lines": text.count("\n") + (1 if text else 0),
        "paragraphs": len(paragraphs),
        "sentences": sentences,
        "reading_minutes": max(1, round(len(words) / 180)) if words else 0,
    }


def transform_text(text: str, mode: str) -> str:
    if mode == "upper":
        return text.upper()
    if mode == "lower":
        return text.lower()
    if mode == "title":
        return text.title()
    if mode == "sentence":
        return text[:1].upper() + text[1:].lower()
    if mode == "trim":
        return "\n".join(line.strip() for line in text.splitlines())
    if mode == "remove_blank":
        return "\n".join(line for line in text.splitlines() if line.strip())
    if mode == "collapse_spaces":
        return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines())
    if mode == "normalize_newlines":
        return text.replace("\r\n", "\n").replace("\r", "\n")
    if mode == "sort_lines":
        return "\n".join(sorted(text.splitlines(), key=str.casefold))
    if mode == "unique_lines":
        return "\n".join(dict.fromkeys(text.splitlines()))
    raise ValueError(f"Неизвестная операция: {mode}")


def find_replace(text: str, needle: str, replacement: str, regex: bool = False, ignore_case: bool = False) -> tuple[str, int]:
    if not needle:
        raise ValueError("Введите текст для поиска")
    flags = re.IGNORECASE if ignore_case else 0
    if regex:
        try:
            return re.subn(needle, replacement, text, flags=flags)
        except re.error as exc:
            raise ValueError(f"Ошибка регулярного выражения: {exc}") from exc
    if ignore_case:
        pattern = re.compile(re.escape(needle), flags)
        return pattern.subn(lambda _match: replacement, text)
    return text.replace(needle, replacement), text.count(needle)


def compare_text(before: str, after: str, from_name: str = "Было", to_name: str = "Стало") -> str:
    return "".join(difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=from_name,
        tofile=to_name,
    ))


def _safe_link(url: str) -> bool:
    parts = urlsplit(url.strip())
    if parts.scheme:
        return parts.scheme.lower() in {"http", "https", "mailto"}
    return not url.strip().startswith("//") and not url.strip().lower().startswith(("javascript:", "data:", "vbscript:"))


def _inline(text: str) -> str:
    safe = html.escape(text, quote=False)
    safe = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", lambda m: f'<span class="md-image">[Изображение: {m.group(1)}]</span>', safe)
    def link(match: re.Match[str]) -> str:
        label, href = match.group(1), html.unescape(match.group(2)).strip()
        if not _safe_link(href):
            return label
        return f'<a href="{html.escape(href, quote=True)}" rel="noopener noreferrer">{label}</a>'
    safe = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, safe)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
    safe = re.sub(r"__(.+?)__", r"<strong>\1</strong>", safe)
    safe = re.sub(r"~~(.+?)~~", r"<del>\1</del>", safe)
    safe = re.sub(r"\*(.+?)\*", r"<em>\1</em>", safe)
    safe = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<em>\1</em>", safe)
    safe = re.sub(r"\x60([^\x60]+)\x60", r"<code>\1</code>", safe)
    return safe


def markdown_to_html(text: str) -> str:
    """Преобразует распространённый Markdown в автономный HTML без сырого HTML."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    output: list[str] = []
    paragraph: list[str] = []
    list_kind: str | None = None
    in_code = False
    code_lines: list[str] = []

    def close_list() -> None:
        nonlocal list_kind
        if list_kind:
            output.append(f"</{list_kind}>")
            list_kind = None

    def flush_paragraph() -> None:
        if paragraph:
            output.append("<p>" + "<br>\n".join(_inline(line) for line in paragraph) + "</p>")
            paragraph.clear()

    for line in lines:
        stripped = line.strip()
        if stripped.startswith(chr(96) * 3) or stripped.startswith("~~~"):
            flush_paragraph()
            close_list()
            if in_code:
                output.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines.clear()
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            output.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
            continue
        if re.match(r"^([-*_])(?:\s*\1){2,}$", stripped):
            flush_paragraph()
            close_list()
            output.append("<hr>")
            continue
        quote = re.match(r"^>\s?(.*)$", stripped)
        if quote:
            flush_paragraph()
            close_list()
            output.append("<blockquote><p>" + _inline(quote.group(1)) + "</p></blockquote>")
            continue
        bullet = re.match(r"^\s*[-+*]\s+(.+)$", line)
        numbered = re.match(r"^\s*\d+[.)]\s+(.+)$", line)
        if bullet or numbered:
            flush_paragraph()
            kind = "ul" if bullet else "ol"
            if list_kind != kind:
                close_list()
                output.append(f"<{kind}>")
                list_kind = kind
            output.append("<li>" + _inline((bullet or numbered).group(1)) + "</li>")
            continue
        close_list()
        if stripped:
            paragraph.append(line)
        else:
            flush_paragraph()
    flush_paragraph()
    close_list()
    if in_code:
        output.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    body = "\n".join(output)
    return """<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Предпросмотр Markdown</title>
<style>
:root{color-scheme:light dark}body{font:16px/1.7 system-ui,sans-serif;max-width:900px;margin:40px auto;padding:0 22px}
h1,h2,h3,h4,h5,h6{line-height:1.25;margin:1.5em 0 .55em}p{margin:.7em 0}
pre,code{font-family:Consolas,monospace;background:rgba(127,127,127,.16);border-radius:6px}
pre{padding:16px;overflow:auto}code{padding:2px 5px}blockquote{border-left:4px solid #c45c26;padding-left:16px;margin-left:0;opacity:.85}
a{color:#dc804c}li{margin:.25em 0}hr{border:0;border-top:1px solid #8885}
</style></head><body>""" + body + "</body></html>"


def save_text(path: str | Path, text: str, encoding: str = "utf-8") -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding=encoding)
    return target


def edit_image(src: str | Path, dest: str | Path, **options) -> Path:
    """Совместимый адаптер к движку изображений для старых интеграций."""
    return _edit_image(src, dest, **options)
