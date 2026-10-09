"""Три панели конструктора: палитра, слои, свойства. Холст не хранит вёрстку."""

from __future__ import annotations

import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from pulpit.engines.constructor import REGISTRY, TEMPLATES, Constructor
from pulpit.engines.site_project import add_image, load_project, save_project
from pulpit.engines.site_render import export_project, preview_html


class ConstructorView(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.folder = Path.home() / "PulpitSites" / "constructor"
        self.folder.mkdir(parents=True, exist_ok=True)
        project = load_project(self.folder) if (self.folder / "project.json").exists() else None
        self.doc = Constructor(project)
        self._fields: dict[str, ctk.CTkTextbox] = {}
        self._build()
        self.refresh()

    def _build(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(bar, text="Конструктор", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        self.template = ctk.CTkComboBox(bar, values=list(TEMPLATES), width=140)
        self.template.set("landing")
        self.template.pack(side="left", padx=12)
        ctk.CTkButton(bar, text="Шаблон", width=90, command=self.apply_template).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Назад", width=70, command=self.undo).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Вперёд", width=80, command=self.redo).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="ZIP", width=60, command=self.export).pack(side="right", padx=4)
        ctk.CTkButton(bar, text="Просмотр", width=100, command=self.preview).pack(side="right", padx=4)
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=8, pady=8)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        self.palette = ctk.CTkScrollableFrame(body, width=170, label_text="Палитра")
        self.palette.grid(row=0, column=0, sticky="nsew", padx=4)
        self.layers = ctk.CTkScrollableFrame(body, label_text="Слои")
        self.layers.grid(row=0, column=1, sticky="nsew", padx=4)
        self.inspector = ctk.CTkScrollableFrame(body, width=250, label_text="Свойства")
        self.inspector.grid(row=0, column=2, sticky="nsew", padx=4)
        for kind, spec in REGISTRY.items():
            ctk.CTkButton(self.palette, text=spec["label"], command=lambda name=kind: self.insert(name)).pack(fill="x", pady=3)
        self.status = ctk.CTkLabel(self, text="")
        self.status.pack(anchor="w", padx=16, pady=(0, 8))

    def refresh(self) -> None:
        for child in self.layers.winfo_children():
            child.destroy()
        for index, block in enumerate(self.doc.page()["blocks"]):
            selected = block["id"] == self.doc.selected
            ctk.CTkButton(
                self.layers,
                text=f"{index + 1}. {REGISTRY.get(block['type'], {}).get('label', block['type'])}",
                fg_color="#3a2c22" if selected else "transparent",
                command=lambda item=block["id"]: self.select(item),
            ).pack(fill="x", pady=2)
        for child in self.inspector.winfo_children():
            child.destroy()
        self._fields.clear()
        block = self.doc.block()
        if not block:
            ctk.CTkLabel(self.inspector, text="Слой не выбран").pack(anchor="w", padx=8, pady=8)
        else:
            spec = REGISTRY.get(block["type"], REGISTRY["text"])
            ctk.CTkLabel(self.inspector, text=spec["label"], font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=6)
            for field in spec["fields"]:
                if field == "images":
                    ctk.CTkLabel(self.inspector, text="\n".join(block.get("images") or []) or "галерея пустая").pack(anchor="w", padx=8)
                    ctk.CTkButton(self.inspector, text="Добавить картинки", command=self.add_gallery).pack(fill="x", padx=8, pady=4)
                    continue
                if field == "image":
                    ctk.CTkLabel(self.inspector, text=block.get("image") or "файла нет").pack(anchor="w", padx=8)
                    ctk.CTkButton(self.inspector, text="Выбрать картинку", command=self.pick_image).pack(fill="x", padx=8, pady=4)
                box = ctk.CTkTextbox(self.inspector, height=68)
                box.pack(fill="x", padx=8, pady=4)
                box.insert("1.0", str(block.get(field) or ""))
                self._fields[field] = box
            ctk.CTkButton(self.inspector, text="Применить", command=self.apply_fields).pack(fill="x", padx=8, pady=4)
            row = ctk.CTkFrame(self.inspector, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=4)
            ctk.CTkButton(row, text="вверх", width=70, command=lambda: self.shift(-1)).pack(side="left", padx=2)
            ctk.CTkButton(row, text="вниз", width=70, command=lambda: self.shift(1)).pack(side="left", padx=2)
            ctk.CTkButton(self.inspector, text="Дублировать", command=self.duplicate).pack(fill="x", padx=8, pady=4)
            ctk.CTkButton(self.inspector, text="Удалить", command=self.remove).pack(fill="x", padx=8, pady=4)
        self.status.configure(text=f"{len(self.doc.page()['blocks'])} блоков · {self.folder}")

    def insert(self, kind: str) -> None:
        self.doc.add(kind)
        self._persist()

    def select(self, block_id: str) -> None:
        self.doc.selected = block_id
        self.refresh()

    def apply_fields(self) -> None:
        for key, widget in self._fields.items():
            self.doc.update(key, widget.get("1.0", "end").strip())
        self._persist()

    def pick_image(self) -> None:
        src = filedialog.askopenfilename(filetypes=[("Картинки", "*.png *.jpg *.jpeg *.webp *.bmp *.gif")])
        if not src:
            return
        rel = add_image(self.folder, src, "constructor")
        self.doc.update("image", rel)
        self._persist()
        messagebox.showinfo("Пульт", f"Картинка в проекте: {rel}")

    def add_gallery(self) -> None:
        picked = filedialog.askopenfilenames(filetypes=[("Картинки", "*.png *.jpg *.jpeg *.webp *.gif")])
        images = list((self.doc.block() or {}).get("images") or [])
        for number, src in enumerate(picked, start=len(images) + 1):
            images.append(add_image(self.folder, src, f"gallery-{number}"))
        self.doc.update("images", images)
        self._persist()

    def shift(self, delta: int) -> None:
        self.doc.move(delta)
        self._persist()

    def duplicate(self) -> None:
        self.doc.duplicate()
        self._persist()

    def remove(self) -> None:
        self.doc.delete()
        self._persist()

    def apply_template(self) -> None:
        self.doc.apply_template(self.template.get())
        self._persist()

    def undo(self) -> None:
        self.doc.undo()
        self._persist(history=False)

    def redo(self) -> None:
        self.doc.redo()
        self._persist(history=False)

    def preview(self) -> None:
        self.apply_fields()
        target = self.folder / "preview.html"
        target.write_text(preview_html(self.doc.project, self.doc.page_index, self.folder), encoding="utf-8")
        webbrowser.open(target.resolve().as_uri())

    def export(self) -> None:
        self.apply_fields()
        folder = filedialog.askdirectory(title="Куда выгрузить конструктор")
        if not folder:
            return
        result = export_project(self.folder, Path(folder) / "site")
        messagebox.showinfo("Пульт", f"Сайт: {result['folder']}\nZIP: {result['zip']}\nКартинок: {result['images']}")

    def _persist(self, history: bool = True) -> None:
        save_project(self.folder, self.doc.project)
        if not history:
            pass
        self.refresh()
