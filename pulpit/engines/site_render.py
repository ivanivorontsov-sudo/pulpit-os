"""Рендер интерактивного проекта в локальный сайт и zip."""

from __future__ import annotations

import html
import shutil
from pathlib import Path

from pulpit.engines.converters import pack_zip


def export_project(folder: str | Path, dest_dir: str | Path) -> dict[str, str]:
    root = Path(folder)
    project = __import__("json").loads((root / "project.json").read_text(encoding="utf-8"))
    out = Path(dest_dir)
    if out.exists():
        shutil.rmtree(out)
    images = out / "images"
    images.mkdir(parents=True)
    copied = _copy_assets(root, images)
    pages = project.get("pages") or []
    nav = "\n".join(
        f'<a href="{_page_href(index)}">{html.escape(page.get("title") or f"Страница {index + 1}")}</a>'
        for index, page in enumerate(pages)
    )
    style = _css(project)
    (out / "style.css").write_text(style, encoding="utf-8")
    for index, page in enumerate(pages):
        document = _document(project, page, nav)
        (out / _page_href(index)).write_text(document, encoding="utf-8")
    if not pages:
        (out / "index.html").write_text("<p>Пустой проект</p>", encoding="utf-8")
    archive = pack_zip(out, out.parent / f"{out.name}.zip")
    return {"folder": str(out), "zip": str(archive), "images": str(len(copied))}


def preview_html(project: dict, page_index: int, asset_root: str | Path, embedded: bool = False) -> str:
    pages = project.get("pages") or []
    page = pages[page_index] if pages else {"title": "Пусто", "blocks": []}
    nav = "\n".join(
        f'<a href="#page-{index}">{html.escape(item.get("title") or "")}</a>'
        for index, item in enumerate(pages)
    )
    body = _blocks(page.get("blocks") or [], Path(asset_root), preview="embed" if embedded else "file")
    return _shell(project, nav, page.get("title") or "Страница", body)


def _copy_assets(root: Path, images: Path) -> list[str]:
    copied: list[str] = []
    assets = root / "assets"
    if not assets.is_dir():
        return copied
    for path in assets.iterdir():
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}:
            shutil.copy2(path, images / path.name)
            copied.append(path.name)
    return copied


def _document(project: dict, page: dict, nav: str) -> str:
    body = _blocks(page.get("blocks") or [], Path("."), preview=False)
    return _shell(project, nav, page.get("title") or "Страница", body)


def _shell(project: dict, nav: str, heading: str, body: str) -> str:
    title = html.escape(project.get("title") or "Сайт")
    tagline = html.escape(project.get("tagline") or "")
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <p class="mark">локальный сайт · zip</p>
    <h1>{title}</h1>
    <p class="tagline">{tagline}</p>
    <nav>{nav}</nav>
  </header>
  <main>
    <h2>{html.escape(heading)}</h2>
    {body}
  </main>
  <footer>Собрано в Пульте. Картинки лежат рядом, облако не вызывали.</footer>
</body>
</html>
"""


def _blocks(blocks: list[dict], asset_root: Path, preview: str | bool) -> str:
    chunks = []
    for block in blocks:
        kind = block.get("type")
        text = html.escape(block.get("text") or "")
        sub = html.escape(block.get("sub") or "")
        anchor = f' id="block-{html.escape(str(block.get("id") or ""))}"'
        if kind == "hero":
            chunks.append(f'<section class="hero"{anchor}><h3>{text}</h3><p>{sub}</p></section>')
        elif kind == "heading":
            chunks.append(f"<h3{anchor}>{text}</h3>")
        elif kind == "features":
            items = "".join(f"<li>{html.escape(part.strip())}</li>" for part in (block.get("text") or "").split("|") if part.strip())
            chunks.append(f'<ul class="features"{anchor}>{items}</ul>')
        elif kind == "cards":
            titles = [part.strip() for part in (block.get("text") or "").split("|")]
            notes = [part.strip() for part in (block.get("sub") or "").split("|")]
            cards = "".join(
                f"<article><h3>{html.escape(title)}</h3><p>{html.escape(notes[i] if i < len(notes) else '')}</p></article>"
                for i, title in enumerate(titles) if title
            )
            chunks.append(f'<section class="cards"{anchor}>{cards}</section>')
        elif kind == "faq":
            rows = []
            for line in (block.get("text") or "").splitlines():
                question, _, answer = line.partition("|")
                if question.strip():
                    rows.append(f"<details><summary>{html.escape(question.strip())}</summary><p>{html.escape(answer.strip())}</p></details>")
            chunks.append(f'<section class="faq"{anchor}>' + "".join(rows) + "</section>")
        elif kind == "spacer":
            size = "".join(ch for ch in str(block.get("text") or "32") if ch.isdigit()) or "32"
            chunks.append(f'<div{anchor} style="height:{size}px"></div>')
        elif kind == "footer":
            chunks.append(f'<p class="foot"{anchor}>{text}</p>')
        elif kind == "quote":
            chunks.append(f"<blockquote{anchor}>{text}</blockquote>")
        elif kind == "button":
            href = html.escape(block.get("href") or "#")
            style = html.escape(str(block.get("style") or "fill"))
            size = html.escape(str(block.get("size") or "md"))
            shape = html.escape(str(block.get("shape") or "square"))
            color = html.escape(str(block.get("color") or "#c45c26"))
            chunks.append(
                f'<p{anchor}><a class="button {style} {size} {shape}" style="--btn:{color}" href="{href}">{text}</a></p>'
            )
        elif kind == "columns":
            chunks.append(f'<section class="cols"{anchor}><p>{text}</p><p>{sub}</p></section>')
        elif kind == "image":
            chunks.append(_image(block.get("image") or "", text, asset_root, preview, anchor))
        elif kind == "gallery":
            figures = "\n".join(
                _image(name, "", asset_root, preview, "") for name in block.get("images") or []
            )
            chunks.append(f'<section class="gallery"{anchor}><h3>{text}</h3>{figures}</section>')
        else:
            chunks.append(f"<p{anchor}>{text}</p>")
    return "\n".join(chunks) or "<p>На странице ещё нет блоков.</p>"


def _image(rel: str, caption: str, asset_root: Path, preview: str | bool, anchor: str = "") -> str:
    name = Path(rel).name
    if not name:
        return f"<p class='missing'{anchor}>Картинка не выбрана</p>"
    if preview in {True, "file"}:
        src = (asset_root / "assets" / name).resolve().as_uri()
    elif preview == "embed":
        src = f"assets/{html.escape(name)}"
    else:
        src = f"images/{html.escape(name)}"
    cap = f"<figcaption>{caption}</figcaption>" if caption else ""
    return f'<figure{anchor}><img src="{src}" alt="{caption or name}">{cap}</figure>'


def _page_href(index: int) -> str:
    return "index.html" if index == 0 else f"page-{index}.html"


def _css(project: dict) -> str:
    accent = project.get("accent") or "#c45c26"
    paper = project.get("paper") or "#f4efe6"
    ink = project.get("ink") or "#1c140f"
    return f"""
:root {{ --ink: {ink}; --paper: {paper}; --accent: {accent}; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: Georgia, "Times New Roman", serif; background: var(--paper); color: var(--ink); }}
header, main, footer {{ width: min(920px, calc(100% - 32px)); margin: 0 auto; }}
header {{ padding: 42px 0 12px; border-bottom: 2px solid var(--ink); }}
.mark {{ letter-spacing: .14em; text-transform: uppercase; font-size: 12px; color: var(--accent); }}
h1 {{ font-size: 46px; margin: 8px 0; }}
nav a, a {{ color: var(--ink); }}
nav a {{ margin-right: 16px; }}
.hero {{ padding: 18px 0; border-bottom: 1px solid var(--accent); }}
.cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
.gallery {{ display: grid; gap: 12px; }}
img {{ max-width: 100%; display: block; border: 1px solid var(--ink); }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
.cards article, .faq details {{ border: 1px solid var(--ink); padding: 12px; }}
.features {{ padding-left: 18px; }}
.button {{ display: inline-block; padding: 8px 14px; text-decoration: none; border: 2px solid transparent; }}
.button.fill {{ background: var(--btn, var(--accent)); color: white; }}
.button.outline {{ background: transparent; color: var(--btn, var(--accent)); border-color: var(--btn, var(--accent)); }}
.button.ghost {{ background: transparent; color: var(--ink); }}
.button.sm {{ padding: 4px 10px; font-size: 14px; }}
.button.lg {{ padding: 14px 22px; font-size: 20px; }}
.button.pill {{ border-radius: 999px; }}
.button.square {{ border-radius: 4px; }}
footer {{ padding-bottom: 40px; font-size: 14px; }}
"""
