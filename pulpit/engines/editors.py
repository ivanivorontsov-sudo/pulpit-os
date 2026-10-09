"""Редакторы: текст, markdown и картинки без фотошопа на 4 гигабайта."""

from __future__ import annotations

import re
from pathlib import Path

from pulpit.engines.images import edit_image


def text_stats(text: str) -> dict[str, int]:
    words = re.findall(r"\w+", text, flags=re.UNICODE)
    return {
        "symbols": len(text),
        "symbols_no_space": len(re.sub(r"\s+", "", text)),
        "words": len(words),
        "lines": text.count("\n") + (1 if text else 0),
    }


def markdown_to_html(text: str) -> str:
    lines = text.splitlines()
    html: list[str] = []
    in_list = False
    for raw in lines:
        line = raw.rstrip()
        if line.startswith("### "):
            html.append(f"<h3>{_inline(line[4:])}</h3>")
        elif line.startswith("## "):
            html.append(f"<h2>{_inline(line[3:])}</h2>")
        elif line.startswith("# "):
            html.append(f"<h1>{_inline(line[2:])}</h1>")
        elif line.startswith("- "):
            if not in_list:
                html.append("<ul>")
                in_list = True
            html.append(f"<li>{_inline(line[2:])}</li>")
        else:
            if in_list:
                html.append("</ul>")
                in_list = False
            if line.strip():
                html.append(f"<p>{_inline(line)}</p>")
    if in_list:
        html.append("</ul>")
    return "\n".join(html)


def _inline(text: str) -> str:
    safe = text.replace("&", "&").replace("<", "<").replace(">", ">")
    safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
    safe = re.sub(r"\*(.+?)\*", r"<em>\1</em>", safe)
    safe = re.sub(r"`(.+?)`", r"<code>\1</code>", safe)
    return safe
