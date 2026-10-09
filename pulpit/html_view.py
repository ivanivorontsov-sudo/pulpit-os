"""Встроенный просмотр HTML. Браузер за окном больше не зовём."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk


class HtmlPane(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master, fg_color="#f4efe6")
        self.view = None
        self.fallback = None
        try:
            from tkinterweb import HtmlFrame

            self.view = HtmlFrame(self, messages_enabled=False, vertical_scrollbar=True)
            self.view.pack(fill="both", expand=True)
            self.view.load_html("<p style='font-family:Georgia'>Просмотр появится здесь.</p>")
        except Exception as exc:  # noqa: BLE001
            self.fallback = ctk.CTkTextbox(self)
            self.fallback.pack(fill="both", expand=True)
            self.fallback.insert("1.0", f"Встроенный просмотр не поднялся: {exc}\nПоставь tkinterweb.")

    def show_file(self, path: str | Path) -> None:
        target = Path(path)
        if self.view is not None:
            self.view.load_file(str(target))
            return
        if self.fallback is not None:
            self.fallback.delete("1.0", "end")
            self.fallback.insert("1.0", target.read_text(encoding="utf-8"))
