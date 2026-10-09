"""Старый вход сборщика. Теперь он тоже кладёт картинки в проект и в zip."""

from __future__ import annotations

from pathlib import Path

from pulpit.engines.site_project import add_image, new_project, save_project
from pulpit.engines.site_render import export_project


def build_site(
    dest_dir: str | Path,
    title: str,
    tagline: str,
    accent: str,
    pages: list[dict[str, str]],
    image_paths: list[str] | None = None,
) -> dict[str, str]:
    project_dir = Path(dest_dir).parent / f"{Path(dest_dir).name}-project"
    project = new_project(title or "Локальный сайт")
    project["tagline"] = tagline or project["tagline"]
    project["accent"] = accent or project["accent"]
    project["pages"] = []
    saved = save_project(project_dir, project)
    gallery = []
    for index, raw in enumerate(image_paths or []):
        if Path(raw).is_file():
            gallery.append(add_image(project_dir, raw, f"photo-{index + 1}"))
    built_pages = []
    for index, page in enumerate(pages or [{"title": "Главная", "body": ""}]):
        blocks = [
            {"id": f"h{index}", "type": "hero", "text": page.get("title") or "Страница", "sub": tagline or ""},
            {"id": f"t{index}", "type": "text", "text": page.get("body") or ""},
        ]
        if index == 0 and gallery:
            blocks.append({"id": "g0", "type": "gallery", "text": "Картинки", "images": gallery})
        built_pages.append({"id": f"p{index}", "title": page.get("title") or f"Страница {index + 1}", "blocks": blocks})
    project["pages"] = built_pages
    save_project(saved.parent, project)
    return export_project(project_dir, dest_dir)
