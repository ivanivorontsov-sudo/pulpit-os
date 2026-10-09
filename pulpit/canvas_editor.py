"""Интерактивный холст: блок видно, его можно ткнуть и утащить."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from pulpit.engines.constructor import REGISTRY, Constructor
from pulpit.engines.site_project import add_image, load_project, save_project
from pulpit.engines.preview_doc import standalone
from pulpit.engines.site_render import _css, preview_html
from pulpit.html_view import HtmlPane


class CanvasEditor(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.folder = Path.home() / "PulpitSites" / "constructor"
        self.folder.mkdir(parents=True, exist_ok=True)
        project = load_project(self.folder) if (self.folder / "project.json").exists() else None
        self.doc = Constructor(project)
        self._cards: list[ctk.CTkFrame] = []
        self._drag_id: str | None = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(bar, text="Холст", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        ctk.CTkButton(bar, text="Обновить", width=100, command=self.reload).pack(side="left", padx=8)
        ctk.CTkButton(bar, text="Текст", width=70, command=lambda: self.add("text")).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="Картинка", width=90, command=lambda: self.add("image")).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="Кнопка", width=80, command=lambda: self.add("button")).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="ZIP", width=60, command=self.export).pack(side="right", padx=4)
        ctk.CTkButton(bar, text="Просмотр", width=100, command=self.preview).pack(side="right", padx=4)
        stage = ctk.CTkFrame(self, fg_color="transparent")
        stage.pack(fill="both", expand=True, padx=12, pady=8)
        stage.grid_columnconfigure(1, weight=1)
        stage.grid_columnconfigure(2, weight=1)
        stage.grid_rowconfigure(0, weight=1)
        self.palette = ctk.CTkScrollableFrame(stage, width=150, label_text="Тащи на холст")
        self.palette.grid(row=0, column=0, sticky="nsew", padx=4)
        for kind, spec in REGISTRY.items():
            item = ctk.CTkButton(self.palette, text=spec["label"], cursor="fleur")
            item.pack(fill="x", pady=3)
            item.bind("<ButtonPress-1>", lambda _event, name=kind: self._palette_start(name))
            item.bind("<B1-Motion>", self._drag_motion)
            item.bind("<ButtonRelease-1>", self._palette_drop)
        self.paper = ctk.CTkScrollableFrame(stage, fg_color="#f4efe6", label_text="Визуальный редактор")
        self.paper.grid(row=0, column=1, sticky="nsew", padx=4)
        self.preview = HtmlPane(stage)
        self.preview.grid(row=0, column=2, sticky="nsew", padx=4)
        self.placeholder = None
        self._drag_kind: str | None = None
        self.status = ctk.CTkLabel(self, text="Ткни блок. Ручка ⋮⋮ таскает. Текст пишется прямо в карточке.")
        self.status.pack(anchor="w", padx=16, pady=(0, 8))

    def reload(self) -> None:
        if (self.folder / "project.json").exists():
            self.doc = Constructor(load_project(self.folder))
        self.refresh()

    def refresh(self) -> None:
        for child in self.paper.winfo_children():
            child.destroy()
        self._cards = []
        for block in self.doc.page()["blocks"]:
            self._cards.append(self._card(block))
        self.render_html()

    def render_html(self) -> None:
        document = standalone(
            preview_html(self.doc.project, self.doc.page_index, self.folder, embedded=True),
            _css(self.doc.project),
            self.folder,
        )
        self.preview.show_html(document)

    def _card(self, block: dict) -> ctk.CTkFrame:
        selected = block["id"] == self.doc.selected
        card = ctk.CTkFrame(self.paper, fg_color="#fffaf3", border_width=2, border_color="#c45c26" if selected else "#d9cbb8")
        card.pack(fill="x", padx=18, pady=8)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=8, pady=4)
        handle = ctk.CTkLabel(head, text="⋮⋮ тащи", width=70, cursor="fleur", text_color="#1c140f")
        handle.pack(side="left")
        ctk.CTkLabel(head, text=REGISTRY.get(block["type"], {}).get("label", block["type"]), text_color="#8a7362").pack(side="left")
        ctk.CTkButton(head, text="убрать", width=70, command=lambda item=block["id"]: self.remove(item)).pack(side="right")
        self._bind_drag(handle, block["id"])
        self._bind_drag(card, block["id"])
        self._body(card, block)
        card.bind("<Button-1>", lambda _event, item=block["id"]: self.select(item))
        return card

    def _body(self, card: ctk.CTkFrame, block: dict) -> None:
        kind = block.get("type")
        if kind == "image":
            self._image_body(card, block)
            return
        if kind == "button":
            self._button_body(card, block)
            return
        text = ctk.CTkTextbox(card, height=90, fg_color="#fffaf3", text_color="#1c140f")
        text.pack(fill="x", padx=10, pady=6)
        text.insert("1.0", block.get("text") or "")
        text.bind("<FocusOut>", lambda _event, item=block["id"], widget=text: self.commit(item, "text", widget.get("1.0", "end").strip()))
        if block.get("sub") is not None and kind in {"hero", "quote", "columns", "cards"}:
            sub = ctk.CTkEntry(card, fg_color="#fffaf3", text_color="#1c140f")
            sub.insert(0, block.get("sub") or "")
            sub.pack(fill="x", padx=10, pady=(0, 8))
            sub.bind("<FocusOut>", lambda _event, item=block["id"], widget=sub: self.commit(item, "sub", widget.get()))

    def _image_body(self, card: ctk.CTkFrame, block: dict) -> None:
        path = self.folder / (block.get("image") or "")
        if path.is_file():
            image = Image.open(path)
            image.thumbnail((420, 180))
            card._preview = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
            ctk.CTkLabel(card, image=card._preview, text="").pack(padx=10, pady=6)
        else:
            ctk.CTkLabel(card, text="Картинки нет. Нажми и положи.", text_color="#8a7362").pack(padx=10, pady=8)
        ctk.CTkButton(card, text="Положить картинку", command=lambda item=block["id"]: self.pick_image(item)).pack(anchor="w", padx=10, pady=(0, 8))

    def _button_body(self, card: ctk.CTkFrame, block: dict) -> None:
        color = block.get("color") or "#c45c26"
        style = block.get("style") or "fill"
        fg = color if style == "fill" else "#fffaf3"
        text_color = "white" if style == "fill" else color
        ctk.CTkButton(
            card,
            text=block.get("text") or "Кнопка",
            fg_color=fg,
            text_color=text_color,
            border_width=2 if style == "outline" else 0,
            border_color=color,
            corner_radius=999 if block.get("shape") == "pill" else 6,
            height={"sm": 28, "lg": 48}.get(block.get("size"), 36),
        ).pack(anchor="w", padx=10, pady=6)
        label = ctk.CTkEntry(card, fg_color="#fffaf3", text_color="#1c140f")
        label.insert(0, block.get("text") or "")
        label.pack(fill="x", padx=10, pady=2)
        label.bind("<FocusOut>", lambda _event, item=block["id"], widget=label: self.commit(item, "text", widget.get()))
        href = ctk.CTkEntry(card, fg_color="#fffaf3", text_color="#1c140f")
        href.insert(0, block.get("href") or "index.html")
        href.pack(fill="x", padx=10, pady=(2, 8))
        href.bind("<FocusOut>", lambda _event, item=block["id"], widget=href: self.commit(item, "href", widget.get()))

    def _bind_drag(self, widget, block_id: str) -> None:
        widget.bind("<ButtonPress-1>", lambda _event, item=block_id: self._drag_start(item))
        widget.bind("<B1-Motion>", self._drag_motion)
        widget.bind("<ButtonRelease-1>", self._drag_drop)

    def _drag_start(self, block_id: str) -> None:
        self._drag_id = block_id
        self.doc.selected = block_id

    def _drag_motion(self, event) -> None:
        if not self._drag_id and not self._drag_kind:
            return
        index = self._index_at(event.y_root)
        self._show_placeholder(index)
        label = REGISTRY.get(self._drag_kind or "", {}).get("label", "блок")
        self.status.configure(text=f"Отпусти — {label} встанет на место {index + 1}")

    def _drag_drop(self, event) -> None:
        if not self._drag_id:
            return
        index = self._index_at(event.y_root)
        self.doc.move_to(self._drag_id, index)
        self._drag_id = None
        self._clear_placeholder()
        self._persist()

    def _palette_start(self, kind: str) -> None:
        self._drag_kind = kind
        self._drag_id = None

    def _palette_drop(self, event) -> None:
        kind = self._drag_kind
        self._drag_kind = None
        self._clear_placeholder()
        if not kind:
            return
        if self._over_paper(event.y_root):
            self.doc.insert_at(kind, self._index_at(event.y_root))
        else:
            self.doc.add(kind)
        self._persist()

    def _over_paper(self, y_root: int) -> bool:
        top = self.paper.winfo_rooty()
        return top <= y_root <= top + max(self.paper.winfo_height(), 40)

    def _show_placeholder(self, index: int) -> None:
        if self.placeholder is None:
            self.placeholder = ctk.CTkFrame(self.paper, height=28, fg_color="#c45c26")
        self.placeholder.pack_forget()
        cards = [card for card in self._cards if card.winfo_exists()]
        if not cards or index >= len(cards):
            self.placeholder.pack(fill="x", padx=18, pady=4)
        else:
            self.placeholder.pack(fill="x", padx=18, pady=4, before=cards[index])

    def _clear_placeholder(self) -> None:
        if self.placeholder is not None:
            self.placeholder.pack_forget()

    def _index_at(self, y_root: int) -> int:
        if not self._cards:
            return 0
        for index, card in enumerate(self._cards):
            if y_root < card.winfo_rooty() + card.winfo_height() / 2:
                return index
        return len(self._cards) - 1

    def select(self, block_id: str) -> None:
        self.doc.selected = block_id
        self.refresh()

    def add(self, kind: str) -> None:
        self.doc.add(kind)
        self._persist()

    def remove(self, block_id: str) -> None:
        self.doc.selected = block_id
        self.doc.delete()
        self._persist()

    def commit(self, block_id: str, key: str, value: str) -> None:
        self.doc.selected = block_id
        self.doc.update(key, value)
        save_project(self.folder, self.doc.project)
        if key == "text" and self.doc.block() and self.doc.block().get("type") == "button":
            self.refresh()

    def pick_image(self, block_id: str) -> None:
        src = filedialog.askopenfilename(filetypes=[("Картинки", "*.png *.jpg *.jpeg *.webp *.bmp *.gif")])
        if not src:
            return
        self.doc.selected = block_id
        self.doc.update("image", add_image(self.folder, src, "canvas"))
        self._persist()

    def preview(self) -> None:
        save_project(self.folder, self.doc.project)
        self.render_html()
        self.status.configure(text="HTML уже в правом окне, браузер не вызывали.")

    def export(self) -> None:
        save_project(self.folder, self.doc.project)
        folder = filedialog.askdirectory(title="Куда выгрузить холст")
        if not folder:
            return
        result = export_project(self.folder, Path(folder) / "site")
        messagebox.showinfo("Пульт", f"Сайт: {result['folder']}\nZIP: {result['zip']}")

    def _persist(self) -> None:
        save_project(self.folder, self.doc.project)
        self.refresh()
