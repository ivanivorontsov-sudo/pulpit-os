"""Сборщик локального сайта. На выходе папка и zip: интернет не требуется."""

from __future__ import annotations

import html
import shutil
from pathlib import Path

from pulpit.engines.converters import pack_zip


def build_site(
    dest_dir: str | Path,
    title: str,
    tagline: str,
    accent: str,
    pages: list[dict[str, str]],
    image_paths: list[str] | None = None,
) -> dict[str, str]:
    root = Path(dest_dir)
    if root.exists():
        shutil.rmtree(root)
    images = root / "images"
    images.mkdir(parents=True)
    copied: list[str] = []
    for raw in image_paths or []:
        source = Path(raw)
        if source.is_file():
            target_name = _safe_name(source.name)
            shutil.copy2(source, images / target_name)
            copied.append(target_name)

    safe_pages = pages or [{"title": "Главная", "body": "Пустая страница, но уже локальная."}]
    nav = "\n".join(
        f'<a href="page-{index}.html">{html.escape(page.get("title") or f"Страница {index}")}</a>'
        for index, page in enumerate(safe_pages)
    )
    gallery = "\n".join(
        f'<figure><img src="images/{html.escape(name)}" alt="{html.escape(name)}"></figure>'
        for name in copied
    ) or "<p>Картинок пока нет. Добавь, и они уедут в zip вместе с сайтом.</p>"

    style = _css(accent or "#c45c26")
    (root / "style.css").write_text(style, encoding="utf-8")
    for index, page in enumerate(safe_pages):
        body = _paragraphs(page.get("body") or "")
        extra = gallery if index == 0 else ""
        document = _page(
            title=title or "Локальный сайт",
            tagline=tagline or "Работает из папки. Облако в отпуске.",
            nav=nav,
            heading=page.get("title") or "Страница",
            body=body + extra,
        )
        name = "index.html" if index == 0 else f"page-{index}.html"
        (root / name).write_text(document, encoding="utf-8")
        if index == 0:
            (root / "page-0.html").write_text(document, encoding="utf-8")

    archive = pack_zip(root, root.parent / f"{root.name}.zip")
    return {"folder": str(root), "zip": str(archive), "images": str(len(copied))}


def _paragraphs(text: str) -> str:
    chunks = [chunk.strip() for chunk in text.splitlines() if chunk.strip()]
    if not chunks:
        return "<p>Текст ещё не написан.</p>"
    return "\n".join(f"<p>{html.escape(chunk)}</p>" for chunk in chunks)


def _page(title: str, tagline: str, nav: str, heading: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <p class="mark">локальный сайт · zip</p>
    <h1>{html.escape(title)}</h1>
    <p class="tagline">{html.escape(tagline)}</p>
    <nav>{nav}</nav>
  </header>
  <main>
    <h2>{html.escape(heading)}</h2>
    {body}
  </main>
  <footer>Собрано в Пульте. Интернет опционален, как совесть у соседа.</footer>
</body>
</html>
"""


def _css(accent: str) -> str:
    color = accent if accent.startswith("#") and len(accent) in {4, 7} else "#c45c26"
    return f"""
:root {{ --ink: #1c140f; --paper: #f4efe6; --accent: {color}; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: Georgia, "Times New Roman", serif; background: var(--paper); color: var(--ink); }}
header, main, footer {{ width: min(860px, calc(100% - 32px)); margin: 0 auto; }}
header {{ padding: 48px 0 12px; border-bottom: 2px solid var(--ink); }}
.mark {{ letter-spacing: .14em; text-transform: uppercase; font-size: 12px; color: var(--accent); }}
h1 {{ font-size: 48px; margin: 8px 0; }}
.tagline {{ font-size: 18px; }}
nav a {{ margin-right: 16px; color: var(--ink); }}
main {{ padding: 28px 0 48px; }}
img {{ max-width: 100%; display: block; margin: 12px 0; border: 1px solid var(--ink); }}
footer {{ padding-bottom: 40px; font-size: 14px; }}
"""


def _safe_name(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ".-_" else "-" for ch in name)
    return cleaned or "image.png"
