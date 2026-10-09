"""Интерактивный редактор сайта: страницы, блоки, картинки, предпросмотр, zip."""

from __future__ import annotations

import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from pulpit.engines.site_project import add_image, blank_block, blank_page, load_project, new_project, save_project
from pulpit.engines.site_render import export_project, preview_html

BLOCK_TYPES = ["hero", "text", "image", "gallery", "quote", "columns", "button"]


class SiteStudio(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.folder = Path.home() / "PulpitSites" / "draft"
        self.folder.mkdir(parents=True, exist_ok=True)
        self.project = new_project()
        self.page_index = 0
        if (self.folder / "project.json").exists():
            try:
                self.project = load_project(self.folder)
            except Exception:
                self.project = new_project()
        self._build()
        self.refresh()

    def _build(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(top, text="Редактор сайта", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkButton(top, text="Сохранить", width=110, command=self.save).pack(side="right", padx=4)
        ctk.CTkButton(top, text="Предпросмотр", width=120, command=self.preview).pack(side="right", padx=4)
        ctk.CTkButton(top, text="ZIP", width=70, command=self.export).pack(side="right", padx=4)
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=8)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        self.pages = ctk.CTkScrollableFrame(body, width=180, label_text="Страницы")
        self.pages.grid(row=0, column=0, sticky="nsew", padx=4)
        self.canvas = ctk.CTkScrollableFrame(body, label_text="Блоки")
        self.canvas.grid(row=0, column=1, sticky="nsew", padx=4)
        side = ctk.CTkFrame(body, width=240)
        side.grid(row=0, column=2, sticky="nsew", padx=4)
        self.title = ctk.CTkEntry(side, placeholder_text="Название сайта")
        self.title.pack(fill="x", padx=10, pady=(12, 4))
        self.tagline = ctk.CTkEntry(side, placeholder_text="Подзаголовок")
        self.tagline.pack(fill="x", padx=10, pady=4)
        self.accent = ctk.CTkEntry(side, placeholder_text="#c45c26")
        self.accent.pack(fill="x", padx=10, pady=4)
        ctk.CTkButton(side, text="Новая страница", command=self.add_page).pack(fill="x", padx=10, pady=(12, 4))
        self.block_kind = ctk.CTkComboBox(side, values=BLOCK_TYPES)
        self.block_kind.set("text")
        self.block_kind.pack(fill="x", padx=10, pady=4)
        ctk.CTkButton(side, text="Добавить блок", command=self.add_block).pack(fill="x", padx=10, pady=4)
        ctk.CTkButton(side, text="Открыть проект", command=self.open_folder).pack(fill="x", padx=10, pady=(16, 4))
        self.status = ctk.CTkLabel(side, text="", wraplength=210, justify="left")
        self.status.pack(fill="x", padx=10, pady=8)

    def refresh(self) -> None:
        self.title.delete(0, "end")
        self.title.insert(0, self.project.get("title") or "")
        self.tagline.delete(0, "end")
        self.tagline.insert(0, self.project.get("tagline") or "")
        self.accent.delete(0, "end")
        self.accent.insert(0, self.project.get("accent") or "#c45c26")
        for child in self.pages.winfo_children():
            child.destroy()
        for index, page in enumerate(self.project["pages"]):
            ctk.CTkButton(
                self.pages,
                text=page.get("title") or f"Страница {index + 1}",
                fg_color="#3a2c22" if index == self.page_index else "transparent",
                command=lambda i=index: self.select_page(i),
            ).pack(fill="x", pady=3)
        for child in self.canvas.winfo_children():
            child.destroy()
        page = self.current()
        for index, block in enumerate(page["blocks"]):
            self._block_card(index, block)
        self.status.configure(text=f"Проект: {self.folder}")

    def _block_card(self, index: int, block: dict) -> None:
        card = ctk.CTkFrame(self.canvas)
        card.pack(fill="x", pady=6, padx=4)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(head, text=block.get("type", "text")).pack(side="left")
        ctk.CTkButton(head, text="вверх", width=60, command=lambda i=index: self.move(i, -1)).pack(side="right", padx=2)
        ctk.CTkButton(head, text="вниз", width=60, command=lambda i=index: self.move(i, 1)).pack(side="right", padx=2)
        ctk.CTkButton(head, text="убрать", width=70, command=lambda i=index: self.delete(i)).pack(side="right", padx=2)
        text = ctk.CTkTextbox(card, height=70)
        text.pack(fill="x", padx=8, pady=4)
        text.insert("1.0", block.get("text") or "")
        text.bind("<KeyRelease>", lambda _event, i=index, widget=text: self._set(i, "text", widget.get("1.0", "end").strip()))
        if block.get("type") in {"hero", "columns"}:
            sub = ctk.CTkEntry(card)
            sub.insert(0, block.get("sub") or "")
            sub.pack(fill="x", padx=8, pady=4)
            sub.bind("<KeyRelease>", lambda _event, i=index, widget=sub: self._set(i, "sub", widget.get()))
        if block.get("type") == "image":
            ctk.CTkButton(card, text="Выбрать картинку", command=lambda i=index: self.pick_image(i)).pack(anchor="w", padx=8, pady=4)
            ctk.CTkLabel(card, text=block.get("image") or "файл не выбран").pack(anchor="w", padx=8, pady=(0, 8))
        if block.get("type") == "gallery":
            ctk.CTkButton(card, text="Добавить в галерею", command=lambda i=index: self.pick_gallery(i)).pack(anchor="w", padx=8, pady=4)
            ctk.CTkLabel(card, text="\n".join(block.get("images") or []) or "галерея пустая").pack(anchor="w", padx=8, pady=(0, 8))
        if block.get("type") == "button":
            href = ctk.CTkEntry(card)
            href.insert(0, block.get("href") or "index.html")
            href.pack(fill="x", padx=8, pady=(0, 8))
            href.bind("<KeyRelease>", lambda _event, i=index, widget=href: self._set(i, "href", widget.get()))
        title = ctk.CTkEntry(card, placeholder_text="имя страницы")
        if index == 0:
            title.insert(0, self.current().get("title") or "")
            title.pack(fill="x", padx=8, pady=(0, 8))
            title.bind("<KeyRelease>", lambda _event, widget=title: self.rename_page(widget.get()))

    def current(self) -> dict:
        return self.project["pages"][self.page_index]

    def select_page(self, index: int) -> None:
        self._pull_meta()
        self.page_index = index
        self.refresh()

    def add_page(self) -> None:
        self._pull_meta()
        self.project["pages"].append(blank_page(f"Страница {len(self.project['pages']) + 1}"))
        self.page_index = len(self.project["pages"]) - 1
        self.save(quiet=True)
        self.refresh()

    def add_block(self) -> None:
        self.current()["blocks"].append(blank_block(self.block_kind.get()))
        self.save(quiet=True)
        self.refresh()

    def move(self, index: int, delta: int) -> None:
        blocks = self.current()["blocks"]
        target = index + delta
        if 0 <= target < len(blocks):
            blocks[index], blocks[target] = blocks[target], blocks[index]
            self.refresh()

    def delete(self, index: int) -> None:
        del self.current()["blocks"][index]
        self.refresh()

    def rename_page(self, title: str) -> None:
        self.current()["title"] = title or "Страница"

    def pick_image(self, index: int) -> None:
        src = filedialog.askopenfilename(filetypes=[("Картинки", "*.png *.jpg *.jpeg *.webp *.bmp *.gif")])
        if not src:
            return
        try:
            rel = add_image(self.folder, src, f"block-{index + 1}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Пульт", f"Картинка не сохранилась: {exc}")
            return
        self._set(index, "image", rel)
        self.save(quiet=True)
        self.refresh()
        messagebox.showinfo("Пульт", f"Картинка лежит в проекте:\n{rel}")

    def pick_gallery(self, index: int) -> None:
        picked = filedialog.askopenfilenames(filetypes=[("Картинки", "*.png *.jpg *.jpeg *.webp *.bmp *.gif")])
        images = list(self.current()["blocks"][index].get("images") or [])
        for number, src in enumerate(picked, start=len(images) + 1):
            images.append(add_image(self.folder, src, f"gallery-{number}"))
        self._set(index, "images", images)
        self.save(quiet=True)
        self.refresh()

    def preview(self) -> None:
        self.save(quiet=True)
        html = preview_html(self.project, self.page_index, self.folder)
        target = self.folder / "preview.html"
        target.write_text(html, encoding="utf-8")
        webbrowser.open(target.resolve().as_uri())
        self.status.configure(text=f"Предпросмотр: {target}")

    def export(self) -> None:
        self.save(quiet=True)
        folder = filedialog.askdirectory(title="Куда выгрузить сайт")
        if not folder:
            return
        result = export_project(self.folder, Path(folder) / "site")
        messagebox.showinfo("Пульт", f"Сайт: {result['folder']}\nZIP: {result['zip']}\nКартинок внутри: {result['images']}")

    def open_folder(self) -> None:
        folder = filedialog.askdirectory(title="Папка проекта")
        if not folder:
            return
        self.folder = Path(folder)
        self.project = load_project(self.folder) if (self.folder / "project.json").exists() else new_project()
        self.page_index = 0
        self.refresh()

    def save(self, quiet: bool = False) -> None:
        self._pull_meta()
        path = save_project(self.folder, self.project)
        self.status.configure(text=f"Сохранено: {path}")
        if not quiet:
            messagebox.showinfo("Пульт", f"Проект записан:\n{path}")

    def _pull_meta(self) -> None:
        self.project["title"] = self.title.get()
        self.project["tagline"] = self.tagline.get()
        self.project["accent"] = self.accent.get() or "#c45c26"

    def _set(self, index: int, key: str, value) -> None:
        self.current()["blocks"][index][key] = value
