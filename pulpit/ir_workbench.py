"""Интерфейс универсального инфракрасного пульта."""
from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Callable

import customtkinter as ctk

from pulpit.engines import ir_remote as ir


class IRWorkbench(ctk.CTkFrame):
    """Профили устройств и управление по Broadlink, USB-serial или Home Assistant."""

    def __init__(self, master: Any) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.profiles = ir.load_profiles()
        self.current_profile: dict[str, Any] | None = None
        self.broadlink_devices: list[Any] = []
        self.broadlink_device: Any | None = None
        self._busy = False
        self.adapter_var = tk.StringVar(value="Broadlink RM / RM4")
        self.ha_url_var = tk.StringVar(value="http://homeassistant.local:8123")
        self.ha_entity_var = tk.StringVar(value="remote.living_room")
        self.ha_device_var = tk.StringVar(value="television")
        self.ha_token_var = tk.StringVar(value="")
        self.serial_port_var = tk.StringVar(value="")
        self.broadlink_var = tk.StringVar(value="")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            self, text="Универсальный ИК-пульт",
            font=ctk.CTkFont(size=27, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(16, 2))
        ctk.CTkLabel(
            self,
            text="Телевизоры · кондиционеры · приставки · аудиосистемы · проекторы · освещение",
            text_color="#c9b8a6",
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(52, 8))

        self.tabs = ctk.CTkTabview(self, corner_radius=10)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))
        for name in ("Мои пульты", "Подключение", "Как подключить"):
            self.tabs.add(name)
        self._build_remotes(self.tabs.tab("Мои пульты"))
        self._build_connections(self.tabs.tab("Подключение"))
        self._build_help(self.tabs.tab("Как подключить"))
        self.status = ctk.CTkLabel(self, text="Создай профиль или импортируй ИК-файл.", text_color="#c9b8a6", anchor="w")
        self.status.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 8))
        self._refresh_profiles()
        if self.profiles:
            self._select_profile(self.profiles[0].get("id"))

    def _button_row(self, parent: Any) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=8, pady=5)
        return frame

    def _set_status(self, value: str) -> None:
        self.status.configure(text=value)

    def _run_worker(
        self,
        label: str,
        worker: Callable[[], Any],
        on_success: Callable[[Any], None],
    ) -> None:
        if self._busy:
            self._set_status("Предыдущая операция ещё выполняется.")
            return
        self._busy = True
        self._set_status(label)

        def run() -> None:
            try:
                result = worker()
                error = None
            except Exception as exc:  # noqa: BLE001
                result = None
                error = exc

            def finish() -> None:
                self._busy = False
                if error is not None:
                    self._set_status(f"Ошибка: {error}")
                    messagebox.showerror("Инфракрасный пульт", str(error))
                    return
                try:
                    on_success(result)
                except Exception as exc:  # noqa: BLE001
                    self._set_status(f"Ошибка: {exc}")
                    messagebox.showerror("Инфракрасный пульт", str(exc))

            try:
                self.after(0, finish)
            except tk.TclError:
                pass

        threading.Thread(target=run, name="PulpitIRWorker", daemon=True).start()

    # ---------------------------------------------------------------- profiles
    def _build_remotes(self, tab: Any) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(3, weight=1)

        profile_row = self._button_row(tab)
        self.profile_select = ctk.CTkComboBox(
            profile_row, values=["Нет профилей"], width=260,
            command=self._profile_changed,
        )
        self.profile_select.pack(side="left", padx=3)
        ctk.CTkButton(profile_row, text="Новый профиль", width=120, command=self._new_profile).pack(side="left", padx=3)
        ctk.CTkButton(profile_row, text="Сохранить", width=100, command=self._save_profile).pack(side="left", padx=3)
        ctk.CTkButton(profile_row, text="Удалить профиль", width=120, command=self._delete_profile).pack(side="left", padx=3)

        meta = self._button_row(tab)
        self.profile_name = ctk.CTkEntry(meta, placeholder_text="Название: Гостиная / телевизор")
        self.profile_name.pack(side="left", fill="x", expand=True, padx=3)
        self.profile_category = ctk.CTkComboBox(meta, values=["TV", "Кондиционер", "Аудио", "Приставка", "Проектор", "Свет", "Другое"], width=160)
        self.profile_category.set("TV")
        self.profile_category.pack(side="left", padx=3)
        self.profile_brand = ctk.CTkEntry(meta, placeholder_text="Бренд", width=150)
        self.profile_brand.pack(side="left", padx=3)
        self.profile_model = ctk.CTkEntry(meta, placeholder_text="Модель", width=160)
        self.profile_model.pack(side="left", padx=3)

        action_row = self._button_row(tab)
        for text, action in [
            ("Импорт Flipper .ir", self._import_flipper),
            ("Импорт Pronto HEX", self._import_pronto),
            ("Экспорт .ir", self._export_flipper),
            ("Обучить кнопку", self._learn_code),
            ("Удалить кнопку", self._delete_code),
        ]:
            ctk.CTkButton(action_row, text=text, width=138, command=action).pack(side="left", padx=2)

        self.code_grid = ctk.CTkScrollableFrame(tab, label_text="Кнопки выбранного устройства", corner_radius=8)
        self.code_grid.pack(fill="both", expand=True, padx=10, pady=6)
        self.code_grid.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.code_name_select = ctk.CTkComboBox(tab, values=["Нет кнопок"], width=250)
        self.code_name_select.pack(anchor="w", padx=14, pady=(0, 8))

    def _refresh_profiles(self) -> None:
        labels = [str(profile.get("name", "Пульт")) for profile in self.profiles]
        self.profile_select.configure(values=labels or ["Нет профилей"])
        if not labels:
            self.profile_select.set("Нет профилей")

    def _save_profile(self) -> None:
        if not self.current_profile:
            return
        self.current_profile["name"] = self.profile_name.get().strip() or "Мой пульт"
        self.current_profile["category"] = self.profile_category.get()
        self.current_profile["brand"] = self.profile_brand.get().strip()
        self.current_profile["model"] = self.profile_model.get().strip()
        ir.save_profiles(self.profiles)
        self._refresh_profiles()
        self.profile_select.set(self.current_profile["name"])
        self._set_status(f"Профиль «{self.current_profile['name']}» сохранён локально.")

    def _new_profile(self) -> None:
        profile = ir.make_profile("Новый пульт")
        self.profiles.append(profile)
        self._select_profile(profile["id"])
        self._refresh_profiles()
        self.profile_select.set(profile["name"])
        ir.save_profiles(self.profiles)
        self._set_status("Создан профиль. Импортируй коды или обучи кнопки с оригинального пульта.")

    def _delete_profile(self) -> None:
        if not self.current_profile:
            return
        if not messagebox.askyesno("Удаление профиля", f"Удалить «{self.current_profile.get('name')}» и все его коды?"):
            return
        profile_id = self.current_profile.get("id")
        self.profiles = [item for item in self.profiles if item.get("id") != profile_id]
        self.current_profile = None
        ir.save_profiles(self.profiles)
        self._refresh_profiles()
        self._render_codes()
        self._set_status("Профиль удалён.")

    def _profile_changed(self, name: str) -> None:
        profile = next((item for item in self.profiles if item.get("name") == name), None)
        if profile:
            self._select_profile(profile.get("id"))

    def _select_profile(self, profile_id: str | None) -> None:
        self.current_profile = next((item for item in self.profiles if item.get("id") == profile_id), None)
        if not self.current_profile:
            return
        profile = self.current_profile
        self.profile_select.set(profile.get("name", "Мой пульт"))
        self.profile_name.delete(0, "end")
        self.profile_name.insert(0, profile.get("name", ""))
        self.profile_category.set(profile.get("category", "TV"))
        self.profile_brand.delete(0, "end")
        self.profile_brand.insert(0, profile.get("brand", ""))
        self.profile_model.delete(0, "end")
        self.profile_model.insert(0, profile.get("model", ""))
        self._render_codes()

    def _render_codes(self) -> None:
        for child in self.code_grid.winfo_children():
            child.destroy()
        codes = self.current_profile.get("codes", []) if self.current_profile else []
        names = [str(code.get("name", "Кнопка")) for code in codes]
        self.code_name_select.configure(values=names or ["Нет кнопок"])
        self.code_name_select.set(names[0] if names else "Нет кнопок")
        if not codes:
            ctk.CTkLabel(
                self.code_grid,
                text="Здесь появятся кнопки. Импортируй файл .ir или нажми «Обучить кнопку».",
                text_color="#c9b8a6",
            ).grid(row=0, column=0, padx=18, pady=18, sticky="w")
            return
        for index, code in enumerate(codes):
            row, column = divmod(index, 4)
            button = ctk.CTkButton(
                self.code_grid, text=str(code.get("name", "Кнопка")),
                height=58, command=lambda item=code: self._send_code(item),
            )
            button.grid(row=row, column=column, sticky="ew", padx=5, pady=5)

    def _selected_code(self) -> dict[str, Any] | None:
        if not self.current_profile:
            return None
        name = self.code_name_select.get()
        return next((code for code in self.current_profile.get("codes", []) if code.get("name") == name), None)

    def _import_flipper(self) -> None:
        if not self.current_profile:
            self._new_profile()
        picked = filedialog.askopenfilename(filetypes=[("Flipper IR", "*.ir"), ("Текст", "*.txt"), ("Все файлы", "*.*")])
        if not picked or not self.current_profile:
            return
        try:
            profile = ir.import_flipper_file(picked)
            added = 0
            for code in profile["codes"]:
                try:
                    ir.add_code(self.current_profile, code)
                    added += 1
                except ValueError:
                    pass
            self._save_profile()
            self._render_codes()
            warnings = profile.get("import_warnings", [])
            summary = f"Импортировано кнопок: {added}."
            if warnings:
                summary += f" Пропущено: {len(warnings)} (неподдерживаемые parsed-сигналы или ошибки)."
            self._set_status(summary)
            if warnings:
                messagebox.showinfo("Импорт завершён с замечаниями", summary + "\n\n" + "\n".join(warnings[:8]))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Импорт Flipper IR", str(exc))

    def _import_pronto(self) -> None:
        if not self.current_profile:
            self._new_profile()
        picked = filedialog.askopenfilename(filetypes=[("Pronto HEX", "*.hex *.txt"), ("Все файлы", "*.*")])
        if not picked or not self.current_profile:
            return
        try:
            code = ir.import_pronto_file(picked)
            dialog = ctk.CTkInputDialog(text="Название кнопки:", title="Импорт Pronto")
            name = dialog.get_input() or Path(picked).stem
            code["name"] = name
            ir.add_code(self.current_profile, code)
            self._save_profile()
            self._render_codes()
            self._set_status(f"Pronto-код «{name}» импортирован.")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Импорт Pronto", str(exc))

    def _export_flipper(self) -> None:
        if not self.current_profile:
            return
        picked = filedialog.asksaveasfilename(
            defaultextension=".ir", initialfile=f"{self.current_profile.get('name', 'remote')}.ir",
            filetypes=[("Flipper IR", "*.ir")],
        )
        if not picked:
            return
        try:
            Path(picked).write_text(ir.export_flipper_ir(self.current_profile), encoding="utf-8")
            self._set_status(f"Экспортировано: {picked}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Экспорт IR", str(exc))

    def _learn_code(self) -> None:
        if not self.current_profile:
            self._new_profile()
        if not self.current_profile:
            return
        dialog = ctk.CTkInputDialog(text="Название кнопки штатного пульта:", title="Обучение ИК-команды")
        name = dialog.get_input()
        if not name:
            return
        adapter = self.adapter_var.get()
        if adapter == "Broadlink RM / RM4":
            if code.get("kind") != "raw":
                messagebox.showwarning("ИК-пульт", "Эта кнопка не содержит raw-ИК-сигнал. Команды Home Assistant отправляй через адаптер Home Assistant.")
                return
            device = self._current_broadlink_device()
            if device is None:
                messagebox.showwarning("ИК-пульт", "Сначала найди и выбери Broadlink на вкладке «Подключение».")
                return
            self._run_worker(
                f"Обучение «{name}»: нажми эту кнопку на оригинальном пульте перед Broadlink…",
                lambda: ir.BROADLINK.learn(device, timeout=30),
                lambda data: self._save_learned_code(name, data),
            )
            return
        if adapter == "USB-ИК через COM (ESP32)":
            port = self.serial_port_var.get().split(" — ", 1)[0].strip()
            if not port:
                messagebox.showwarning("ИК-пульт", "Выбери COM-порт на вкладке «Подключение».")
                return
            self._run_worker(
                f"Обучение «{name}»: направь оригинальный пульт на ИК-приёмник…",
                lambda: ir.serial_learn(port, timeout=30),
                lambda data: self._save_learned_code(name, data),
            )
            return
        base, token, entity, device = self._ha_connection()
        self._run_worker(
            f"Home Assistant обучает «{name}»… нажми кнопку штатного пульта у ИК-приёмника.",
            lambda: ir.home_assistant_learn(base, token, entity, device, name, timeout=35),
            lambda _result: self._save_ha_code(name, device),
        )

    def _save_learned_code(self, name: str, data: dict[str, Any]) -> None:
        if not self.current_profile:
            return
        data["name"] = name
        ir.add_code(self.current_profile, data)
        self._save_profile()
        self._render_codes()
        self._set_status(f"Команда «{name}» обучена и сохранена.")

    def _save_ha_code(self, name: str, device: str) -> None:
        if not self.current_profile:
            return
        ir.add_code(self.current_profile, {
            "name": name,
            "kind": "homeassistant",
            "ha_device": device,
            "ha_command": name,
        })
        self._save_profile()
        self._render_codes()
        self._set_status(f"Home Assistant сохранил команду «{name}» для устройства «{device}».")

    def _delete_code(self) -> None:
        if not self.current_profile:
            return
        code = self._selected_code()
        if not code:
            return
        if not messagebox.askyesno("Удалить кнопку", f"Удалить команду «{code['name']}»?"):
            return
        ir.remove_code(self.current_profile, code["name"])
        self._save_profile()
        self._render_codes()

    # ------------------------------------------------------------- connectors
    def _build_connections(self, tab: Any) -> None:
        tab.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tab, text="Активный адаптер", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=14, pady=(12, 4))
        self.adapter_select = ctk.CTkComboBox(
            tab,
            values=["Broadlink RM / RM4", "USB-ИК через COM (ESP32)", "Home Assistant"],
            variable=self.adapter_var, width=340,
        )
        self.adapter_select.pack(anchor="w", padx=14, pady=4)

        broad = ctk.CTkFrame(tab, fg_color="#2a211a", corner_radius=10)
        broad.pack(fill="x", padx=10, pady=7)
        ctk.CTkLabel(broad, text="Broadlink RM / RM4", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=12, pady=(8, 2))
        row = self._button_row(broad)
        ctk.CTkButton(row, text="Найти устройства в сети", command=self._discover_broadlink, width=190).pack(side="left", padx=3)
        self.broadlink_select = ctk.CTkComboBox(row, values=["Не найдено"], variable=self.broadlink_var, width=300)
        self.broadlink_select.pack(side="left", padx=3)
        ctk.CTkLabel(broad, text="Поддерживает отправку и обучение ИК-команд; RF-режим в этом модуле пока не реализован.", text_color="#c9b8a6").pack(anchor="w", padx=12, pady=(0, 8))

        serial_box = ctk.CTkFrame(tab, fg_color="#2a211a", corner_radius=10)
        serial_box.pack(fill="x", padx=10, pady=7)
        ctk.CTkLabel(serial_box, text="USB-ИК передатчик / ESP32", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=12, pady=(8, 2))
        row = self._button_row(serial_box)
        self.serial_select = ctk.CTkComboBox(row, values=["COM-порт не выбран"], variable=self.serial_port_var, width=300)
        self.serial_select.pack(side="left", padx=3)
        ctk.CTkButton(row, text="Обновить COM-порты", command=self._refresh_serial_ports, width=160).pack(side="left", padx=3)
        ctk.CTkLabel(serial_box, text="Нужен адаптер с ИК-светодиодом и приёмником, прошитый приложенным скетчем. Обычный USB-кабель ИК не излучает.", text_color="#c9b8a6").pack(anchor="w", padx=12, pady=(0, 8))

        ha_box = ctk.CTkFrame(tab, fg_color="#2a211a", corner_radius=10)
        ha_box.pack(fill="x", padx=10, pady=7)
        ctk.CTkLabel(ha_box, text="Home Assistant (Broadlink / ESPHome / другие remote-адаптеры)", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=12, pady=(8, 2))
        self.ha_url = ctk.CTkEntry(ha_box, textvariable=self.ha_url_var, placeholder_text="http://homeassistant.local:8123")
        self.ha_url.pack(fill="x", padx=12, pady=3)
        row = self._button_row(ha_box)
        self.ha_entity = ctk.CTkEntry(row, textvariable=self.ha_entity_var, placeholder_text="remote.living_room", width=220)
        self.ha_entity.pack(side="left", padx=3)
        self.ha_device = ctk.CTkEntry(row, textvariable=self.ha_device_var, placeholder_text="device name", width=180)
        self.ha_device.pack(side="left", padx=3)
        self.ha_token = ctk.CTkEntry(ha_box, textvariable=self.ha_token_var, placeholder_text="Long-Lived Access Token", show="•")
        self.ha_token.pack(fill="x", padx=12, pady=3)
        ctk.CTkLabel(ha_box, text="Токен используется только в памяти текущего сеанса и не сохраняется в профилях.", text_color="#c9b8a6").pack(anchor="w", padx=12, pady=(0, 8))

        row = self._button_row(tab)
        ctk.CTkButton(row, text="Проверить Home Assistant", command=self._check_home_assistant, width=210).pack(side="left", padx=3)

    def _current_broadlink_device(self) -> Any | None:
        selected = self.broadlink_var.get()
        for device in self.broadlink_devices:
            if ir.device_label(device) == selected:
                return device
        return None

    def _discover_broadlink(self) -> None:
        self._run_worker(
            "Ищу Broadlink-адаптеры в локальной сети…",
            lambda: ir.BROADLINK.discover(timeout=5),
            self._on_broadlink_found,
        )

    def _on_broadlink_found(self, devices: list[Any]) -> None:
        self.broadlink_devices = devices
        labels = [ir.device_label(device) for device in devices]
        self.broadlink_select.configure(values=labels or ["Не найдено"])
        if labels:
            self.broadlink_var.set(labels[0])
            self._set_status(f"Найдено Broadlink: {len(labels)}.")
        else:
            self.broadlink_var.set("Не найдено")
            self._set_status("Broadlink в локальной сети не обнаружен. Проверь Wi-Fi и питание адаптера.")

    def _refresh_serial_ports(self) -> None:
        try:
            ports = ir.list_serial_ports()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("COM-порты", str(exc))
            return
        labels = [f"{item['device']} — {item['description']}" for item in ports]
        self.serial_select.configure(values=labels or ["COM-порты не найдены"])
        if labels:
            self.serial_port_var.set(labels[0])
            self._set_status(f"Найдено последовательных портов: {len(labels)}.")
        else:
            self.serial_port_var.set("")
            self._set_status("COM-порты не найдены. Подключи USB-ИК адаптер и обнови список.")

    def _ha_connection(self) -> tuple[str, str, str, str]:
        return (
            self.ha_url_var.get().strip(),
            self.ha_token_var.get().strip(),
            self.ha_entity_var.get().strip(),
            self.ha_device_var.get().strip(),
        )

    def _check_home_assistant(self) -> None:
        base, token, entity, device = self._ha_connection()
        self._run_worker(
            "Проверяю подключение Home Assistant…",
            lambda: ir.home_assistant_ping(base, token),
            lambda result: self._set_status("Home Assistant отвечает: " + str(result.get("message", "подключение успешно"))),
        )

    # --------------------------------------------------------------- transmit
    def _send_code(self, code: dict[str, Any]) -> None:
        adapter = self.adapter_var.get()
        if adapter == "Broadlink RM / RM4":
            device = self._current_broadlink_device()
            if device is None:
                messagebox.showwarning("ИК-пульт", "Сначала найди Broadlink на вкладке «Подключение».")
                return
            self._run_worker(
                f"Отправляю «{code['name']}» через Broadlink…",
                lambda: ir.BROADLINK.send(device, code),
                lambda _result: self._set_status(f"Отправлена команда: {code['name']}"),
            )
            return
        if adapter == "USB-ИК через COM (ESP32)":
            port = self.serial_port_var.get().split(" — ", 1)[0].strip()
            if not port:
                messagebox.showwarning("ИК-пульт", "Сначала выбери COM-порт.")
                return
            if code.get("kind") != "raw":
                messagebox.showwarning("ИК-пульт", "Эта кнопка не содержит raw-импульсов.")
                return
            self._run_worker(
                f"Отправляю «{code['name']}» через {port}…",
                lambda: ir.serial_send(
                    port, code.get("timings", []),
                    frequency=int(code.get("frequency", ir.DEFAULT_FREQUENCY)),
                    repeats=int(code.get("repeat", 1)),
                ),
                lambda response: self._set_status(f"{code['name']}: {response}"),
            )
            return
        if code.get("kind") != "homeassistant":
            messagebox.showwarning(
                "ИК-пульт",
                "Для Home Assistant используй команду, обученную через него, или выбери Broadlink/USB-ИК для raw-кодов.",
            )
            return
        base, token, entity, _device = self._ha_connection()
        device = str(code.get("ha_device") or self.ha_device_var.get().strip())
        command = str(code.get("ha_command") or code.get("name"))
        self._run_worker(
            f"Отправляю «{code['name']}» через Home Assistant…",
            lambda: ir.home_assistant_send(base, token, entity, device, command),
            lambda _result: self._set_status(f"Home Assistant отправил: {code['name']}"),
        )

    def _build_help(self, tab: Any) -> None:
        body = ctk.CTkTextbox(tab, wrap="word", font=ctk.CTkFont(size=13))
        body.pack(fill="both", expand=True, padx=12, pady=12)
        body.insert(
            "1.0",
            "КАК ПОДКЛЮЧИТЬ УНИВЕРСАЛЬНЫЙ ИК-ПУЛЬТ\n\n"
            "1. Broadlink RM Mini / RM4 Mini / RM Pro\n"
            "Подключи Broadlink к той же Wi-Fi сети, что и компьютер. Нажми «Найти устройства в сети» на вкладке «Подключение». "
            "RM Mini/RM4 Mini управляют ИК-техникой; RM Pro в зависимости от модели поддерживает также некоторые радиочастотные устройства. "
            "Положи адаптер в прямой видимости от техники.\n\n"
            "2. USB-ИК адаптер на ESP32\n"
            "Подключи ESP32 с ИК-светодиодом и приёмником, прошей файл firmware/PulpitIRBridge.ino из репозитория, затем выбери появившийся COM-порт. "
            "Скетч использует библиотеку IRremoteESP8266 из Arduino Library Manager. Рекомендуемая схема: ИК-светодиод с транзисторным драйвером на GPIO 4, "
            "приёмник TSOP38238/VS1838B на GPIO 15, общий GND. Не подключай мощный ИК-светодиод напрямую к GPIO.\n\n"
            "3. Home Assistant\n"
            "Введи адрес сервера, сущность remote.* и Long-Lived Access Token. Здесь используются сервисы remote.learn_command и remote.send_command. "
            "Токен не сохраняется в файлах профилей. В Home Assistant заранее должна быть настроена IR-интеграция/адаптер.\n\n"
            "ПРОФИЛИ И КОДЫ\n"
            "Импортируй Flipper Zero .ir или Pronto HEX, либо обучи кнопки с оригинального пульта. Профили хранятся локально в папке конфигурации Пульта. "
            "Их можно экспортировать в стандартный Flipper .ir и использовать в совместимых устройствах.\n\n"
            "КАКАЯ ТЕХНИКА ПОДХОДИТ\n"
            "Телевизоры, кондиционеры, ТВ-приставки, проекторы, ресиверы, саундбары, вентиляторы и световые контроллеры — если у них есть ИК-приёмник и известен код. "
            "ИК не проходит сквозь стены и мебель: адаптер должен «видеть» окно приёмника.\n\n"
            "ОГРАНИЧЕНИЯ\n"
            "Обычный USB-приёмник без ИК-передатчика не сможет управлять техникой. Bluetooth, Wi-Fi и радиопульты не становятся ИК-устройствами; для них нужны соответствующие сетевые или RF-адаптеры. "
            "Некоторые кондиционеры используют длинные фирменные кадры, а у отдельных устройств есть защищённые/динамические коды. Универсального кода для всех моделей не существует.\n\n"
            "База Flipper-IRDB: https://github.com/flipperdevices/IRDB\n"
            "Формат .ir: https://developer.flipper.net/flipperzero/doxygen/infrared_file_format.html\n"
            "ESPHome IR transmitter: https://esphome.io/components/remote_transmitter/\n",
        )
        body.configure(state="disabled")
