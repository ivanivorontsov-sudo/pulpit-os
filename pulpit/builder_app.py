"""Native pywebview host and safe local file bridge for the Pulpit page builder."""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import traceback
from pathlib import Path

from pulpit.engines.site_export import export_site

APP_DIR = Path(__file__).resolve().parent
WEB_DIR = APP_DIR / "web"
DEFAULT_FOLDER = Path.home() / "PulpitSites" / "constructor"


def _safe_name(value: str) -> str:
    name = Path(str(value or "image.png")).name
    name = re.sub(r"[^0-9A-Za-zА-Яа-яЁё._ -]+", "_", name).strip(" .")
    return name[:100] or "image.png"


def _migrate_legacy(legacy: dict) -> dict:
    """Keep old v2 constructor projects editable in the new builder."""
    from html import escape

    renderers = {
        "hero": lambda b: f'<section class="hero"><p class="eyebrow">ПУЛЬТ · САЙТ</p><h1>{escape(str(b.get("text", "")))}</h1><p>{escape(str(b.get("sub", "")))}</p></section>',
        "heading": lambda b: f'<h2>{escape(str(b.get("text", "")))}</h2>',
        "text": lambda b: f'<p>{escape(str(b.get("text", "")))}</p>',
        "quote": lambda b: f'<blockquote><p>{escape(str(b.get("text", "")))}</p><cite>{escape(str(b.get("sub", "")))}</cite></blockquote>',
        "columns": lambda b: f'<section class="cols"><div><p>{escape(str(b.get("text", "")))}</p></div><div><p>{escape(str(b.get("sub", "")))}</p></div></section>',
        "button": lambda b: f'<p><a class="button" href="{escape(str(b.get("href", "#")), quote=True)}">{escape(str(b.get("text", "Кнопка")))}</a></p>',
        "image": lambda b: f'<figure><img src="{escape(str(b.get("image", "")), quote=True)}" alt="{escape(str(b.get("text", "")), quote=True)}"><figcaption>{escape(str(b.get("text", "")))}</figcaption></figure>',
        "gallery": lambda b: '<section class="gallery"><h2>' + escape(str(b.get("text", "Галерея"))) + "</h2>" + "".join(f'<img src="{escape(str(src), quote=True)}" alt="">' for src in b.get("images", [])) + "</section>",
        "features": lambda b: "<ul>" + "".join(f"<li>{escape(part.strip())}</li>" for part in str(b.get("text", "")).split("|") if part.strip()) + "</ul>",
        "cards": lambda b: '<section class="cards">' + "".join(f"<article><h3>{escape(t.strip())}</h3><p>{escape((b.get('sub','').split('|') + [''])[i])}</p></article>" for i, t in enumerate(str(b.get("text", "")).split("|")) if t.strip()) + "</section>",
        "faq": lambda b: '<section class="faq">' + "".join(f"<details><summary>{escape(q.strip())}</summary><p>{escape(a.strip())}</p></details>" for line in str(b.get("text", "")).splitlines() for q, _, a in [line.partition("|")] if q.strip()) + "</section>",
        "footer": lambda b: f'<footer><p>{escape(str(b.get("text", "")))}</p></footer>',
    }
    pages = []
    for i, page in enumerate(legacy.get("pages") or []):
        html_blocks = [renderers[block["type"]](block) for block in page.get("blocks", []) if block.get("type") in renderers]
        pages.append({
            "id": str(page.get("id") or f"page-{i+1}"),
            "name": str(page.get("title") or f"Страница {i+1}"),
            "component": "\n".join(html_blocks) or "<main><h1>Новая страница</h1></main>",
            "styles": "",
        })
    if not pages:
        pages = [{"id": "home", "name": "Главная", "component": "<main><h1>Новый сайт</h1></main>", "styles": ""}]
    page_meta = {
        page["id"]: {"slug": "index" if i == 0 else f"page-{i+1}", "title": page["name"], "description": ""}
        for i, page in enumerate(pages)
    }
    return {
        "format": "pulpit-page-project",
        "version": 1,
        "title": str(legacy.get("title") or "Мой сайт"),
        "language": "ru",
        "pageMeta": page_meta,
        "projectData": {"pages": pages, "styles": []},
    }


class BuilderApi:
    """Only local project files are accessed; no account or cloud service is required."""

    def __init__(self) -> None:
        self.window = None
        self.folder = DEFAULT_FOLDER
        self.project_path = self.folder / "project.json"
        self.folder.mkdir(parents=True, exist_ok=True)
        (self.folder / "assets").mkdir(exist_ok=True)

    def attach_window(self, window) -> None:
        self.window = window

    def _dialog(self, kind: int, **kwargs):
        if self.window is None:
            raise RuntimeError("Окно конструктора ещё не готово")
        return self.window.create_file_dialog(kind, **kwargs)

    def _read_document(self, path: Path) -> dict:
        if path.stat().st_size > 25 * 1024 * 1024:
            raise ValueError("Файл проекта больше 25 МБ")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Неверный формат проекта")
        if data.get("format") != "pulpit-page-project" or "projectData" not in data:
            data = _migrate_legacy(data)
        if not isinstance(data.get("projectData"), dict):
            raise ValueError("В проекте отсутствуют данные конструктора")
        self.folder = path.parent
        self.project_path = path
        (self.folder / "assets").mkdir(parents=True, exist_ok=True)
        return data

    def get_initial_state(self) -> dict:
        document = None
        if self.project_path.is_file():
            try:
                document = self._read_document(self.project_path)
            except Exception:
                document = None
        return {
            "document": document,
            "projectPath": str(self.project_path),
            "projectFolder": str(self.folder),
            "assets": self.list_assets(),
        }

    def open_project(self) -> dict | None:
        import webview
        selected = self._dialog(
            webview.OPEN_DIALOG,
            directory=str(self.folder),
            allow_multiple=False,
            file_types=("Проект Пульта (*.json)", "Все файлы (*.*)"),
        )
        if not selected:
            return None
        path = Path(selected[0]).expanduser().resolve()
        data = self._read_document(path)
        return {"document": data, "projectPath": str(self.project_path), "assets": self.list_assets()}

    def save_project(self, document_json: str) -> dict:
        data = json.loads(document_json)
        if not isinstance(data, dict) or data.get("format") != "pulpit-page-project":
            raise ValueError("Некорректный проект конструктора")
        project_data = data.get("projectData")
        if not isinstance(project_data, dict) or not isinstance(project_data.get("pages"), list):
            raise ValueError("В проекте отсутствуют страницы")
        if len(project_data["pages"]) > 100:
            raise ValueError("Максимум 100 страниц")
        self.folder.mkdir(parents=True, exist_ok=True)
        (self.folder / "assets").mkdir(exist_ok=True)
        temp = self.project_path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.project_path)
        return {"ok": True, "path": str(self.project_path)}

    def save_project_as(self, document_json: str) -> dict | None:
        import webview
        selected = self._dialog(
            webview.SAVE_DIALOG,
            directory=str(self.folder),
            save_filename="project.json",
            file_types=("Проект Пульта (*.json)",),
        )
        if not selected:
            return None
        path = Path(selected[0]).expanduser()
        if path.suffix.lower() != ".json":
            path = path.with_suffix(".json")
        self.folder = path.parent.resolve()
        self.project_path = path.resolve()
        (self.folder / "assets").mkdir(parents=True, exist_ok=True)
        return self.save_project(document_json)

    def import_assets(self, files_json: str) -> list[dict]:
        files = json.loads(files_json)
        if not isinstance(files, list) or len(files) > 40:
            raise ValueError("Можно добавить не более 40 изображений за раз")
        assets_dir = self.folder / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        allowed = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
        total, result = 0, []
        for item in files:
            name = _safe_name(item.get("name", "image.png"))
            if Path(name).suffix.lower() not in allowed:
                continue
            raw = str(item.get("data") or "")
            if raw.startswith("data:") and "," in raw:
                raw = raw.split(",", 1)[1]
            try:
                content = base64.b64decode(raw, validate=True)
            except Exception as exc:
                raise ValueError(f"Не удалось прочитать {name}") from exc
            total += len(content)
            if len(content) > 20 * 1024 * 1024 or total > 80 * 1024 * 1024:
                raise ValueError("Размер изображений слишком велик")
            target = assets_dir / name
            stem, ext, count = target.stem, target.suffix, 2
            while target.exists():
                target = assets_dir / f"{stem}-{count}{ext}"
                count += 1
            target.write_bytes(content)
            result.append({"name": target.name, "src": f"assets/{target.name}", "bytes": len(content)})
        return result

    def list_assets(self) -> list[dict]:
        folder = self.folder / "assets"
        allowed = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
        if not folder.is_dir():
            return []
        return [
            {"name": item.name, "src": f"assets/{item.name}", "bytes": item.stat().st_size}
            for item in sorted(folder.iterdir(), key=lambda p: p.name.lower())
            if item.is_file() and item.suffix.lower() in allowed
        ]

    def export_site(self, export_json: str) -> dict | None:
        import webview
        selected = self._dialog(
            webview.SAVE_DIALOG,
            directory=str(self.folder),
            save_filename="site.zip",
            file_types=("ZIP-архив (*.zip)",),
        )
        if not selected:
            return None
        return {"ok": True, **export_site(json.loads(export_json), self.folder / "assets", selected[0])}

    def reveal_project_folder(self) -> dict:
        import subprocess
        self.folder.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(self.folder))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(self.folder)])
        else:
            subprocess.Popen(["xdg-open", str(self.folder)])
        return {"ok": True, "path": str(self.folder)}


def run() -> None:
    try:
        import webview
        api = BuilderApi()
        window = webview.create_window(
            "Пульт — визуальный конструктор сайтов",
            str(WEB_DIR / "index.html"),
            js_api=api,
            width=1560,
            height=960,
            min_size=(1120, 720),
            resizable=True,
            text_select=True,
            confirm_close=True,
        )
        api.attach_window(window)
        webview.start(debug=False)
    except Exception as exc:
        log = Path.home() / "PulpitSites" / "builder-error.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(f"{type(exc).__name__}: {exc}\n\n{traceback.format_exc()}", encoding="utf-8")
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Пульт — конструктор", f"Не удалось запустить визуальный редактор.\n\n{exc}\n\nПодробности: {log}")
            root.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    run()
