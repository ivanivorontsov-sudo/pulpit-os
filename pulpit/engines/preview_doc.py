"""Самодостаточный HTML для встроенного просмотра.

TkinterWeb не обязан находить style.css и папку assets.
Поэтому в кадр уходит документ, где CSS уже внутри, а картинки — data URI.
"""

from __future__ import annotations

import base64
import re
from pathlib import Path

MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}


def standalone(html: str, css: str, asset_root: str | Path) -> str:
    root = Path(asset_root)
    styled = _inline_css(html, css)
    return _inline_images(styled, root)


def _inline_css(html: str, css: str) -> str:
    block = f"<style>\n{css}\n</style>"
    if 'href="style.css"' in html:
        return html.replace('<link rel="stylesheet" href="style.css">', block)
    if "</head>" in html:
        return html.replace("</head>", block + "\n</head>")
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'>{block}</head><body>{html}</body></html>"


def _inline_images(html: str, root: Path) -> str:
    def replace(match: re.Match[str]) -> str:
        src = match.group(1)
        if src.startswith("data:") or src.startswith("http"):
            return match.group(0)
        path = _find(root, src)
        if path is None:
            return match.group(0)
        mime = MIME.get(path.suffix.lower(), "application/octet-stream")
        payload = base64.b64encode(path.read_bytes()).decode("ascii")
        return f'src="data:{mime};base64,{payload}"'

    return re.sub(r'src="([^"]+)"', replace, html)


def _find(root: Path, src: str) -> Path | None:
    clean = src.split("?")[0].replace("\\", "/")
    candidates = [root / clean, root / "assets" / Path(clean).name, root / "images" / Path(clean).name]
    for path in candidates:
        if path.is_file():
            return path
    return None
