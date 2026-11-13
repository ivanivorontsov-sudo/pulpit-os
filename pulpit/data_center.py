"""Рабочий стол преобразования таблиц, JSON, XML, архивов и кодировок."""

from __future__ import annotations

import csv
import json
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from pulpit.engines import converters


class DataCenter(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.current_path: Path | None = None
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Данные и архивы", font=ctk.CTkFont(size=26, weight="bold")).pack(anchor="w", padx=24, pady=(20, 0))
        ctk.CTkLabel(self, text="JSON, CSV, XML, ZIP и кодировки. Не заставляем Excel читать JSON по фотографии.", text_color="#c9b8a6").pack(anchor="w", padx=24, pady=(0, 10))
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=18, pady=8)
        for name in ("JSON / CSV / XML", "Архивы", "Кодировки"):
            self.tabs.add(name)
        self._build_data_tab(self.tabs.tab("JSON / CSV / XML"))
        self._build_archive_tab(self.tabs.tab("Архивы"))
        self._build_encoding_tab(self.tabs.tab("Кодировки"))

    def _build_data_tab(self, tab) -> None:
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=(5, 8))
        for label, callback in [
            ("Открыть файл", self.open_data), ("Проверить JSON", self.validate_json),
            ("Форматировать JSON", self.format_json), ("Сжать JSON", self.minify_json),
        ]:
            ctk.CTkButton(row, text=label, command=callback).pack(side="left", padx=3)
        self.data_text = ctk.CTkTextbox(tab, height=300, font=ctk.CTkFont(family="Consolas", size=13))
        self.data_text.pack(fill="both", expand=True, pady=4)
        self.data_text.insert("1.0", '{\n  "пример": "Открой JSON, CSV или XML",\n  "число": 42\n}')
        actions = ctk.CTkFrame(tab, fg_color="transparent")
        actions.pack(fill="x", pady=5)
        for label, callback in [
            ("JSON → CSV", lambda: self.convert_data("json", "csv")),
            ("CSV → JSON", lambda: self.convert_data("csv", "json")),
            ("JSON → XML", lambda: self.convert_data("json", "xml")),
            ("XML → JSON", lambda: self.convert_data("xml", "json")),
            ("Сохранить результат", self.save_data),
        ]:
            ctk.CTkButton(actions, text=label, command=callback).pack(side="left", padx=3)
        self.data_status = ctk.CTkLabel(tab, text="Готов к работе", anchor="w", justify="left")
        self.data_status.pack(fill="x", pady=5)

    def _build_archive_tab(self, tab) -> None:
        ctk.CTkLabel(tab, text="Упаковка и распаковка ZIP", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", pady=8)
        ctk.CTkLabel(tab, text="Перед извлечением Пульт проверяет пути, символические ссылки и размер архива. Архив не сможет вылезти наружу, как кот из переноски.", wraplength=760, justify="left").pack(anchor="w", pady=4)
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=10)
        ctk.CTkButton(row, text="Папка → ZIP", command=self.pack_folder).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Посмотреть ZIP", command=self.inspect_archive).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Безопасно распаковать ZIP", command=self.unpack_archive).pack(side="left", padx=4)
        self.archive_log = ctk.CTkTextbox(tab, height=250)
        self.archive_log.pack(fill="both", expand=True, pady=8)

    def _build_encoding_tab(self, tab) -> None:
        ctk.CTkLabel(tab, text="Перекодировка текста", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", pady=8)
        ctk.CTkLabel(tab, text="Помогает исправить старые файлы в Windows-1251, UTF-8 и других кодировках. Исходник не перезаписывается.", wraplength=760, justify="left").pack(anchor="w")
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=12)
        self.encoding_from = ctk.CTkComboBox(row, values=["utf-8", "utf-8-sig", "cp1251", "cp866", "koi8-r", "latin-1"], width=150)
        self.encoding_from.set("utf-8")
        self.encoding_from.pack(side="left", padx=4)
        ctk.CTkLabel(row, text="→").pack(side="left", padx=4)
        self.encoding_to = ctk.CTkComboBox(row, values=["utf-8", "utf-8-sig", "cp1251", "cp866", "koi8-r", "latin-1"], width=150)
        self.encoding_to.set("cp1251")
        self.encoding_to.pack(side="left", padx=4)
        ctk.CTkButton(row, text="Выбрать и перекодировать", command=self.recode).pack(side="left", padx=8)
        self.encoding_log = ctk.CTkLabel(tab, text="Выбери файл для перекодировки.", anchor="w", justify="left")
        self.encoding_log.pack(fill="x", pady=8)

    def _replace_data(self, content: str) -> None:
        self.data_text.delete("1.0", "end")
        self.data_text.insert("1.0", content)

    def _content(self) -> str:
        return self.data_text.get("1.0", "end-1c")

    def open_data(self) -> None:
        picked = filedialog.askopenfilename(filetypes=[
            ("Данные", "*.json *.csv *.xml *.tsv *.txt"),
            ("JSON", "*.json"), ("CSV / TSV", "*.csv *.tsv"), ("XML", "*.xml"), ("Все файлы", "*.*")
        ])
        if not picked:
            return
        path = Path(picked)
        try:
            content = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            content = path.read_text(encoding="cp1251")
        self.current_path = path
        self._replace_data(content)
        self.data_status.configure(text=f"Открыт: {path} · {path.stat().st_size:,} байт")

    def validate_json(self) -> None:
        valid, message = converters.validate_json(self._content())
        self.data_status.configure(text=("✓ " if valid else "✕ ") + message)

    def format_json(self) -> None:
        try:
            self._replace_data(converters.json_format(self._content(), indent=2))
            self.data_status.configure(text="JSON отформатирован и проверен.")
        except (ValueError, TypeError) as exc:
            messagebox.showerror("Проверка JSON", str(exc))

    def minify_json(self) -> None:
        try:
            self._replace_data(converters.json_format(self._content(), indent=None))
            self.data_status.configure(text="JSON сжат до компактного вида.")
        except (ValueError, TypeError) as exc:
            messagebox.showerror("Проверка JSON", str(exc))

    def convert_data(self, source_kind: str, target_kind: str) -> None:
        content = self._content()
        try:
            with tempfile.TemporaryDirectory(prefix="pulpit-data-") as folder:
                source = Path(folder) / f"input.{source_kind}"
                target = Path(folder) / f"output.{target_kind}"
                source.write_text(content, encoding="utf-8-sig")
                if (source_kind, target_kind) == ("json", "csv"):
                    converters.json_to_csv(source, target, delimiter=";")
                elif (source_kind, target_kind) == ("csv", "json"):
                    converters.csv_to_json(source, target)
                elif (source_kind, target_kind) == ("json", "xml"):
                    converters.json_to_xml(source, target)
                else:
                    converters.xml_to_json(source, target)
                result = target.read_text(encoding="utf-8-sig")
            self._replace_data(result)
            self.current_path = None
            self.data_status.configure(text=f"Готово: {source_kind.upper()} → {target_kind.upper()}. Сохрани результат в отдельный файл.")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Преобразование данных", str(exc))

    def save_data(self) -> None:
        dest = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("JSON", "*.json"), ("CSV", "*.csv"), ("XML", "*.xml"), ("Текст", "*.txt"), ("Все файлы", "*.*")]
        )
        if not dest:
            return
        path = Path(dest)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self._content(), encoding="utf-8-sig" if path.suffix.lower() in {".csv", ".tsv"} else "utf-8")
            self.data_status.configure(text=f"Сохранено: {path} · {path.stat().st_size:,} байт")
        except OSError as exc:
            messagebox.showerror("Сохранение", str(exc))

    def pack_folder(self) -> None:
        folder = filedialog.askdirectory(title="Папка для упаковки")
        if not folder:
            return
        dest = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("ZIP", "*.zip")])
        if not dest:
            return
        try:
            path = converters.pack_zip(folder, dest)
            self.archive_log.insert("end", f"Создан архив: {path}\nРазмер: {path.stat().st_size:,} байт\n\n")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("ZIP", str(exc))

    def inspect_archive(self) -> None:
        picked = filedialog.askopenfilename(filetypes=[("ZIP", "*.zip")])
        if not picked:
            return
        try:
            info = converters.inspect_zip(picked)
            lines = [
                f"Файлов: {info['files']}", f"Папок: {info['folders']}",
                f"После распаковки: {info['uncompressed_bytes']:,} байт",
                f"Размер архива: {info['compressed_bytes']:,} байт", "", "Содержимое:"
            ] + list(info["names"])
            self.archive_log.insert("end", "\n".join(lines) + "\n\n")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("ZIP", str(exc))

    def unpack_archive(self) -> None:
        picked = filedialog.askopenfilename(filetypes=[("ZIP", "*.zip")])
        if not picked:
            return
        dest = filedialog.askdirectory(title="Куда распаковать")
        if not dest:
            return
        try:
            folder = converters.unpack_zip(picked, dest)
            self.archive_log.insert("end", f"Распаковано безопасно: {folder}\n\n")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Безопасная распаковка", str(exc))

    def recode(self) -> None:
        picked = filedialog.askopenfilename(title="Исходный текст")
        if not picked:
            return
        source = Path(picked)
        dest = filedialog.asksaveasfilename(initialfile=source.stem + "-recode.txt", defaultextension=".txt")
        if not dest:
            return
        try:
            path = converters.recode_text(source, dest, self.encoding_from.get(), self.encoding_to.get())
            self.encoding_log.configure(text=f"Перекодировано: {path}\nИсходный файл оставлен без изменений.")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Перекодировка", str(exc))
