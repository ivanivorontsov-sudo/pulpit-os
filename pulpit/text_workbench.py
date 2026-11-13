"""Редактор текста с открытием, сохранением, преобразованиями и Markdown."""

from __future__ import annotations

import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from pulpit.engines import editors


class TextWorkbench(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.current_path: Path | None = None
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Редакторы текста", font=ctk.CTkFont(size=26, weight="bold")).pack(anchor="w", padx=24, pady=(20, 0))
        ctk.CTkLabel(self, text="Текстовый редактор, Markdown, поиск и замена, очистка, сравнение файлов.", text_color="#c9b8a6").pack(anchor="w", padx=24)
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=8)
        for label, callback in [("Открыть", self.open_file), ("Сохранить", self.save_file), ("Сохранить как", self.save_as), ("Markdown → HTML", self.export_markdown), ("Сравнить с файлом", self.compare_file)]:
            ctk.CTkButton(top, text=label, command=callback).pack(side="left", padx=3)
        tools = ctk.CTkFrame(self, fg_color="transparent")
        tools.pack(fill="x", padx=20, pady=4)
        self.transform = ctk.CTkComboBox(
            tools,
            width=205,
            values=["ВЕРХНИЙ РЕГИСТР", "нижний регистр", "Заглавные слова", "Предложение", "Обрезать края строк", "Свернуть пробелы", "Удалить пустые строки", "Сортировать строки", "Убрать повторы строк", "Нормализовать переносы"],
        )
        self.transform.set("Обрезать края строк")
        self.transform.pack(side="left", padx=3)
        ctk.CTkButton(tools, text="Применить", command=self.apply_transform).pack(side="left", padx=3)
        self.search = ctk.CTkEntry(tools, width=180, placeholder_text="Найти")
        self.search.pack(side="left", padx=(12, 3))
        self.replace = ctk.CTkEntry(tools, width=180, placeholder_text="Заменить на")
        self.replace.pack(side="left", padx=3)
        self.regex = ctk.CTkCheckBox(tools, text="Regex")
        self.regex.pack(side="left", padx=4)
        self.ignore_case = ctk.CTkCheckBox(tools, text="Без регистра")
        self.ignore_case.select()
        self.ignore_case.pack(side="left", padx=4)
        ctk.CTkButton(tools, text="Заменить всё", command=self.replace_all, width=105).pack(side="left", padx=3)
        self.editor = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Consolas", size=14), wrap="word")
        self.editor.pack(fill="both", expand=True, padx=24, pady=8)
        self.editor.insert("1.0", "# Добро пожаловать в редактор\n\nМожно открыть TXT, MD, HTML, JSON, CSV, Python и другие текстовые файлы.\n\n**Markdown** можно экспортировать в автономную HTML-страницу.")
        self.editor.bind("<KeyRelease>", self.update_stats)
        self.status = ctk.CTkLabel(self, text="Новый документ · не сохранён", anchor="w", justify="left")
        self.status.pack(fill="x", padx=24, pady=(0, 12))
        self.update_stats()

    def content(self) -> str:
        return self.editor.get("1.0", "end-1c")

    def replace_content(self, text: str) -> None:
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", text)
        self.update_stats()

    def open_file(self) -> None:
        picked = filedialog.askopenfilename(filetypes=[
            ("Текстовые файлы", "*.txt *.md *.markdown *.html *.htm *.json *.csv *.xml *.py *.js *.css *.log *.ini *.yaml *.yml"),
            ("Все файлы", "*.*")
        ])
        if not picked:
            return
        path = Path(picked)
        try:
            try:
                text = path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                text = path.read_text(encoding="cp1251")
            self.current_path = path
            self.replace_content(text)
            self.status.configure(text=f"{path} · открыт")
        except (OSError, UnicodeError) as exc:
            messagebox.showerror("Открытие файла", str(exc))

    def save_file(self) -> None:
        if self.current_path is None:
            self.save_as()
            return
        try:
            editors.save_text(self.current_path, self.content())
            self.status.configure(text=f"Сохранено: {self.current_path}")
        except OSError as exc:
            messagebox.showerror("Сохранение", str(exc))

    def save_as(self) -> None:
        dest = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Текст", "*.txt"), ("Markdown", "*.md"), ("HTML", "*.html"), ("Все файлы", "*.*")]
        )
        if not dest:
            return
        self.current_path = Path(dest)
        self.save_file()

    def apply_transform(self) -> None:
        modes = {
            "ВЕРХНИЙ РЕГИСТР": "upper", "нижний регистр": "lower",
            "Заглавные слова": "title", "Предложение": "sentence",
            "Обрезать края строк": "trim", "Свернуть пробелы": "collapse_spaces",
            "Удалить пустые строки": "remove_blank", "Сортировать строки": "sort_lines",
            "Убрать повторы строк": "unique_lines", "Нормализовать переносы": "normalize_newlines",
        }
        try:
            self.replace_content(editors.transform_text(self.content(), modes[self.transform.get()]))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Преобразование текста", str(exc))

    def replace_all(self) -> None:
        try:
            text, count = editors.find_replace(
                self.content(), self.search.get(), self.replace.get(),
                regex=bool(self.regex.get()), ignore_case=bool(self.ignore_case.get()),
            )
            self.replace_content(text)
            self.status.configure(text=f"Заменено совпадений: {count}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Поиск и замена", str(exc))

    def export_markdown(self) -> None:
        dest = filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("HTML", "*.html")])
        if not dest:
            return
        try:
            path = editors.save_text(dest, editors.markdown_to_html(self.content()))
            webbrowser.open(path.resolve().as_uri())
            self.status.configure(text=f"HTML экспортирован и открыт: {path}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Экспорт Markdown", str(exc))

    def compare_file(self) -> None:
        picked = filedialog.askopenfilename(title="Второй файл для сравнения", filetypes=[("Текст", "*.txt *.md *.py *.json *.csv *.html *.css *.js"), ("Все файлы", "*.*")])
        if not picked:
            return
        try:
            other = Path(picked).read_text(encoding="utf-8-sig")
            diff = editors.compare_text(self.content(), other, "Текущий документ", Path(picked).name)
            window = ctk.CTkToplevel(self)
            window.title("Сравнение текстов")
            window.geometry("850x600")
            view = ctk.CTkTextbox(window, font=ctk.CTkFont(family="Consolas", size=13))
            view.pack(fill="both", expand=True, padx=12, pady=12)
            view.insert("1.0", diff or "Различий нет.")
            view.configure(state="disabled")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Сравнение", str(exc))

    def update_stats(self, _event=None) -> None:
        info = editors.text_stats(self.content())
        name = self.current_path.name if self.current_path else "Новый документ"
        self.status.configure(
            text=f"{name} · слов: {info['words']} · символов: {info['symbols']} · строк: {info['lines']} · абзацев: {info['paragraphs']} · чтение: ~{info['reading_minutes']} мин"
        )
