"""Launcher for the native interactive GrapesJS page studio."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import customtkinter as ctk


class ConstructorView(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.process: subprocess.Popen | None = None
        self._build()

    def _build(self) -> None:
        root = ctk.CTkFrame(self, fg_color="#1b2435", corner_radius=18)
        root.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(root, text="СТУДИЯ САЙТОВ", text_color="#98a8c8", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=28, pady=(26, 4))
        ctk.CTkLabel(root, text="Визуальный конструктор", font=ctk.CTkFont(size=30, weight="bold")).pack(anchor="w", padx=28, pady=2)
        ctk.CTkLabel(
            root,
            text="Собирайте полноценные сайты из блоков, настраивайте каждый элемент прямо на холсте и сразу смотрите, как страница выглядит на компьютере, планшете и телефоне.",
            wraplength=760,
            justify="left",
            text_color="#bdc9dc",
            font=ctk.CTkFont(size=14),
        ).pack(anchor="w", padx=28, pady=(6, 22))

        grid = ctk.CTkFrame(root, fg_color="transparent")
        grid.pack(fill="x", padx=22, pady=6)
        grid.grid_columnconfigure((0, 1, 2), weight=1)
        features = [
            ("01", "Drag & Drop", "Перетаскивайте секции, карточки, формы, галереи и другие элементы."),
            ("02", "Живой предпросмотр", "Редактируйте текст и стили на самом холсте. Переключайте размеры экрана."),
            ("03", "Многостраничные сайты", "Создавайте страницы, меняйте адреса и настраивайте SEO каждой страницы."),
            ("04", "Стили и свойства", "Цвета, типографика, размеры, отступы, границы, слои и атрибуты."),
            ("05", "Медиатека", "Импортируйте изображения и используйте их повторно в проекте."),
            ("06", "Экспорт без облака", "Сохраняйте JSON проекта и выгружайте готовый сайт в ZIP для GitHub Pages."),
        ]
        for i, (num, title, description) in enumerate(features):
            card = ctk.CTkFrame(grid, fg_color="#25334a", corner_radius=12)
            card.grid(row=i // 3, column=i % 3, sticky="nsew", padx=6, pady=6)
            ctk.CTkLabel(card, text=num, text_color="#91a0ff", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=13, pady=(12, 3))
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=13, pady=1)
            ctk.CTkLabel(card, text=description, text_color="#aebbd0", wraplength=205, justify="left").pack(anchor="w", padx=13, pady=(3, 13))

        row = ctk.CTkFrame(root, fg_color="transparent")
        row.pack(fill="x", padx=28, pady=(22, 8))
        ctk.CTkButton(
            row,
            text="Открыть визуальный конструктор  →",
            height=46,
            width=290,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#727fe7",
            hover_color="#8792f3",
            command=self.open_builder,
        ).pack(side="left")
        self.status = ctk.CTkLabel(row, text="Проекты хранятся локально · без аккаунта и обязательного облака", text_color="#aebbd0")
        self.status.pack(side="left", padx=16)
        ctk.CTkLabel(
            root,
            text="Подсказка: Ctrl+S — сохранить проект · Ctrl+Z — отменить · Экспорт ZIP — готовый сайт с HTML, CSS и ресурсами.",
            text_color="#8493aa",
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=28, pady=(10, 24))

    def open_builder(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.status.configure(text="Конструктор уже открыт.")
            return
        if getattr(sys, "frozen", False):
            command = [sys.executable, "--site-builder"]
        else:
            command = [sys.executable, "-m", "pulpit.builder_app"]
        kwargs = {"cwd": str(Path(__file__).resolve().parents[1])}
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        try:
            self.process = subprocess.Popen(command, **kwargs)
            self.status.configure(text="Визуальный конструктор запущен в отдельном окне.")
        except Exception as exc:
            self.status.configure(text=f"Не удалось запустить: {exc}")
