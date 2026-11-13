"""Стол изображений: пакетная конвертация и базовая обработка."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from pulpit.engines.images import create_contact_sheet, edit_image, image_info, supported_suffixes


class ImageBench(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.files: list[str] = []
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Стол изображений", font=ctk.CTkFont(size=26, weight="bold")).pack(anchor="w", padx=24, pady=(20, 0))
        ctk.CTkLabel(self, text="Пакетная конвертация, масштабирование, поворот, яркость, отражение и водяные знаки.", text_color="#c9b8a6").pack(anchor="w", padx=24)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=8)
        self.format = ctk.CTkComboBox(row, values=["png", "jpg", "webp", "bmp", "gif", "tiff"], width=105)
        self.format.set("png")
        self.format.pack(side="left", padx=4)
        self.width = ctk.CTkEntry(row, width=85, placeholder_text="ширина")
        self.width.pack(side="left", padx=4)
        self.height = ctk.CTkEntry(row, width=85, placeholder_text="высота")
        self.height.pack(side="left", padx=4)
        self.rotate = ctk.CTkComboBox(row, values=["0", "90", "180", "270"], width=85)
        self.rotate.set("0")
        self.rotate.pack(side="left", padx=4)
        self.quality = ctk.CTkEntry(row, width=85, placeholder_text="качество")
        self.quality.insert(0, "90")
        self.quality.pack(side="left", padx=4)
        self.fit = ctk.CTkComboBox(row, values=["contain", "cover", "stretch"], width=110)
        self.fit.set("contain")
        self.fit.pack(side="left", padx=4)
        flags = ctk.CTkFrame(self, fg_color="transparent")
        flags.pack(fill="x", padx=24, pady=4)
        self.gray = ctk.CTkCheckBox(flags, text="Чёрно-белое")
        self.gray.pack(side="left", padx=5)
        self.flip_h = ctk.CTkCheckBox(flags, text="Отразить по горизонтали")
        self.flip_h.pack(side="left", padx=5)
        self.flip_v = ctk.CTkCheckBox(flags, text="Отразить по вертикали")
        self.flip_v.pack(side="left", padx=5)
        self.brightness = ctk.CTkEntry(flags, width=100, placeholder_text="яркость 1.0")
        self.brightness.insert(0, "1.0")
        self.brightness.pack(side="left", padx=8)
        self.watermark = ctk.CTkEntry(self, placeholder_text="Водяной знак (необязательно)")
        self.watermark.pack(fill="x", padx=28, pady=4)
        self.listbox = ctk.CTkTextbox(self, height=250, font=ctk.CTkFont(family="Consolas", size=12))
        self.listbox.pack(fill="both", expand=True, padx=24, pady=8)
        self.listbox.insert("1.0", "Файлов пока нет. Добавь изображения или целую пачку.")
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=24, pady=8)
        ctk.CTkButton(buttons, text="Добавить", command=self.add).pack(side="left", padx=4)
        ctk.CTkButton(buttons, text="Информация", command=self.show_info).pack(side="left", padx=4)
        ctk.CTkButton(buttons, text="Обработать и сохранить", command=self.save).pack(side="left", padx=4)
        ctk.CTkButton(buttons, text="Контактный лист", command=self.contact_sheet).pack(side="left", padx=4)
        ctk.CTkButton(buttons, text="Очистить список", command=self.clear).pack(side="left", padx=4)

    def add(self) -> None:
        picked = filedialog.askopenfilenames(
            title="Изображения",
            filetypes=[("Изображения", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff"), ("Все файлы", "*.*")]
        )
        self.files.extend(path for path in picked if path not in self.files)
        self._refresh()

    def save(self) -> None:
        if not self.files:
            messagebox.showwarning("Пульт", "Сначала добавь изображения.")
            return
        folder = filedialog.askdirectory(title="Куда сохранить обработанные изображения")
        if not folder:
            return
        suffix = "." + self.format.get().lower()
        if suffix not in supported_suffixes():
            messagebox.showerror("Пульт", f"Формат {suffix} не поддерживается этой сборкой Pillow.")
            return
        try:
            width, height = self._int(self.width.get()), self._int(self.height.get())
            quality = self._int(self.quality.get()) or 90
            brightness = float(self.brightness.get().replace(",", ".") or "1")
        except ValueError as exc:
            messagebox.showerror("Пульт", f"Проверь параметры обработки: {exc}")
            return
        saved, failed = [], []
        for index, src in enumerate(self.files, start=1):
            stem = Path(src).stem
            dest = Path(folder) / f"{stem}{suffix}"
            if dest.exists():
                dest = Path(folder) / f"{stem}-{index}{suffix}"
            try:
                path = edit_image(
                    src, dest, width=width, height=height, rotate=int(self.rotate.get()),
                    grayscale=bool(self.gray.get()), brightness=brightness, quality=quality,
                    fit=self.fit.get(), flip_horizontal=bool(self.flip_h.get()),
                    flip_vertical=bool(self.flip_v.get()), watermark=self.watermark.get(),
                )
                saved.append(f"✓ {path.name} · {path.stat().st_size:,} байт")
            except Exception as exc:  # noqa: BLE001
                failed.append(f"✕ {Path(src).name}: {exc}")
        report = "\n".join(saved + failed) or "Нечего сохранять"
        self._set_log(report)
        messagebox.showinfo("Пульт", f"Готово: {len(saved)} из {len(self.files)}.\nПапка: {folder}")

    def show_info(self) -> None:
        if not self.files:
            messagebox.showwarning("Пульт", "Сначала добавь изображения.")
            return
        lines = []
        for path in self.files:
            try:
                info = image_info(path)
                lines.append(f"{info['name']} · {info['width']}×{info['height']} · {info['format']} · {info['megapixels']} Мп · {info['bytes']:,} байт · кадров: {info['frames']}")
            except Exception as exc:  # noqa: BLE001
                lines.append(f"{path}: {exc}")
        self._set_log("\n".join(lines))

    def contact_sheet(self) -> None:
        if not self.files:
            messagebox.showwarning("Пульт", "Сначала добавь изображения.")
            return
        dest = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if not dest:
            return
        try:
            path = create_contact_sheet(self.files, dest)
            self._set_log(f"Контактный лист создан: {path}\nРазмер: {path.stat().st_size:,} байт")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Контактный лист", str(exc))

    def clear(self) -> None:
        self.files.clear()
        self._refresh()

    def _refresh(self) -> None:
        self._set_log("\n".join(self.files) or "Список пуст")

    def _set_log(self, value: str) -> None:
        self.listbox.delete("1.0", "end")
        self.listbox.insert("1.0", value)

    @staticmethod
    def _int(raw: str) -> int | None:
        raw = raw.strip()
        if not raw:
            return None
        try:
            value = int(raw)
            if value <= 0:
                raise ValueError
            return value
        except ValueError:
            raise ValueError(f"Ожидалось положительное целое число, получено: {raw}")
