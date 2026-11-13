"""Static multi-page website exporter for the Pulpit visual builder."""
from __future__ import annotations
import html
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

def slugify(value: str, fallback: str = "page") -> str:
    table = str.maketrans({
        "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"yo","ж":"zh","з":"z","и":"i","й":"y",
        "к":"k","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r","с":"s","т":"t","у":"u","ф":"f","х":"kh",
        "ц":"ts","ч":"ch","ш":"sh","щ":"sch","ъ":"","ы":"y","ь":"","э":"e","ю":"yu","я":"ya",
    })
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower().translate(table)).strip("-")
    if not slug or slug in {"index","assets","admin","null","undefined"}:
        slug = fallback
    return slug[:72].strip("-") or fallback

def _page_document(page: dict, pages: list[dict], index: int, site_title: str, language: str) -> str:
    name = str(page.get("name") or f"Страница {index + 1}")
    title = str(page.get("title") or f"{name} — {site_title}")
    description = str(page.get("description") or "")
    body = str(page.get("html") or "")
    css = str(page.get("css") or "")
    script = str(page.get("js") or "").replace("</script", "<\\/script")
    links = []
    for i, item in enumerate(pages):
        slug = slugify(item.get("slug") or item.get("name"), f"page-{i + 1}")
        href = "index.html" if i == 0 else f"{slug}.html"
        active = ' aria-current="page"' if i == index else ""
        links.append(f'<a href="{html.escape(href, quote=True)}"{active}>{html.escape(str(item.get("name") or f"Страница {i + 1}"))}</a>')
    nav = "\n".join(links)
    return f"""<!doctype html>
<html lang="{html.escape(language, quote=True)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{html.escape(description, quote=True)}">
<meta name="theme-color" content="#172033">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(title, quote=True)}">
<meta property="og:description" content="{html.escape(description, quote=True)}">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="style.css">
<style>
{css}
</style>
</head>
<body>
<header class="pulpit-site-header">
<a class="pulpit-brand" href="index.html">{html.escape(site_title)}</a>
<nav aria-label="Основная навигация">{nav}</nav>
</header>
<main>
{body}
</main>
<footer class="pulpit-site-footer">Создано в «Пульте» · локальный экспорт без обязательного облака</footer>
<script>
{script}
</script>
</body>
</html>
"""

def export_site(payload: dict, asset_dir: str | Path, destination: str | Path) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Некорректный проект")
    pages = payload.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError("В проекте нет страниц")
    if len(pages) > 100:
        raise ValueError("Максимум 100 страниц в одном проекте")
    title = str(payload.get("title") or "Мой сайт").strip()[:160] or "Мой сайт"
    language = str(payload.get("language") or "ru")[:12] or "ru"
    slugs = set()
    normalized = []
    for i, page in enumerate(pages):
        if not isinstance(page, dict):
            raise ValueError(f"Страница {i + 1} имеет неверный формат")
        slug = slugify(page.get("slug") or page.get("name"), f"page-{i+1}")
        if slug in slugs:
            slug = f"{slug}-{i+1}"
        slugs.add(slug)
        normalized.append({**page, "slug": slug})
    output = Path(destination).expanduser()
    if output.suffix.lower() != ".zip":
        output = output.with_suffix(".zip")
    output.parent.mkdir(parents=True, exist_ok=True)
    base_css = """
:root{color-scheme:light;--pulpit-ink:#172033;--pulpit-paper:#fff;--pulpit-accent:#6d75e8}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--pulpit-paper);color:var(--pulpit-ink);font:16px/1.6 Inter,system-ui,-apple-system,"Segoe UI",sans-serif}
.pulpit-site-header{display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap;padding:18px max(24px,calc((100vw - 1180px)/2));border-bottom:1px solid #e5e7eb;background:#fff}
.pulpit-brand{font-weight:800;color:inherit;text-decoration:none;font-size:1.15rem}
.pulpit-site-header nav{display:flex;gap:16px;flex-wrap:wrap}
.pulpit-site-header nav a{color:inherit;text-decoration:none}
.pulpit-site-header nav a[aria-current=page]{color:var(--pulpit-accent);font-weight:700}
.pulpit-site-footer{max-width:1180px;margin:40px auto 0;padding:24px;color:#64748b;border-top:1px solid #e5e7eb;font-size:13px}
main{min-height:55vh}img,video,iframe{max-width:100%}
@media(max-width:640px){.pulpit-site-header{align-items:flex-start}.pulpit-site-header nav{gap:10px 14px}}
"""
    with tempfile.TemporaryDirectory(prefix="pulpit-site-") as temp:
        root = Path(temp) / "site"
        assets = root / "assets"
        assets.mkdir(parents=True)
        asset_count = 0
        source_assets = Path(asset_dir)
        if source_assets.is_dir():
            for item in source_assets.iterdir():
                if item.is_file() and item.suffix.lower() in {".png",".jpg",".jpeg",".webp",".gif",".bmp"} and item.stat().st_size <= 40*1024*1024:
                    shutil.copy2(item, assets / item.name)
                    asset_count += 1
        (root / "style.css").write_text(base_css, encoding="utf-8")
        for i, page in enumerate(normalized):
            filename = "index.html" if i == 0 else f"{page['slug']}.html"
            (root / filename).write_text(_page_document(page, normalized, i, title, language), encoding="utf-8")
        (root / "README.md").write_text(
            f"# {title}\n\nСтатический сайт из Пульта.\n\nСтраниц: {len(normalized)}\nРесурсов: {asset_count}\n\nГлавная страница — index.html. Распакуйте архив и загрузите содержимое на статический хостинг, например GitHub Pages.\n",
            encoding="utf-8",
        )
        (root / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=8) as archive:
            for item in sorted(root.rglob("*")):
                if item.is_file():
                    archive.write(item, item.relative_to(root).as_posix())
    return {"zip": str(output), "pages": str(len(normalized)), "assets": str(asset_count), "bytes": str(output.stat().st_size)}
