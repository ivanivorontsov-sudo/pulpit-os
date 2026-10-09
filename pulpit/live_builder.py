"""Живой локальный конструктор: HTML и CSS правятся, кадр обновляется сразу."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from pulpit.engines.converters import pack_zip
from pulpit.engines.images import store_image
from pulpit.engines.preview_doc import standalone
from pulpit.html_view import HtmlPane


DEFAULT_CSS = """
body { margin: 0; background: #f4efe6; color: #1c140f; font-family: Georgia, serif; }
header, main, footer { width: min(880px, calc(100% - 32px)); margin: 0 auto; }
header { padding: 36px 0 12px; border-bottom: 3px solid #1c140f; }
h1 { font-size: 42px; margin: 8px 0; }
.mark { color: #c45c26; letter-spacing: 2px; text-transform: uppercase; font-size: 12px; }
img { max-width: 100%; border: 1px solid #1c140f; }
.button { display: inline-block; background: #c45c26; color: white; padding: 10px 16px; text-decoration: none; }
.cards { display: block; }
.cards article { border: 1px solid #1c140f; padding: 12px; margin: 8px 0; }
"""

DEFAULT_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>Локальный сайт</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <p class="mark">локальный конструктор</p>
    <h1>Страница, которую видно сразу</h1>
    <p>Правь HTML слева. Стили и картинки живут в этом же окне.</p>
  </header>
  <main>
    <p>Абзац можно заменить. Картинку вставляй кнопкой, не заклинанием.</p>
    <p><a class="button" href="index.html">Кнопка</a></p>
  </main>
</body>
</html>
"""


class LiveBuilder(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.folder = Path.home() / "PulpitSites" / "live"
        self.folder.mkdir(parents=True, exist_ok=True)
        (self.folder / "assets").mkdir(exist_ok=True)
        self.pages = [{"title": "Главная", "html": DEFAULT_HTML}]
        self.css = DEFAULT_CSS
        self.index = 0
        self._job = None
        self._load()
        self._build()
        self._show_page()

    def _build(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=10, pady=(8, 4))
        ctk.CTkLabel(bar, text="Живой конструктор", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        ctk.CTkButton(bar, text="Картинка", width=100, command=self.insert_image).pack(side="left", padx=8)
        ctk.CTkButton(bar, text="Секция", width=80, command=lambda: self.insert(_section())).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="Кнопка", width=80, command=lambda: self.insert(_button())).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="ZIP", width=60, command=self.export).pack(side="right", padx=4)
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=8, pady=6)
        body.grid_columnconfigure(1, weight=1)
        body.grid_columnconfigure(2, weight=1)
        body.grid_rowconfigure(0, weight=1)
        side = ctk.CTkFrame(body, width=160)
        side.grid(row=0, column=0, sticky="nsew", padx=4)
        ctk.CTkButton(side, text="Новая страница", command=self.add_page).pack(fill="x", padx=8, pady=8)
        self.page_box = ctk.CTkScrollableFrame(side, label_text="Страницы")
        self.page_box.pack(fill="both", expand=True, padx=6, pady=6)
        editors = ctk.CTkFrame(body, fg_color="transparent")
        editors.grid(row=0, column=1, sticky="nsew", padx=4)
        editors.grid_rowconfigure(1, weight=1)
        editors.grid_rowconfigure(3, weight=1)
        editors.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(editors, text="HTML").grid(row=0, column=0, sticky="w")
        self.html = ctk.CTkTextbox(editors)
        self.html.grid(row=1, column=0, sticky="nsew")
        self.html.bind("<KeyRelease>", self._schedule)
        ctk.CTkLabel(editors, text="CSS").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.css_box = ctk.CTkTextbox(editors, height=140)
        self.css_box.grid(row=3, column=0, sticky="nsew")
        self.css_box.bind("<KeyRelease>", self._schedule)
        self.preview = HtmlPane(body)
        self.preview.grid(row=0, column=2, sticky="nsew", padx=4)
        self.status = ctk.CTkLabel(self, text="")
        self.status.pack(anchor="w", padx=12, pady=(0, 6))

    def _show_page(self) -> None:
        for child in self.page_box.winfo_children():
            child.destroy()
        for index, page in enumerate(self.pages):
            ctk.CTkButton(
                self.page_box,
                text=page.get("title") or f"Страница {index + 1}",
                fg_color="#3a2c22" if index == self.index else "transparent",
                command=lambda i=index: self.select_page(i),
            ).pack(fill="x", pady=2)
        self.html.delete("1.0", "end")
        self.html.insert("1.0", self.pages[self.index].get("html") or "")
        self.css_box.delete("1.0", "end")
        self.css_box.insert("1.0", self.css)
        self.render()

    def select_page(self, index: int) -> None:
        self._pull()
        self.index = index
        self._show_page()

    def add_page(self) -> None:
        self._pull()
        self.pages.append({"title": f"Страница {len(self.pages) + 1}", "html": DEFAULT_HTML.replace("Страница, которую видно сразу", f"Страница {len(self.pages) + 1}")})
        self.index = len(self.pages) - 1
        self._show_page()

    def insert_image(self) -> None:
        src = filedialog.askopenfilename(filetypes=[("Картинки", "*.png *.jpg *.jpeg *.webp *.gif *.bmp")])
        if not src:
            return
        name = store_image(src, self.folder / "assets", Path(src).stem)
        self.insert(f'<figure><img src="assets/{name}" alt="{Path(src).stem}"></figure>\n')
        self.render()

    def insert(self, snippet: str) -> None:
        self.html.insert("insert", snippet)
        self._schedule()

    def _schedule(self, _event=None) -> None:
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(250, self.render)

    def render(self) -> None:
        self._pull()
        self._save()
        document = standalone(self.pages[self.index]["html"], self.css, self.folder)
        self.preview.show_html(document)
        self.status.configure(text="Кадр обновлён. Стили внутри страницы, картинки вшиты.")

    def export(self) -> None:
        self._pull()
        folder = filedialog.askdirectory(title="Куда выгрузить сайт")
        if not folder:
            return
        out = Path(folder) / "site"
        if out.exists():
            shutil.rmtree(out)
        (out / "images").mkdir(parents=True)
        assets = self.folder / "assets"
        if assets.is_dir():
            for path in assets.iterdir():
                if path.is_file():
                    shutil.copy2(path, out / "images" / path.name)
        (out / "style.css").write_text(self.css, encoding="utf-8")
        for index, page in enumerate(self.pages):
            name = "index.html" if index == 0 else f"page-{index}.html"
            html = page["html"].replace("assets/", "images/")
            (out / name).write_text(html, encoding="utf-8")
        archive = pack_zip(out, out.parent / "site.zip")
        messagebox.showinfo("Пульт", f"Сайт: {out}\nZIP: {archive}")

    def _pull(self) -> None:
        self.pages[self.index]["html"] = self.html.get("1.0", "end").strip()
        self.css = self.css_box.get("1.0", "end").strip()
        title = _title(self.pages[self.index]["html"])
        if title:
            self.pages[self.index]["title"] = title

    def _save(self) -> None:
        payload = {"css": self.css, "pages": self.pages}
        (self.folder / "live.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> None:
        path = self.folder / "live.json"
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        self.css = payload.get("css") or DEFAULT_CSS
        self.pages = payload.get("pages") or self.pages


def _title(html: str) -> str:
    start = html.lower().find("<h1>")
    end = html.lower().find("</h1>")
    if start >= 0 and end > start:
        return html[start + 4:end].strip()
    return ""


def _section() -> str:
    return "<section><h2>Новая секция</h2><p>Текст секции.</p></section>\n"


def _button() -> str:
    return '<p><a class="button" href="index.html">Новая кнопка</a></p>\n'
