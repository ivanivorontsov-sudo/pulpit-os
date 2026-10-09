"""Стол для картинок: формат выбирается явно, файл пишется и проверяется."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from pulpit.engines.images import convert_image, edit_image, supported_suffixes


class ImageBench(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.files: list[str] = []
        ctk.CTkLabel(self, text="Картинки", font=ctk.CTkFont(size=26, weight="bold")).pack(anchor="w", padx=24, pady=(20, 0))
        ctk.CTkLabel(self, text="Сначала папка, потом формат. Если файл не лёг на диск, скажем прямо.", text_color="#c9b8a6").pack(anchor="w", padx=24)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=8)
        self.format = ctk.CTkComboBox(row, values=["png", "jpg", "webp", "bmp", "gif"], width=120)
        self.format.set("png")
        self.format.pack(side="left", padx=4)
        self.width = ctk.CTkEntry(row, width=90, placeholder_text="ширина")
        self.width.pack(side="left", padx=4)
        self.quality = ctk.CTkEntry(row, width=90, placeholder_text="качество")
        self.quality.insert(0, "90")
        self.quality.pack(side="left", padx=4)
        self.gray = ctk.CTkCheckBox(row, text="ч/б")
        self.gray.pack(side="left", padx=8)
        self.listbox = ctk.CTkTextbox(self, height=240)
        self.listbox.pack(fill="both", expand=True, padx=24, pady=8)
        self.listbox.insert("1.0", "Файлов пока нет. Добавь, иначе конвертировать нечего.")
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=24, pady=8)
        ctk.CTkButton(buttons, text="Добавить", command=self.add).pack(side="left", padx=4)
        ctk.CTkButton(buttons, text="Конвертировать и сохранить", command=self.save).pack(side="left", padx=4)

    def add(self) -> None:
        picked = filedialog.askopenfilenames(
            title="Картинки",
            filetypes=[("Картинки", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff")],
        )
        self.files.extend(path for path in picked if path not in self.files)
        self._refresh()

    def save(self) -> None:
        if not self.files:
            messagebox.showwarning("Пульт", "Сначала добавь картинки.")
            return
        folder = filedialog.askdirectory(title="Куда сохранить")
        if not folder:
            return
        suffix = "." + self.format.get().lower()
        if suffix not in supported_suffixes() and suffix != ".jpg":
            messagebox.showerror("Пульт", f"Формат {suffix} здесь не пишется.")
            return
        width = self._int(self.width.get())
        quality = self._int(self.quality.get()) or 90
        saved, failed = [], []
        for src in self.files:
            dest = Path(folder) / f"{Path(src).stem}{suffix}"
            try:
                path = edit_image(
                    src,
                    dest,
                    width=width,
                    grayscale=bool(self.gray.get()),
                    quality=quality,
                ) if width or self.gray.get() else convert_image(src, dest, quality=quality)
                saved.append(f"{path.name} · {path.stat().st_size} байт")
            except Exception as exc:  # noqa: BLE001
                failed.append(f"{Path(src).name}: {exc}")
        report = "Сохранено:\n" + "\n".join(saved)
        if failed:
            report += "\n\nНе вышло:\n" + "\n".join(failed)
        self.listbox.delete("1.0", "end")
        self.listbox.insert("1.0", report)
        messagebox.showinfo("Пульт", f"Записано {len(saved)} из {len(self.files)}.\nПапка: {folder}")

    def _refresh(self) -> None:
        self.listbox.delete("1.0", "end")
        self.listbox.insert("1.0", "\n".join(self.files) or "Пусто")

    @staticmethod
    def _int(raw: str) -> int | None:
        raw = raw.strip()
        return int(raw) if raw.isdigit() else None
