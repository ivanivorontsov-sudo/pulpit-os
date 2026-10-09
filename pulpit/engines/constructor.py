"""Конструктор страниц.

Источник правды — дерево блоков, не HTML. Так делают Builder, GrapesJS
и Sanity: палитра вставляет тип из реестра, правки идут в свойства,
рендер и zip собираются уже из модели.
"""

from __future__ import annotations

import copy
from uuid import uuid4

from pulpit.engines.site_project import blank_page, new_project


REGISTRY: dict[str, dict] = {
    "hero": {"label": "Шапка", "fields": ["text", "sub"], "defaults": {"text": "Название", "sub": "Обещание в одну строку"}},
    "heading": {"label": "Заголовок", "fields": ["text"], "defaults": {"text": "Раздел"}},
    "text": {"label": "Текст", "fields": ["text"], "defaults": {"text": "Абзац конструктора."}},
    "image": {"label": "Картинка", "fields": ["text", "image"], "defaults": {"text": "Подпись", "image": ""}},
    "gallery": {"label": "Галерея", "fields": ["text", "images"], "defaults": {"text": "Галерея", "images": []}},
    "quote": {"label": "Цитата", "fields": ["text", "sub"], "defaults": {"text": "Цитата", "sub": "Кто сказал"}},
    "columns": {"label": "Две колонки", "fields": ["text", "sub"], "defaults": {"text": "Слева", "sub": "Справа"}},
    "cards": {"label": "Карточки", "fields": ["text", "sub"], "defaults": {"text": "Одна|Две|Три", "sub": "Коротко|Ещё|И ещё"}},
    "features": {"label": "Преимущества", "fields": ["text"], "defaults": {"text": "Без сети|Картинки в zip|Office рядом"}},
    "faq": {"label": "Вопросы", "fields": ["text"], "defaults": {"text": "Где интернет?|Не нужен\nКак открыть?|index.html"}},
    "button": {
        "label": "Кнопка",
        "fields": ["text", "href", "style", "size", "shape", "color"],
        "defaults": {"text": "Дальше", "href": "index.html", "style": "fill", "size": "md", "shape": "square", "color": "#c45c26"},
    },
    "spacer": {"label": "Отступ", "fields": ["text"], "defaults": {"text": "32"}},
    "footer": {"label": "Подвал", "fields": ["text"], "defaults": {"text": "Собрано в Пульте"}},
}

TEMPLATES = {
    "landing": ["hero", "features", "cards", "quote", "button", "footer"],
    "gallery": ["hero", "gallery", "text", "footer"],
    "catalog": ["hero", "cards", "faq", "button", "footer"],
}


class Constructor:
    def __init__(self, project: dict | None = None) -> None:
        self.project = project or new_project("Конструктор")
        self.page_index = 0
        self.selected: str | None = self.page()["blocks"][0]["id"]
        self._undo: list[dict] = []
        self._redo: list[dict] = []

    def page(self) -> dict:
        return self.project["pages"][self.page_index]

    def block(self) -> dict | None:
        for item in self.page()["blocks"]:
            if item["id"] == self.selected:
                return item
        return None

    def add(self, kind: str) -> dict:
        self._snapshot()
        block = make_block(kind)
        self.page()["blocks"].append(block)
        self.selected = block["id"]
        return block

    def update(self, key: str, value) -> None:
        current = self.block()
        if not current or current.get(key) == value:
            return
        self._snapshot()
        current[key] = value

    def move_to(self, block_id: str, target_index: int) -> None:
        blocks = self.page()["blocks"]
        index = next((i for i, item in enumerate(blocks) if item["id"] == block_id), -1)
        if index < 0:
            return
        target_index = max(0, min(target_index, len(blocks) - 1))
        if index == target_index:
            return
        self._snapshot()
        item = blocks.pop(index)
        blocks.insert(target_index, item)
        self.selected = item["id"]

    def insert_at(self, kind: str, index: int) -> dict:
        self._snapshot()
        block = make_block(kind)
        blocks = self.page()["blocks"]
        blocks.insert(max(0, min(index, len(blocks))), block)
        self.selected = block["id"]
        return block

    def insert_button(self, spec: dict, index: int | None = None) -> dict:
        self._snapshot()
        block = make_block("button")
        block.update({key: value for key, value in spec.items() if value not in (None, "")})
        blocks = self.page()["blocks"]
        blocks.insert(len(blocks) if index is None else max(0, min(index, len(blocks))), block)
        self.selected = block["id"]
        return block

    def move(self, delta: int) -> None:
        blocks = self.page()["blocks"]
        index = self._index()
        target = index + delta
        if index < 0 or not 0 <= target < len(blocks):
            return
        self._snapshot()
        blocks[index], blocks[target] = blocks[target], blocks[index]

    def delete(self) -> None:
        index = self._index()
        if index < 0:
            return
        self._snapshot()
        del self.page()["blocks"][index]
        if self.page()["blocks"]:
            self.selected = self.page()["blocks"][max(0, index - 1)]["id"]
        else:
            self.selected = None

    def duplicate(self) -> dict | None:
        current = self.block()
        if not current:
            return None
        self._snapshot()
        clone = copy.deepcopy(current)
        clone["id"] = uuid4().hex[:8]
        self.page()["blocks"].insert(self._index() + 1, clone)
        self.selected = clone["id"]
        return clone

    def add_page(self, title: str = "Страница") -> None:
        self._snapshot()
        self.project["pages"].append(blank_page(title))
        self.page_index = len(self.project["pages"]) - 1
        self.selected = self.page()["blocks"][0]["id"]

    def apply_template(self, name: str) -> None:
        kinds = TEMPLATES.get(name)
        if not kinds:
            raise KeyError(name)
        self._snapshot()
        self.page()["blocks"] = [make_block(kind) for kind in kinds]
        self.selected = self.page()["blocks"][0]["id"]

    def undo(self) -> bool:
        if not self._undo:
            return False
        self._redo.append(self._dump())
        self._restore(self._undo.pop())
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._undo.append(self._dump())
        self._restore(self._redo.pop())
        return True

    def _index(self) -> int:
        return next((i for i, item in enumerate(self.page()["blocks"]) if item["id"] == self.selected), -1)

    def _snapshot(self) -> None:
        self._undo.append(self._dump())
        self._redo.clear()
        if len(self._undo) > 40:
            self._undo.pop(0)

    def _dump(self) -> dict:
        return {"project": copy.deepcopy(self.project), "page_index": self.page_index, "selected": self.selected}

    def _restore(self, state: dict) -> None:
        self.project = state["project"]
        self.page_index = state["page_index"]
        self.selected = state["selected"]


def make_block(kind: str) -> dict:
    spec = REGISTRY.get(kind) or REGISTRY["text"]
    block = {"id": uuid4().hex[:8], "type": kind if kind in REGISTRY else "text"}
    block.update(copy.deepcopy(spec["defaults"]))
    return block
