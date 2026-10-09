"""Проект сайта: страницы, блоки и картинки, которые уже лежат в папке."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from pulpit.engines.images import store_image


def new_project(title: str = "Локальный сайт") -> dict:
    return {
        "version": 2,
        "title": title,
        "tagline": "Картинки в папке, интернет опционален",
        "accent": "#c45c26",
        "paper": "#f4efe6",
        "ink": "#1c140f",
        "pages": [blank_page("Главная")],
    }


def blank_page(title: str = "Страница") -> dict:
    return {"id": uuid4().hex[:8], "title": title, "blocks": [blank_block("hero")]}


def blank_block(kind: str = "text") -> dict:
    presets = {
        "hero": {"text": "Большой заголовок", "sub": "Короткий подзаголовок"},
        "text": {"text": "Абзац, который можно править прямо здесь."},
        "image": {"text": "Подпись к картинке", "image": ""},
        "gallery": {"text": "Галерея", "images": []},
        "quote": {"text": "Цитата, которую не стыдно оставить в zip."},
        "button": {"text": "Кнопка", "href": "page-0.html"},
        "columns": {"text": "Левая колонка", "sub": "Правая колонка"},
    }
    payload = {"id": uuid4().hex[:8], "type": kind}
    payload.update(presets.get(kind, presets["text"]))
    return payload


def save_project(folder: str | Path, project: dict) -> Path:
    root = Path(folder)
    (root / "assets").mkdir(parents=True, exist_ok=True)
    target = root / "project.json"
    target.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def load_project(folder: str | Path) -> dict:
    target = Path(folder) / "project.json"
    return json.loads(target.read_text(encoding="utf-8"))


def add_image(folder: str | Path, src: str | Path, stem: str) -> str:
    return "assets/" + store_image(src, Path(folder) / "assets", stem)
