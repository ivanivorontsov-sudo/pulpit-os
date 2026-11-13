"""Интерфейс встроенного офиса Пульта: Word, Excel, презентации и конвертация."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

import customtkinter as ctk
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from pulpit.engines import office_suite


class OfficeWorkbench(ctk.CTkFrame):
    """Отдельная офисная рабочая область внутри основного окна Пульта."""

    def __init__(self, master: Any) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self,
            text="Пульт Office",
            font=ctk.CTkFont(size=27, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(16, 2))
        ctk.CTkLabel(
            self,
            text="Три редактора документов в одном окне. Файлы обрабатываются на этом компьютере.",
            text_color="#c9b8a6",
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(52, 8))

        self.tabs = ctk.CTkTabview(self, corner_radius=10)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))
        self.tabs.add("Word")
        self.tabs.add("Excel")
        self.tabs.add("PowerPoint")
        self.tabs.add("Форматы и PDF")
        self._build_word(self.tabs.tab("Word"))
        self._build_excel(self.tabs.tab("Excel"))
        self._build_powerpoint(self.tabs.tab("PowerPoint"))
        self._build_file_tools(self.tabs.tab("Форматы и PDF"))

    def _status(self, parent: Any, text: str = "Готово") -> ctk.CTkLabel:
        label = ctk.CTkLabel(parent, text=text, text_color="#c9b8a6", anchor="w", justify="left")
        label.pack(fill="x", padx=10, pady=(4, 8))
        return label

    def _button_row(self, parent: Any) -> ctk.CTkFrame:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=5)
        return row

    # ------------------------------------------------------------------ Word
    def _build_word(self, tab: Any) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)
        self.word_path: Path | None = None

        metadata = ctk.CTkFrame(tab, fg_color="transparent")
        metadata.pack(fill="x", padx=8, pady=(8, 2))
        self.word_title = ctk.CTkEntry(metadata, placeholder_text="Название документа")
        self.word_title.pack(side="left", fill="x", expand=True, padx=3)
        self.word_title.insert(0, "Новый документ")
        self.word_author = ctk.CTkEntry(metadata, placeholder_text="Автор (необязательно)", width=180)
        self.word_author.pack(side="left", padx=3)

        row = self._button_row(tab)
        for label, action in [
            ("Новый", self._word_new), ("Открыть DOCX", self._word_open),
            ("Сохранить", self._word_save), ("Сохранить как…", self._word_save_as),
            ("Экспорт PDF", self._word_pdf),
        ]:
            ctk.CTkButton(row, text=label, command=action, width=118).pack(side="left", padx=3)

        format_row = self._button_row(tab)
        for label, prefix, suffix in [
            ("Заголовок 1", "# ", ""), ("Заголовок 2", "## ", ""),
            ("Маркированный список", "- ", ""), ("Нумерованный", "1. ", ""),
            ("Цитата", "> ", ""), ("Жирный", "**", "**"),
            ("Курсив", "*", "*"), ("Код", chr(96), chr(96)),
        ]:
            ctk.CTkButton(
                format_row, text=label, width=114,
                command=lambda a=prefix, b=suffix: self._word_wrap_selection(a, b),
            ).pack(side="left", padx=2)

        self.word_editor = ctk.CTkTextbox(tab, wrap="word", font=ctk.CTkFont(family="Aptos", size=14))
        self.word_editor.pack(fill="both", expand=True, padx=10, pady=6)
        self.word_editor.insert(
            "1.0",
            "Начни писать здесь.\n\n"
            "# Заголовок первого уровня\n"
            "Обычный абзац с **жирным**, *курсивом* и коротким фрагментом кода.\n\n"
            "## Список\n"
            "- Первый пункт\n- Второй пункт\n\n"
            "| Наименование | Количество |\n| --- | --- |\n| Карандаши | 12 |\n| Блокноты | 5 |\n\n"
            "> Пример цитаты.\n\n"
            "Таблицы можно создавать текстом через вертикальные черты; при сохранении они станут настоящими таблицами Word.",
        )
        self.word_status = self._status(tab, "Форматирование задаётся панелью и простыми маркерами. DOCX сохраняет абзацы, таблицы и основные стили.")

    def _word_wrap_selection(self, prefix: str, suffix: str) -> None:
        try:
            start = self.word_editor.index("sel.first")
            end = self.word_editor.index("sel.last")
            selected = self.word_editor.get(start, end)
            self.word_editor.delete(start, end)
            self.word_editor.insert(start, prefix + selected + suffix)
            self.word_editor.mark_set("insert", f"{start}+{len(prefix + selected + suffix)}c")
        except tk.TclError:
            self.word_editor.insert("insert", prefix)

    def _word_new(self) -> None:
        self.word_path = None
        self.word_title.delete(0, "end")
        self.word_title.insert(0, "Новый документ")
        self.word_author.delete(0, "end")
        self.word_editor.delete("1.0", "end")
        self.word_editor.insert("1.0", "# Новый документ\n\nНачни писать здесь.")
        self.word_status.configure(text="Создан новый документ. Пока только в памяти — сохрани его в DOCX.")

    def _word_open(self) -> None:
        picked = filedialog.askopenfilename(
            filetypes=[("Документы Word", "*.docx"), ("Все файлы", "*.*")]
        )
        if not picked:
            return
        try:
            path = Path(picked)
            text = office_suite.read_word_document(path)
            metadata = office_suite.word_metadata(path)
            self.word_editor.delete("1.0", "end")
            self.word_editor.insert("1.0", text)
            self.word_title.delete(0, "end")
            self.word_title.insert(0, str(metadata["title"]))
            self.word_author.delete(0, "end")
            self.word_author.insert(0, str(metadata["author"]))
            self.word_path = path
            self.word_status.configure(
                text=f"Открыт {path.name}. Абзацы: {metadata['paragraphs']}, таблицы: {metadata['tables']}. "
                     "При повторном сохранении поддерживаемая структура будет пересоздана.",
            )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Word — ошибка открытия", str(exc))

    def _word_save_to(self, path: str | Path) -> None:
        result = office_suite.create_word_document(
            path,
            self.word_title.get().strip() or "Документ Пульта",
            self.word_editor.get("1.0", "end-1c"),
            author=self.word_author.get().strip(),
        )
        self.word_path = result
        self.word_status.configure(text=f"Сохранено: {result} · {result.stat().st_size:,} байт")

    def _word_save(self) -> None:
        if self.word_path is None:
            self._word_save_as()
            return
        try:
            self._word_save_to(self.word_path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Word — ошибка сохранения", str(exc))

    def _word_save_as(self) -> None:
        picked = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[("Документ Word", "*.docx")],
            initialfile=(self.word_title.get().strip() or "Документ") + ".docx",
        )
        if not picked:
            return
        try:
            self._word_save_to(picked)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Word — ошибка сохранения", str(exc))

    def _word_pdf(self) -> None:
        if self.word_path is None or not self.word_path.is_file():
            self._word_save_as()
        if self.word_path is None or not self.word_path.is_file():
            return
        self._convert_file_to("pdf", self.word_path)

    # ------------------------------------------------------------------ Excel
    def _build_excel(self, tab: Any) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)
        self.xlsx_book: Any | None = None
        self.xlsx_path: Path | None = None
        self.xlsx_sheet = ""

        row = self._button_row(tab)
        actions = [
            ("Новая книга", self._excel_new), ("Открыть", self._excel_open),
            ("Сохранить", self._excel_save), ("Сохранить как…", self._excel_save_as),
            ("Импорт CSV", self._excel_import_csv), ("Экспорт CSV", self._excel_export_csv),
        ]
        for label, action in actions:
            ctk.CTkButton(row, text=label, width=106, command=action).pack(side="left", padx=2)

        sheet_row = self._button_row(tab)
        self.xlsx_sheet_select = ctk.CTkComboBox(sheet_row, values=["Лист1"], width=180, command=self._excel_sheet_changed)
        self.xlsx_sheet_select.pack(side="left", padx=3)
        for label, action in [
            ("Добавить лист", self._excel_add_sheet),
            ("Переименовать", self._excel_rename_sheet),
            ("Удалить лист", self._excel_delete_sheet),
            ("Добавить строку", self._excel_add_row),
            ("Добавить столбец", self._excel_add_column),
            ("Оформить заголовки", self._excel_format_headers),
            ("Диаграмма", self._excel_chart),
        ]:
            ctk.CTkButton(sheet_row, text=label, width=105, command=action).pack(side="left", padx=2)

        grid = ctk.CTkFrame(tab, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=10, pady=4)
        grid.grid_rowconfigure(0, weight=1)
        grid.grid_columnconfigure(0, weight=1)
        style = ttk.Style()
        try:
            style.configure("Pulpit.Treeview", rowheight=27, font=("Segoe UI", 10))
            style.configure("Pulpit.Treeview.Heading", font=("Segoe UI", 10, "bold"))
        except tk.TclError:
            pass
        self.xlsx_tree = ttk.Treeview(grid, show="headings", style="Pulpit.Treeview")
        yscroll = ttk.Scrollbar(grid, orient="vertical", command=self.xlsx_tree.yview)
        xscroll = ttk.Scrollbar(grid, orient="horizontal", command=self.xlsx_tree.xview)
        self.xlsx_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.xlsx_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        self.xlsx_tree.bind("<ButtonRelease-1>", self._excel_pick_cell)

        edit_row = self._button_row(tab)
        self.xlsx_cell_label = ctk.CTkLabel(edit_row, text="Ячейка A1", width=86)
        self.xlsx_cell_label.pack(side="left", padx=3)
        self.xlsx_cell_value = ctk.CTkEntry(edit_row, placeholder_text="Значение или формула, например =SUM(B2:B8)")
        self.xlsx_cell_value.pack(side="left", fill="x", expand=True, padx=3)
        ctk.CTkButton(edit_row, text="Применить значение", command=self._excel_apply_cell, width=150).pack(side="left", padx=3)
        ctk.CTkButton(edit_row, text="Закрепить первую строку", command=self._excel_freeze, width=165).pack(side="left", padx=3)
        self.xlsx_status = self._status(tab, "Открой XLSX/XLSM или создай новую книгу. Двойного щелчка для редактирования не требуется: выбери ячейку, измени значение ниже и нажми «Применить».")

        self.xlsx_book = Workbook()
        self.xlsx_sheet = self.xlsx_book.active.title
        self._excel_refresh()

    def _excel_new(self) -> None:
        self.xlsx_book = Workbook()
        self.xlsx_path = None
        self.xlsx_sheet = self.xlsx_book.active.title
        self._excel_refresh()
        self.xlsx_status.configure(text="Новая пустая книга. Сохрани её как XLSX.")

    def _excel_open(self) -> None:
        picked = filedialog.askopenfilename(
            filetypes=[("Книги Excel", "*.xlsx *.xlsm"), ("Все файлы", "*.*")]
        )
        if not picked:
            return
        try:
            self.xlsx_book = office_suite.open_excel_workbook(picked)
            self.xlsx_path = Path(picked)
            self.xlsx_sheet = self.xlsx_book.active.title
            self._excel_refresh()
            self.xlsx_status.configure(text=f"Открыта {self.xlsx_path.name}. Формулы отображаются как формулы; пересчёт выполняет Excel или LibreOffice.")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Excel — ошибка открытия", str(exc))

    def _excel_save(self) -> None:
        if self.xlsx_book is None:
            return
        if self.xlsx_path is None:
            self._excel_save_as()
            return
        try:
            path = office_suite.save_excel_workbook(self.xlsx_book, self.xlsx_path)
            self.xlsx_status.configure(text=f"Сохранено: {path} · {path.stat().st_size:,} байт")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Excel — ошибка сохранения", str(exc))

    def _excel_save_as(self) -> None:
        if self.xlsx_book is None:
            return
        picked = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Книга Excel", "*.xlsx"), ("Книга с макросами", "*.xlsm")],
        )
        if not picked:
            return
        try:
            path = office_suite.save_excel_workbook(self.xlsx_book, picked)
            self.xlsx_path = path
            self.xlsx_status.configure(text=f"Сохранено: {path} · {path.stat().st_size:,} байт")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Excel — ошибка сохранения", str(exc))

    def _excel_refresh(self) -> None:
        if self.xlsx_book is None:
            return
        names = self.xlsx_book.sheetnames
        self.xlsx_sheet_select.configure(values=names)
        if self.xlsx_sheet not in names:
            self.xlsx_sheet = names[0]
        self.xlsx_sheet_select.set(self.xlsx_sheet)
        snapshot = office_suite.excel_sheet_snapshot(self.xlsx_book, self.xlsx_sheet)
        rows = snapshot["rows"]
        column_count = max(1, min(snapshot["max_column"], 24))
        columns = [f"c{index}" for index in range(1, column_count + 1)]
        self.xlsx_tree.delete(*self.xlsx_tree.get_children())
        self.xlsx_tree.configure(columns=columns)
        for index, column in enumerate(columns, start=1):
            letter = get_column_letter(index)
            self.xlsx_tree.heading(column, text=letter)
            self.xlsx_tree.column(column, width=135, minwidth=70, stretch=True, anchor="w")
        for row_index, values in enumerate(rows, start=1):
            display = []
            for value in values[:column_count]:
                if value is None:
                    display.append("")
                elif isinstance(value, float):
                    display.append(f"{value:g}")
                else:
                    display.append(str(value))
            display.extend([""] * (column_count - len(display)))
            self.xlsx_tree.insert("", "end", iid=str(row_index), values=display)
        note = f"Лист «{self.xlsx_sheet}» · строк: {snapshot['max_row']} · столбцов: {snapshot['max_column']}"
        if snapshot["truncated"]:
            note += " · показана верхняя часть (до 250 × 24)"
        if snapshot["freeze_panes"]:
            note += f" · закрепление: {snapshot['freeze_panes']}"
        self.xlsx_status.configure(text=note)

    def _excel_sheet_changed(self, name: str) -> None:
        if self.xlsx_book is None or name not in self.xlsx_book.sheetnames:
            return
        self.xlsx_sheet = name
        self._excel_refresh()

    def _excel_pick_cell(self, event: Any) -> None:
        if self.xlsx_book is None:
            return
        row_id = self.xlsx_tree.identify_row(event.y)
        column_id = self.xlsx_tree.identify_column(event.x)
        if not row_id or not column_id or not column_id.startswith("#"):
            return
        try:
            row_number = int(row_id)
            column_number = int(column_id[1:])
            if row_number < 1 or column_number < 1:
                return
            ref = f"{get_column_letter(column_number)}{row_number}"
            value = self.xlsx_book[self.xlsx_sheet][ref].value
            self.xlsx_cell_label.configure(text=f"Ячейка {ref}")
            self.xlsx_cell_value.delete(0, "end")
            if value is not None:
                self.xlsx_cell_value.insert(0, str(value))
        except (ValueError, IndexError):
            return

    def _excel_apply_cell(self) -> None:
        if self.xlsx_book is None:
            return
        ref = self.xlsx_cell_label.cget("text").replace("Ячейка ", "")
        try:
            office_suite.set_excel_cell(self.xlsx_book, self.xlsx_sheet, ref, self.xlsx_cell_value.get())
            self._excel_refresh()
            self.xlsx_status.configure(text=f"Изменена ячейка {self.xlsx_sheet}!{ref}. Не забудь сохранить книгу.")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Excel — ошибка изменения ячейки", str(exc))

    def _excel_add_row(self) -> None:
        if self.xlsx_book is None:
            return
        sheet = self.xlsx_book[self.xlsx_sheet]
        office_suite.append_excel_row(self.xlsx_book, self.xlsx_sheet, [None] * max(1, sheet.max_column))
        self._excel_refresh()

    def _excel_add_column(self) -> None:
        if self.xlsx_book is None:
            return
        sheet = self.xlsx_book[self.xlsx_sheet]
        column = sheet.max_column + 1
        sheet.cell(row=1, column=column, value=f"Столбец {column}")
        office_suite.format_excel_header(self.xlsx_book, self.xlsx_sheet)
        self._excel_refresh()

    def _excel_add_sheet(self) -> None:
        if self.xlsx_book is None:
            return
        dialog = ctk.CTkInputDialog(text="Название нового листа:", title="Добавить лист")
        name = dialog.get_input()
        if not name:
            return
        try:
            self.xlsx_sheet = office_suite.add_excel_sheet(self.xlsx_book, name)
            self._excel_refresh()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Excel — лист", str(exc))

    def _excel_rename_sheet(self) -> None:
        if self.xlsx_book is None:
            return
        dialog = ctk.CTkInputDialog(text="Новое название листа:", title="Переименовать лист")
        name = dialog.get_input()
        if not name:
            return
        try:
            self.xlsx_sheet = office_suite.rename_excel_sheet(self.xlsx_book, self.xlsx_sheet, name)
            self._excel_refresh()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Excel — лист", str(exc))

    def _excel_delete_sheet(self) -> None:
        if self.xlsx_book is None:
            return
        if not messagebox.askyesno("Удалить лист", f"Удалить лист «{self.xlsx_sheet}»?"):
            return
        try:
            office_suite.delete_excel_sheet(self.xlsx_book, self.xlsx_sheet)
            self.xlsx_sheet = self.xlsx_book.active.title
            self._excel_refresh()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Excel — лист", str(exc))

    def _excel_format_headers(self) -> None:
        if self.xlsx_book is None:
            return
        office_suite.format_excel_header(self.xlsx_book, self.xlsx_sheet)
        self._excel_refresh()
        self.xlsx_status.configure(text="Оформлены заголовки, включён автофильтр и закреплена первая строка.")

    def _excel_freeze(self) -> None:
        if self.xlsx_book is None:
            return
        self.xlsx_book[self.xlsx_sheet].freeze_panes = "A2"
        self._excel_refresh()

    def _excel_chart(self) -> None:
        if self.xlsx_book is None:
            return
        try:
            office_suite.add_excel_chart(self.xlsx_book, self.xlsx_sheet, chart_type="bar")
            self._excel_refresh()
            self.xlsx_status.configure(text="Добавлена столбчатая диаграмма по столбцам A и B. Сохрани книгу.")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Excel — диаграмма", str(exc))

    def _excel_import_csv(self) -> None:
        if self.xlsx_book is None:
            return
        picked = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("Все файлы", "*.*")])
        if not picked:
            return
        try:
            self.xlsx_sheet = office_suite.import_csv_to_workbook(self.xlsx_book, picked)
            self._excel_refresh()
            self.xlsx_status.configure(text=f"CSV импортирован в новый лист «{self.xlsx_sheet}».")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Excel — импорт CSV", str(exc))

    def _excel_export_csv(self) -> None:
        if self.xlsx_book is None:
            return
        picked = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not picked:
            return
        try:
            path = office_suite.export_excel_sheet_csv(self.xlsx_book, self.xlsx_sheet, picked)
            self.xlsx_status.configure(text=f"Экспортировано: {path}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Excel — экспорт CSV", str(exc))

    # ------------------------------------------------------------- PowerPoint
    def _build_powerpoint(self, tab: Any) -> None:
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        self.ppt_path: Path | None = None
        self.ppt_slides: list[dict[str, str]] = []

        row = self._button_row(tab)
        for label, action in [
            ("Новая презентация", self._ppt_new), ("Открыть PPTX", self._ppt_open),
            ("Сохранить", self._ppt_save), ("Сохранить как…", self._ppt_save_as),
            ("Экспорт PDF", self._ppt_pdf),
        ]:
            ctk.CTkButton(row, text=label, width=130, command=action).pack(side="left", padx=3)

        workarea = ctk.CTkFrame(tab, fg_color="transparent")
        workarea.pack(fill="both", expand=True, padx=8, pady=5)
        workarea.grid_columnconfigure(1, weight=1)
        workarea.grid_rowconfigure(0, weight=1)
        left = ctk.CTkFrame(workarea, width=220, fg_color="#2b211a", corner_radius=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        left.grid_propagate(False)
        ctk.CTkLabel(left, text="Слайды", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=10, pady=8)
        self.ppt_listbox = tk.Listbox(
            left, bg="#211a15", fg="#f4e9df", selectbackground="#76503b",
            selectforeground="#ffffff", relief="flat", highlightthickness=0,
            font=("Segoe UI", 10), activestyle="none",
        )
        self.ppt_listbox.pack(fill="both", expand=True, padx=8, pady=4)
        self.ppt_listbox.bind("<<ListboxSelect>>", self._ppt_select)
        buttons = ctk.CTkFrame(left, fg_color="transparent")
        buttons.pack(fill="x", padx=4, pady=6)
        for label, action in [
            ("Добавить", self._ppt_add), ("Удалить", self._ppt_remove),
            ("↑", lambda: self._ppt_move(-1)), ("↓", lambda: self._ppt_move(1)),
        ]:
            ctk.CTkButton(buttons, text=label, width=48, command=action).pack(side="left", padx=2)

        editor = ctk.CTkFrame(workarea, fg_color="transparent")
        editor.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        editor.grid_columnconfigure(0, weight=1)
        editor.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(editor, text="Заголовок слайда", anchor="w").grid(row=0, column=0, sticky="ew", pady=(4, 2))
        self.ppt_title = ctk.CTkEntry(editor, placeholder_text="Заголовок")
        self.ppt_title.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(editor, text="Текст и пункты (каждый с новой строки)", anchor="w").grid(row=2, column=0, sticky="new")
        self.ppt_body = ctk.CTkTextbox(editor, wrap="word", font=ctk.CTkFont(size=14))
        self.ppt_body.grid(row=3, column=0, sticky="nsew", pady=5)
        editor.grid_rowconfigure(3, weight=1)
        ctk.CTkButton(editor, text="Применить изменения к выбранному слайду", command=self._ppt_update).grid(row=4, column=0, sticky="e", pady=5)
        self.ppt_status = self._status(tab, "Слайды можно добавлять, удалять, переставлять и редактировать. Сохраняется настоящий PPTX.")

        self._ppt_new()

    def _ppt_render_list(self, select_index: int | None = None) -> None:
        self.ppt_listbox.delete(0, "end")
        for index, slide in enumerate(self.ppt_slides, start=1):
            title = slide.get("title", "").strip() or "Без заголовка"
            self.ppt_listbox.insert("end", f"{index:02d}. {title}")
        if self.ppt_slides:
            index = 0 if select_index is None else max(0, min(select_index, len(self.ppt_slides) - 1))
            self.ppt_listbox.selection_clear(0, "end")
            self.ppt_listbox.selection_set(index)
            self.ppt_listbox.activate(index)
            self._ppt_load_editor(index)
        else:
            self.ppt_title.delete(0, "end")
            self.ppt_body.delete("1.0", "end")

    def _ppt_load_editor(self, index: int) -> None:
        slide = self.ppt_slides[index]
        self.ppt_title.delete(0, "end")
        self.ppt_title.insert(0, slide.get("title", ""))
        self.ppt_body.delete("1.0", "end")
        self.ppt_body.insert("1.0", slide.get("body", ""))

    def _ppt_select(self, _event: Any = None) -> None:
        selection = self.ppt_listbox.curselection()
        if selection:
            self._ppt_load_editor(selection[0])

    def _ppt_update(self) -> None:
        selection = self.ppt_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        self.ppt_slides[index] = {
            "title": self.ppt_title.get().strip() or "Слайд",
            "body": self.ppt_body.get("1.0", "end-1c"),
        }
        self._ppt_render_list(index)
        self.ppt_status.configure(text=f"Изменён слайд {index + 1}. Сохрани презентацию.")

    def _ppt_add(self) -> None:
        self.ppt_slides.append({"title": f"Новый слайд {len(self.ppt_slides) + 1}", "body": ""})
        self._ppt_render_list(len(self.ppt_slides) - 1)
        self.ppt_title.focus_set()

    def _ppt_remove(self) -> None:
        selection = self.ppt_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        del self.ppt_slides[index]
        self._ppt_render_list(max(0, index - 1))
        self.ppt_status.configure(text="Слайд удалён. Сохрани презентацию.")

    def _ppt_move(self, offset: int) -> None:
        selection = self.ppt_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        target = index + offset
        if target < 0 or target >= len(self.ppt_slides):
            return
        self.ppt_slides[index], self.ppt_slides[target] = self.ppt_slides[target], self.ppt_slides[index]
        self._ppt_render_list(target)

    def _ppt_new(self) -> None:
        self.ppt_path = None
        self.ppt_slides = [
            {"title": "О проекте", "body": "Ключевая мысль презентации\n- Первый тезис\n- Второй тезис"},
        ]
        self._ppt_render_list(0)
        self.ppt_status.configure(text="Создана новая презентация. Добавляй слайды и сохраняй в PPTX.")

    def _ppt_open(self) -> None:
        picked = filedialog.askopenfilename(filetypes=[("Презентации PowerPoint", "*.pptx")])
        if not picked:
            return
        try:
            self.ppt_slides = office_suite.read_presentation(picked)
            self.ppt_path = Path(picked)
            self._ppt_render_list(0)
            self.ppt_status.configure(text=f"Открыто слайдов: {len(self.ppt_slides)} · {self.ppt_path.name}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("PowerPoint — ошибка открытия", str(exc))

    def _ppt_save_to(self, path: str | Path) -> None:
        self._ppt_update()
        result = office_suite.create_presentation(
            path,
            "Презентация Пульта",
            self.ppt_slides,
        )
        self.ppt_path = result
        self.ppt_status.configure(text=f"Сохранено: {result} · слайдов с титульным: {len(self.ppt_slides) + 1}")

    def _ppt_save(self) -> None:
        if self.ppt_path is None:
            self._ppt_save_as()
            return
        try:
            self._ppt_save_to(self.ppt_path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("PowerPoint — ошибка сохранения", str(exc))

    def _ppt_save_as(self) -> None:
        picked = filedialog.asksaveasfilename(
            defaultextension=".pptx", filetypes=[("Презентация PowerPoint", "*.pptx")]
        )
        if not picked:
            return
        try:
            self._ppt_save_to(picked)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("PowerPoint — ошибка сохранения", str(exc))

    def _ppt_pdf(self) -> None:
        if self.ppt_path is None or not self.ppt_path.is_file():
            self._ppt_save_as()
        if self.ppt_path is None or not self.ppt_path.is_file():
            return
        self._convert_file_to("pdf", self.ppt_path)

    # ---------------------------------------------------------- File formats
    def _build_file_tools(self, tab: Any) -> None:
        tab.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tab, text="Центр форматов", font=ctk.CTkFont(size=21, weight="bold")).pack(anchor="w", padx=16, pady=(16, 4))
        ctk.CTkLabel(
            tab,
            text="Конвертация в PDF и открытые форматы через установленный LibreOffice. Это дополнительный движок, встроенный офис без него тоже работает.",
            text_color="#c9b8a6", wraplength=760, justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 14))
        self.file_path_entry = ctk.CTkEntry(tab, placeholder_text="Выбери DOC/DOCX, XLS/XLSX, PPT/PPTX, ODT/ODS/ODP или PDF")
        self.file_path_entry.pack(fill="x", padx=16, pady=5)
        row = self._button_row(tab)
        ctk.CTkButton(row, text="Выбрать файл…", command=self._file_browse).pack(side="left", padx=3)
        ctk.CTkButton(row, text="Открыть в системе", command=self._file_open_external).pack(side="left", padx=3)
        self.file_format = ctk.CTkComboBox(row, values=["pdf", "docx", "xlsx", "pptx", "odt", "ods", "odp"], width=110)
        self.file_format.set("pdf")
        self.file_format.pack(side="left", padx=10)
        ctk.CTkButton(row, text="Преобразовать", command=self._file_convert).pack(side="left", padx=3)
        backend = "LibreOffice найден — доступны PDF и конвертация форматов." if office_suite.libreoffice_available() else "LibreOffice не найден. Встроенные редакторы работают; для PDF/старых форматов установи LibreOffice."
        self.file_status = self._status(tab, backend)
        ctk.CTkLabel(
            tab,
            text="Поддержка встроенного редактирования: DOCX, XLSX/XLSM, PPTX. Старые DOC/XLS/PPT и ODT/ODS/ODP доступны через LibreOffice, если он установлен.",
            text_color="#c9b8a6", wraplength=760, justify="left",
        ).pack(anchor="w", padx=16, pady=12)

    def _file_browse(self) -> None:
        picked = filedialog.askopenfilename(
            filetypes=[
                ("Документы и таблицы", "*.doc *.docx *.xls *.xlsx *.xlsm *.ppt *.pptx *.odt *.ods *.odp *.pdf"),
                ("Все файлы", "*.*"),
            ]
        )
        if picked:
            self.file_path_entry.delete(0, "end")
            self.file_path_entry.insert(0, picked)

    def _file_open_external(self) -> None:
        picked = self.file_path_entry.get().strip()
        if not picked:
            self._file_browse()
            picked = self.file_path_entry.get().strip()
        if not picked:
            return
        try:
            self.file_status.configure(text=office_suite.open_with_associated_app(picked))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Открытие файла", str(exc))

    def _file_convert(self) -> None:
        picked = self.file_path_entry.get().strip()
        if not picked:
            self._file_browse()
            picked = self.file_path_entry.get().strip()
        if not picked:
            return
        self._convert_file_to(self.file_format.get(), Path(picked))

    def _convert_file_to(self, output_format: str, source: Path) -> None:
        if not source.is_file():
            messagebox.showerror("Конвертация", "Сначала сохрани документ и выбери существующий файл.")
            return
        try:
            result = office_suite.convert_with_libreoffice(source, output_format)
            self.file_status.configure(text=f"Создано: {result} · {result.stat().st_size:,} байт")
            messagebox.showinfo("Конвертация завершена", f"Файл создан:\n{result}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Конвертация", str(exc))
