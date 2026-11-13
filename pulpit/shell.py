"""Главное окно Пульта и его рабочие разделы."""

from __future__ import annotations

import platform
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from pulpit import APP_NAME, __version__
from pulpit.data_center import DataCenter
from pulpit.engines import office_bridge, units
from pulpit.image_bench import ImageBench
from pulpit.live_builder import LiveBuilder
from pulpit.constructor_view import ConstructorView
from pulpit.system_info import format_snapshot
from pulpit.text_workbench import TextWorkbench

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class PulpitApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} {__version__} — рабочая панель Windows")
        self.geometry("1180x780")
        self.minsize(980, 660)
        self.configure(fg_color="#17130f")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._pages: dict[str, ctk.CTkFrame] = {}
        self._build_sidebar()
        self._build_pages()
        self.show("home")

    def _build_sidebar(self) -> None:
        side = ctk.CTkFrame(self, width=220, fg_color="#241c16", corner_radius=0)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)
        ctk.CTkLabel(side, text="ПУЛЬТ", font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w", padx=20, pady=(24, 0))
        ctk.CTkLabel(side, text=f"рабочая панель · {__version__}", text_color="#c9b8a6").pack(anchor="w", padx=20, pady=(0, 20))
        for key, label in [
            ("home", "Обзор"), ("convert", "Стол изображений"),
            ("data", "Данные и архивы"), ("edit", "Редакторы текста"),
            ("constructor", "Конструктор страниц"), ("live", "HTML / CSS"),
            ("office", "Документы Office"), ("units", "Конвертер единиц"),
            ("system", "Система и диагностика"),
        ]:
            ctk.CTkButton(
                side, text=label, anchor="w", height=38,
                fg_color="transparent", hover_color="#3a2c22",
                command=lambda name=key: self.show(name),
            ).pack(fill="x", padx=12, pady=3)

    def _build_pages(self) -> None:
        host = ctk.CTkFrame(self, fg_color="#17130f")
        host.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        host.grid_columnconfigure(0, weight=1)
        host.grid_rowconfigure(0, weight=1)
        builders = {
            "home": self._page_home, "convert": self._page_convert,
            "data": self._page_data, "edit": self._page_edit,
            "constructor": self._page_constructor, "live": self._page_live,
            "office": self._page_office, "units": self._page_units,
            "system": self._page_system,
        }
        for key, builder in builders.items():
            frame = ctk.CTkFrame(host, fg_color="#211a15")
            frame.grid(row=0, column=0, sticky="nsew")
            builder(frame)
            self._pages[key] = frame

    def show(self, name: str) -> None:
        self._pages[name].tkraise()

    def _page_home(self, frame: ctk.CTkFrame) -> None:
        self._title(frame, "Пульт — инструменты для повседневной работы", "Один интерфейс для изображений, файлов, текста, Office и диагностики.")
        cards = [
            ("Изображения", "Пакетная конвертация, изменение размера, водяные знаки и контактные листы.", "convert"),
            ("Данные и архивы", "JSON, CSV, XML, ZIP, таблицы и кодировки.", "data"),
            ("Редакторы текста", "Markdown, поиск и замена, преобразования, сравнение документов.", "edit"),
            ("Документы Office", "Создание и чтение DOCX, XLSX, PPTX без обязательного Microsoft Office.", "office"),
            ("Единицы измерения", "Длина, масса, площадь, объём, скорость, время, энергия, давление, температура и данные.", "units"),
            ("Диагностика", "Система, процессор, память, диск и состояние батареи.", "system"),
        ]
        for index, (heading, description, key) in enumerate(cards):
            card = ctk.CTkFrame(frame, fg_color="#2a211a", corner_radius=12)
            card.pack(fill="x", padx=24, pady=6)
            ctk.CTkLabel(card, text=heading, font=ctk.CTkFont(size=17, weight="bold")).pack(anchor="w", padx=14, pady=(10, 0))
            ctk.CTkLabel(card, text=description, text_color="#d0c0b2", justify="left", wraplength=720).pack(anchor="w", padx=14, pady=4)
            ctk.CTkButton(card, text="Открыть", width=100, command=lambda name=key: self.show(name)).pack(anchor="e", padx=12, pady=(0, 10))
        ctk.CTkButton(frame, text="Открыть конструктор страниц", command=lambda: self.show("constructor")).pack(anchor="w", padx=24, pady=8)
        ctk.CTkLabel(frame, text="Пульт работает локально: документы и изображения не отправляются на сторонний сервер.", text_color="#c9b8a6", wraplength=760, justify="left").pack(anchor="w", padx=24, pady=8)

    def _page_convert(self, frame: ctk.CTkFrame) -> None:
        ImageBench(frame)

    def _page_data(self, frame: ctk.CTkFrame) -> None:
        DataCenter(frame)

    def _page_edit(self, frame: ctk.CTkFrame) -> None:
        TextWorkbench(frame)

    def _page_live(self, frame: ctk.CTkFrame) -> None:
        LiveBuilder(frame)

    def _page_constructor(self, frame: ctk.CTkFrame) -> None:
        ConstructorView(frame)

    def _page_office(self, frame: ctk.CTkFrame) -> None:
        self._title(frame, "Документы Office", "Создавай, читай и передавай документы Word, Excel и PowerPoint.")
        title = ctk.CTkEntry(frame, placeholder_text="Название документа")
        title.pack(fill="x", padx=24, pady=5)
        title.insert(0, "Документ Пульта")
        body = ctk.CTkTextbox(frame, height=330, font=ctk.CTkFont(size=14))
        body.pack(fill="both", expand=True, padx=24, pady=8)
        body.insert("1.0", "Вставь сюда текст документа.\n\nЗаголовки Markdown вида # Заголовок и списки - пункт преобразуются в стили Word.\n\nДля таблицы Excel используй табуляцию между столбцами.")
        header_row = ctk.CTkFrame(frame, fg_color="transparent")
        header_row.pack(fill="x", padx=24, pady=4)
        use_header = ctk.CTkCheckBox(header_row, text="Первая строка — заголовки таблицы Excel")
        use_header.select()
        use_header.pack(side="left", padx=4)
        log = ctk.CTkLabel(frame, text="Файлы создаются локально в формате Open XML.", anchor="w", justify="left")
        log.pack(fill="x", padx=24, pady=4)

        def lines() -> list[str]:
            return [line for line in body.get("1.0", "end-1c").splitlines()]

        def save_docx() -> None:
            dest = filedialog.asksaveasfilename(defaultextension=".docx", filetypes=[("Word", "*.docx")])
            if not dest:
                return
            try:
                path = office_bridge.write_docx(dest, title.get(), lines())
                log.configure(text=f"DOCX создан: {path} · {path.stat().st_size:,} байт")
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("DOCX", str(exc))

        def save_xlsx() -> None:
            dest = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
            if not dest:
                return
            try:
                source_lines = [line for line in lines() if line.strip()]
                parsed = [line.split("\t") for line in source_lines]
                headers = bool(use_header.get())
                if len(parsed) == 1 and len(parsed[0]) == 1:
                    parsed = [["№", "Содержание"]] + [[str(i + 1), line] for i, line in enumerate(source_lines)]
                    headers = True
                path = office_bridge.write_xlsx(dest, title.get() or "Данные", parsed, headers=headers)
                log.configure(text=f"XLSX создан: {path} · строк: {len(parsed)} · {path.stat().st_size:,} байт")
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("XLSX", str(exc))

        def save_pptx() -> None:
            dest = filedialog.asksaveasfilename(defaultextension=".pptx", filetypes=[("PowerPoint", "*.pptx")])
            if not dest:
                return
            try:
                content = [line.strip() for line in lines() if line.strip()]
                slides = [(f"Раздел {i + 1}", line) for i, line in enumerate(content)]
                path = office_bridge.write_pptx(dest, title.get(), slides or [("Пустой слайд", "Добавь текст в редактор")])
                log.configure(text=f"PPTX создан: {path} · слайдов: {len(slides) + 1} · {path.stat().st_size:,} байт")
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("PPTX", str(exc))

        def import_office() -> None:
            picked = filedialog.askopenfilename(filetypes=[("Office", "*.docx *.xlsx *.pptx")])
            if not picked:
                return
            try:
                text = office_bridge.read_office(picked)
                body.delete("1.0", "end")
                body.insert("1.0", text)
                title.delete(0, "end")
                title.insert(0, Path(picked).stem)
                log.configure(text=f"Извлечено содержимое: {picked}")
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("Чтение Office", str(exc))

        def open_office() -> None:
            picked = filedialog.askopenfilename(filetypes=[("Office", "*.docx *.xlsx *.pptx")])
            if not picked:
                return
            try:
                log.configure(text=office_bridge.open_with_associated_app(picked))
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("Открытие Office", str(exc))

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=8)
        for label, command in [
            ("Импортировать Office", import_office), ("Создать DOCX", save_docx),
            ("Создать XLSX", save_xlsx), ("Создать PPTX", save_pptx),
            ("Открыть в Office", open_office),
        ]:
            ctk.CTkButton(row, text=label, command=command).pack(side="left", padx=3)

    def _page_units(self, frame: ctk.CTkFrame) -> None:
        self._title(frame, "Конвертер единиц", "Десять категорий: от миллиметров до гигабайтов и кельвинов.")
        self.unit_value = ctk.CTkEntry(frame, placeholder_text="Число")
        self.unit_value.pack(fill="x", padx=24, pady=8)
        self.unit_value.insert(0, "10")
        self.unit_category = ctk.CTkComboBox(frame, values=list(units.UNITS.keys()), command=self._change_unit_category)
        self.unit_category.set("Длина")
        self.unit_category.pack(fill="x", padx=24, pady=5)
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=8)
        self.unit_from = ctk.CTkComboBox(row, values=list(units.LENGTH.keys()), width=220)
        self.unit_from.set("м")
        self.unit_from.pack(side="left", padx=4)
        ctk.CTkButton(row, text="⇄", width=48, command=self._swap_units).pack(side="left", padx=4)
        self.unit_to = ctk.CTkComboBox(row, values=list(units.LENGTH.keys()), width=220)
        self.unit_to.set("фут")
        self.unit_to.pack(side="left", padx=4)
        ctk.CTkButton(frame, text="Преобразовать", command=self._convert_units).pack(anchor="w", padx=24, pady=6)
        self.unit_result = ctk.CTkTextbox(frame, height=270, font=ctk.CTkFont(family="Consolas", size=14))
        self.unit_result.pack(fill="both", expand=True, padx=24, pady=8)
        self.unit_result.insert("1.0", "Результат появится здесь. Можно вывести значение сразу во все единицы выбранной категории.")
        self.unit_all = ctk.CTkCheckBox(frame, text="Показать результат во всех единицах")
        self.unit_all.pack(anchor="w", padx=24, pady=4)

    def _change_unit_category(self, category: str) -> None:
        values = list(units.UNITS[category].keys()) if category != "Температура" else ["°C", "°F", "K"]
        self.unit_from.configure(values=values)
        self.unit_to.configure(values=values)
        self.unit_from.set(values[0])
        self.unit_to.set(values[1] if len(values) > 1 else values[0])

    def _swap_units(self) -> None:
        source, target = self.unit_from.get(), self.unit_to.get()
        self.unit_from.set(target)
        self.unit_to.set(source)

    def _convert_units(self) -> None:
        try:
            value = float(self.unit_value.get().replace(",", "."))
            category, source, target = self.unit_category.get(), self.unit_from.get(), self.unit_to.get()
            if self.unit_all.get():
                values = units.convert_all(value, category, source)
                output = "\n".join(f"{value:g} {source} = {result:.10g} {unit}" for unit, result in values.items())
            else:
                result = units.convert(value, category, source, target)
                output = f"{value:g} {source} = {result:.12g} {target}"
            self.unit_result.delete("1.0", "end")
            self.unit_result.insert("1.0", output)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Конвертер единиц", str(exc))

    def _page_system(self, frame: ctk.CTkFrame) -> None:
        self._title(frame, "Система и диагностика", "Сведения о системе, процессоре, памяти, диске и батарее.")
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=8)
        output = ctk.CTkTextbox(frame, font=ctk.CTkFont(family="Consolas", size=13))
        output.pack(fill="both", expand=True, padx=24, pady=8)

        def refresh() -> None:
            output.delete("1.0", "end")
            output.insert("1.0", format_snapshot())
            output.insert("end", "\n\nПоказатели обновлены. IP-адреса, серийные номера и содержимое пользовательских файлов не собираются.")

        def copy() -> None:
            self.clipboard_clear()
            self.clipboard_append(output.get("1.0", "end-1c"))

        ctk.CTkButton(row, text="Обновить диагностику", command=refresh).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Копировать отчёт", command=copy).pack(side="left", padx=4)
        refresh()

    def _title(self, frame: ctk.CTkFrame, title: str, subtitle: str) -> None:
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=26, weight="bold")).pack(anchor="w", padx=24, pady=(20, 0))
        ctk.CTkLabel(frame, text=subtitle, text_color="#c9b8a6", wraplength=820, justify="left").pack(anchor="w", padx=24, pady=(0, 8))


def main() -> None:
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ivanivorontsov.pulpit.os")
    except Exception:
        pass
    app = PulpitApp()
    app.mainloop()


if __name__ == "__main__":
    main()
