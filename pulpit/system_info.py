"""Безопасная диагностика устройства для вкладки «Система»."""

from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path


def _bytes(value: int) -> str:
    size = float(value)
    for unit in ("Б", "КиБ", "МиБ", "ГиБ", "ТиБ"):
        if size < 1024 or unit == "ТиБ":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} ТиБ"


def snapshot() -> dict[str, object]:
    home = Path.home()
    root = Path.home().anchor or str(home)
    usage = shutil.disk_usage(root)
    info: dict[str, object] = {
        "os": f"{platform.system()} {platform.release()}",
        "version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor() or "Не определён системой",
        "logical_cpus": os.cpu_count() or 1,
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "disk_total": _bytes(usage.total),
        "disk_used": _bytes(usage.used),
        "disk_free": _bytes(usage.free),
        "disk_percent": round(usage.used / usage.total * 100, 1) if usage.total else 0,
        "home": str(home),
    }
    try:
        import psutil
        memory = psutil.virtual_memory()
        info.update({
            "ram_total": _bytes(memory.total),
            "ram_available": _bytes(memory.available),
            "ram_percent": round(memory.percent, 1),
            "cpu_percent": psutil.cpu_percent(interval=0.15),
            "uptime_hours": round((__import__("time").time() - psutil.boot_time()) / 3600, 1),
        })
        battery = psutil.sensors_battery()
        if battery:
            info["battery"] = f"{battery.percent:.0f}% · {'зарядка' if battery.power_plugged else 'от батареи'}"
    except (ImportError, OSError, AttributeError):
        info["monitoring"] = "Дополнительные показатели RAM/CPU недоступны"
    return info


def format_snapshot(info: dict[str, object] | None = None) -> str:
    data = info or snapshot()
    labels = [
        ("os", "Операционная система"), ("version", "Версия системы"),
        ("architecture", "Архитектура"), ("processor", "Процессор"),
        ("logical_cpus", "Логических ядер"), ("cpu_percent", "Загрузка CPU"),
        ("ram_total", "Оперативная память"), ("ram_available", "Свободная RAM"),
        ("ram_percent", "Использование RAM"), ("disk_total", "Диск"),
        ("disk_used", "Занято на диске"), ("disk_free", "Свободно на диске"),
        ("disk_percent", "Заполнено"), ("battery", "Батарея"),
        ("uptime_hours", "Время после запуска, ч"), ("python", "Python"),
        ("python_executable", "Интерпретатор"), ("home", "Домашняя папка"),
        ("monitoring", "Мониторинг"),
    ]
    return "\n".join(f"{label}: {data[key]}" for key, label in labels if key in data)
