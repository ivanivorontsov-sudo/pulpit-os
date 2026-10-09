"""Окно Пульта. Не заменяет Windows 11, а садится сверху и делает полезное."""

from __future__ import annotations

import platform
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from pulpit import APP_NAME, __version__
from pulpit.engines import converters, editors, office_bridge, site_builder, units


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class PulpitApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} {__version__} — поверх Windows 11")
        self.geometry("1100x720")
        self.minsize(960, 640)
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
        ctk.CTkLabel(side, text="мини-оболочка Windows 11", text_color="#c9b8a6").pack(anchor="w", padx=20, pady=(0, 20))
        for key, label in [
            ("home", "Обзор"),
            ("convert", "Конвертеры"),
            ("edit", "Редакторы"),
            ("site", "Сайт в zip"),
            ("office", "Office"),
            ("units", "Единицы"),
            ("system", "Система"),
        ]:
            ctk.CTkButton(
                side,
                text=label,
                anchor="w",
                fg_color="transparent",
                hover_color="#3a2c22",
                command=lambda name=key: self.show(name),
            ).pack(fill="x", padx=12, pady=4)

    def _build_pages(self) -> None:
        host = ctk.CTkFrame(self, fg_color="#17130f")
        host.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        host.grid_columnconfigure(0, weight=1)
        host.grid_rowconfigure(0, weight=1)
        builders = {
            "home": self._page_home,
            "convert": self._page_convert,
            "edit": self._page_edit,
            "site": self._page_site,
            "office": self._page_office,
            "units": self._page_units,
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
        self._title(frame, "Пульт поверх Windows 11", "Инструменты, которых в системе нет из коробки.")
        text = (
            "Конвертеры картинок, JSON и CSV.\n"
            "Редактор текста, markdown и простой фотоцех.\n"
            "Сборщик локального сайта: папка + zip, интернет не нужен.\n"
            "Мост к Microsoft Office: DOCX, XLSX, PPTX. Word, Excel и PowerPoint открывают как свои.\n"
            "Единицы измерения и карточка системы."
        )
        ctk.CTkLabel(frame, text=text, justify="left", font=ctk.CTkFont(size=16)).pack(anchor="w", padx=24, pady=12)
        ctk.CTkButton(frame, text="Собрать сайт в zip", command=lambda: self.show("site")).pack(anchor="w", padx=24, pady=8)
        ctk.CTkButton(frame, text="Проверить Office", command=lambda: self.show("office")).pack(anchor="w", padx=24, pady=8)

    def _page_convert(self, frame: ctk.CTkFrame) -> None:
        self._title(frame, "Конвертеры", "Картинки, таблицы и архивы. Без облака и без очереди.")
        box = ctk.CTkTextbox(frame, height=220)
        box.pack(fill="both", expand=True, padx=24, pady=8)
        box.insert("1.0", "Выбери действие. Результат появится здесь.")

        def image() -> None:
            src = filedialog.askopenfilename(filetypes=[("Картинки", "*.png *.jpg *.jpeg *.webp *.bmp *.gif")])
            if not src:
                return
            dest = filedialog.asksaveasfilename(defaultextension=".webp", filetypes=[("WEBP", "*.webp"), ("PNG", "*.png"), ("JPEG", "*.jpg")])
            if dest:
                path = converters.convert_image(src, dest)
                box.insert("end", f"\nКартинка: {path}")

        def table() -> None:
            src = filedialog.askopenfilename(filetypes=[("JSON или CSV", "*.json *.csv")])
            if not src:
                return
            source = Path(src)
            if source.suffix.lower() == ".json":
                dest = filedialog.asksaveasfilename(defaultextension=".csv")
                if dest:
                    box.insert("end", f"\nCSV: {converters.json_to_csv(src, dest)}")
            else:
                dest = filedialog.asksaveasfilename(defaultextension=".json")
                if dest:
                    box.insert("end", f"\nJSON: {converters.csv_to_json(src, dest)}")

        def archive() -> None:
            folder = filedialog.askdirectory()
            if not folder:
                return
            dest = filedialog.asksaveasfilename(defaultextension=".zip")
            if dest:
                box.insert("end", f"\nZIP: {converters.pack_zip(folder, dest)}")

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=8)
        ctk.CTkButton(row, text="Картинка", command=image).pack(side="left", padx=4)
        ctk.CTkButton(row, text="JSON ↔ CSV", command=table).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Папка в zip", command=archive).pack(side="left", padx=4)

    def _page_edit(self, frame: ctk.CTkFrame) -> None:
        self._title(frame, "Редакторы", "Текст, markdown и картинка без лишнего софта.")
        editor = ctk.CTkTextbox(frame, height=220)
        editor.pack(fill="both", expand=True, padx=24, pady=8)
        editor.insert("1.0", "# Черновик\n\n**Жирный**, *курсив*, список:\n- пункт один\n- пункт два")
        status = ctk.CTkLabel(frame, text="")
        status.pack(anchor="w", padx=24)

        def stats() -> None:
            info = editors.text_stats(editor.get("1.0", "end"))
            status.configure(text=f"Слов: {info['words']} · строк: {info['lines']} · символов: {info['symbols']}")

        def preview() -> None:
            html_text = editors.markdown_to_html(editor.get("1.0", "end"))
            dest = filedialog.asksaveasfilename(defaultextension=".html")
            if dest:
                Path(dest).write_text(html_text, encoding="utf-8")
                status.configure(text=f"HTML сохранён: {dest}")

        def photo() -> None:
            src = filedialog.askopenfilename(filetypes=[("Картинки", "*.png *.jpg *.jpeg *.webp")])
            if not src:
                return
            dest = filedialog.asksaveasfilename(defaultextension=".png")
            if dest:
                editors.edit_image(src, dest, width=1280, grayscale=False, brightness=1.05)
                status.configure(text=f"Картинка ужата до 1280 по ширине: {dest}")

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=8)
        ctk.CTkButton(row, text="Статистика", command=stats).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Markdown в HTML", command=preview).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Ужать картинку", command=photo).pack(side="left", padx=4)

    def _page_site(self, frame: ctk.CTkFrame) -> None:
        self._title(frame, "Мини-сайт в zip", "Открыл index.html — и всё. CDN может идти пить чай.")
        title = ctk.CTkEntry(frame, placeholder_text="Название сайта")
        title.pack(fill="x", padx=24, pady=4)
        title.insert(0, "Локальная галерея")
        tagline = ctk.CTkEntry(frame, placeholder_text="Подзаголовок")
        tagline.pack(fill="x", padx=24, pady=4)
        tagline.insert(0, "Картинки в zip, интернет опционален")
        body = ctk.CTkTextbox(frame, height=180)
        body.pack(fill="both", expand=True, padx=24, pady=8)
        body.insert("1.0", "Это страница, которая живёт в папке.\nРаспаковал архив, открыл index.html, смотришь.")
        images: list[str] = []
        label = ctk.CTkLabel(frame, text="Картинок: 0")
        label.pack(anchor="w", padx=24)

        def add_images() -> None:
            picked = filedialog.askopenfilenames(filetypes=[("Картинки", "*.png *.jpg *.jpeg *.webp *.gif")])
            images.extend(picked)
            label.configure(text=f"Картинок: {len(images)}")

        def build() -> None:
            folder = filedialog.askdirectory(title="Куда положить сайт")
            if not folder:
                return
            pages = [
                {"title": "Главная", "body": body.get("1.0", "end").strip()},
                {"title": "Как открыть", "body": "1. Распаковать zip.\n2. Открыть index.html.\n3. Не ждать облако."},
            ]
            result = site_builder.build_site(
                Path(folder) / "site",
                title.get(),
                tagline.get(),
                "#c45c26",
                pages,
                images,
            )
            messagebox.showinfo("Сайт собран", f"Папка: {result['folder']}\nZIP: {result['zip']}")

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=8)
        ctk.CTkButton(row, text="Добавить картинки", command=add_images).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Собрать zip", command=build).pack(side="left", padx=4)

    def _page_office(self, frame: ctk.CTkFrame) -> None:
        self._title(frame, "Совместимость с Microsoft Office", "DOCX, XLSX, PPTX. Office не обязан быть установлен, чтобы файл родился.")
        title = ctk.CTkEntry(frame, placeholder_text="Заголовок")
        title.pack(fill="x", padx=24, pady=4)
        title.insert(0, "Отчёт Пульта")
        body = ctk.CTkTextbox(frame, height=160)
        body.pack(fill="both", expand=True, padx=24, pady=8)
        body.insert("1.0", "Пульт создал этот файл в Open XML.\nWord, Excel и PowerPoint открывают его как родной.")
        log = ctk.CTkTextbox(frame, height=140)
        log.pack(fill="x", padx=24, pady=4)

        def lines() -> list[str]:
            return [line for line in body.get("1.0", "end").splitlines() if line.strip()]

        def save_docx() -> None:
            dest = filedialog.asksaveasfilename(defaultextension=".docx")
            if dest:
                path = office_bridge.write_docx(dest, title.get(), lines())
                log.insert("end", f"\nDOCX: {path}\n{office_bridge.read_docx(path)[:240]}")

        def save_xlsx() -> None:
            dest = filedialog.asksaveasfilename(defaultextension=".xlsx")
            if dest:
                rows = [[str(i + 1), line] for i, line in enumerate(lines())]
                path = office_bridge.write_xlsx(dest, "Пульт", rows)
                log.insert("end", f"\nXLSX: {path}\n{office_bridge.read_xlsx(path)[:240]}")

        def save_pptx() -> None:
            dest = filedialog.asksaveasfilename(defaultextension=".pptx")
            if dest:
                slides = [(f"Пункт {i + 1}", line) for i, line in enumerate(lines())]
                path = office_bridge.write_pptx(dest, title.get(), slides or [("Пусто", "Добавь текст")])
                log.insert("end", f"\nPPTX: {path}\n{office_bridge.read_pptx(path)[:240]}")

        def open_last() -> None:
            dest = filedialog.askopenfilename(filetypes=[("Office", "*.docx *.xlsx *.pptx")])
            if dest:
                log.insert("end", f"\n{office_bridge.open_with_associated_app(dest)}")

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=8)
        ctk.CTkButton(row, text="DOCX", command=save_docx).pack(side="left", padx=4)
        ctk.CTkButton(row, text="XLSX", command=save_xlsx).pack(side="left", padx=4)
        ctk.CTkButton(row, text="PPTX", command=save_pptx).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Открыть в Office", command=open_last).pack(side="left", padx=4)

    def _page_units(self, frame: ctk.CTkFrame) -> None:
        self._title(frame, "Единицы", "Метры, килограммы и градусы. Без поиска в браузере.")
        value = ctk.CTkEntry(frame, placeholder_text="Число")
        value.pack(fill="x", padx=24, pady=4)
        value.insert(0, "10")
        result = ctk.CTkLabel(frame, text="Результат появится здесь", font=ctk.CTkFont(size=18))
        result.pack(anchor="w", padx=24, pady=12)

        def run(kind: str) -> None:
            number = float(value.get().replace(",", "."))
            if kind == "length":
                answer = units.convert_length(number, "м", "фут")
                result.configure(text=f"{number} м = {answer:.4f} фут")
            elif kind == "weight":
                answer = units.convert_weight(number, "кг", "фунт")
                result.configure(text=f"{number} кг = {answer:.4f} фунт")
            else:
                answer = units.convert_temperature(number, "C", "F")
                result.configure(text=f"{number} °C = {answer:.2f} °F")

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=24)
        ctk.CTkButton(row, text="Метры в футы", command=lambda: run("length")).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Кг в фунты", command=lambda: run("weight")).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Цельсий в Фаренгейт", command=lambda: run("temp")).pack(side="left", padx=4)

    def _page_system(self, frame: ctk.CTkFrame) -> None:
        self._title(frame, "Система", "Пульт не ставит драйверы. Он только смотрит, на чём сидит.")
        info = (
            f"Система: {platform.system()} {platform.release()}\n"
            f"Версия: {platform.version()}\n"
            f"Машина: {platform.machine()}\n"
            f"Python: {platform.python_version()}\n"
            "Ожидаемая база: Windows 11. На других системах движки тоже работают, оболочка не обижается."
        )
        ctk.CTkLabel(frame, text=info, justify="left", font=ctk.CTkFont(size=16)).pack(anchor="w", padx=24, pady=12)

    def _title(self, frame: ctk.CTkFrame, title: str, subtitle: str) -> None:
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=26, weight="bold")).pack(anchor="w", padx=24, pady=(20, 0))
        ctk.CTkLabel(frame, text=subtitle, text_color="#c9b8a6").pack(anchor="w", padx=24, pady=(0, 8))


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
