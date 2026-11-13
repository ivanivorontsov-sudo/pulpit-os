"""Конвертер физических и цифровых единиц."""

from __future__ import annotations

LENGTH = {"мм": 0.001, "см": 0.01, "м": 1.0, "км": 1000.0, "дюйм": 0.0254, "фут": 0.3048, "ярд": 0.9144, "миля": 1609.344, "морская миля": 1852.0}
WEIGHT = {"мкг": 1e-9, "мг": 1e-6, "г": 0.001, "кг": 1.0, "ц": 100.0, "т": 1000.0, "унция": 0.028349523125, "фунт": 0.45359237, "stone": 6.35029318}
AREA = {"мм²": 1e-6, "см²": 1e-4, "м²": 1.0, "га": 10000.0, "км²": 1_000_000.0, "акр": 4046.8564224, "фут²": 0.09290304}
VOLUME = {"мл": 0.001, "л": 1.0, "м³": 1000.0, "ч. л.": 0.00492892, "ст. л.": 0.0147868, "чашка US": 0.236588, "галлон US": 3.785411784}
SPEED = {"м/с": 1.0, "км/ч": 1 / 3.6, "миль/ч": 0.44704, "узел": 0.514444, "фут/с": 0.3048}
TIME = {"мс": 0.001, "с": 1.0, "мин": 60.0, "ч": 3600.0, "сутки": 86400.0, "неделя": 604800.0}
ENERGY = {"Дж": 1.0, "кДж": 1000.0, "кал": 4.184, "ккал": 4184.0, "Вт·ч": 3600.0, "кВт·ч": 3_600_000.0, "эВ": 1.602176634e-19}
PRESSURE = {"Па": 1.0, "кПа": 1000.0, "бар": 100000.0, "атм": 101325.0, "мм рт. ст.": 133.322387415}
DATA = {"бит": 1 / 8, "байт": 1.0, "КБ": 1000.0, "МБ": 1_000_000.0, "ГБ": 1_000_000_000.0, "ТБ": 1_000_000_000_000.0, "КиБ": 1024.0, "МиБ": 1024.0**2, "ГиБ": 1024.0**3, "ТиБ": 1024.0**4}

UNITS = {
    "Длина": LENGTH, "Масса": WEIGHT, "Площадь": AREA, "Объём": VOLUME,
    "Скорость": SPEED, "Время": TIME, "Энергия": ENERGY,
    "Давление": PRESSURE, "Данные": DATA, "Температура": {"°C": 1, "°F": 1, "K": 1},
}


def convert_temperature(value: float, src: str, dest: str) -> float:
    if src not in {"C", "F", "K", "°C", "°F"} or dest not in {"C", "F", "K", "°C", "°F"}:
        raise ValueError(f"Неизвестная температурная шкала: {src} → {dest}")
    if src in {"F", "°F"}:
        celsius = (value - 32) * 5 / 9
    elif src == "K":
        celsius = value - 273.15
    else:
        celsius = value
    if celsius < -273.15:
        raise ValueError("Температура ниже абсолютного нуля")
    if dest in {"C", "°C"}:
        return celsius
    if dest in {"F", "°F"}:
        return celsius * 9 / 5 + 32
    return celsius + 273.15


def convert(value: float, category: str, src: str, dest: str) -> float:
    if category in {"Температура", "temperature", "temp"}:
        aliases = {"°C": "C", "°F": "F"}
        return convert_temperature(value, aliases.get(src, src), aliases.get(dest, dest))
    aliases = {
        "length": "Длина", "weight": "Масса", "area": "Площадь",
        "volume": "Объём", "speed": "Скорость", "time": "Время",
        "energy": "Энергия", "pressure": "Давление", "data": "Данные",
    }
    name = aliases.get(category, category)
    if name not in UNITS:
        raise ValueError(f"Неизвестная категория: {category}")
    values = UNITS[name]
    if src not in values or dest not in values:
        raise ValueError(f"Нельзя преобразовать {src} в {dest} в категории «{name}»")
    return value * values[src] / values[dest]


def convert_all(value: float, category: str, src: str) -> dict[str, float]:
    if category in {"Температура", "temperature", "temp"}:
        aliases = {"°C": "C", "°F": "F"}
        return {unit: convert_temperature(value, aliases.get(src, src), unit) for unit in ("C", "F", "K")}
    aliases = {
        "length": "Длина", "weight": "Масса", "area": "Площадь",
        "volume": "Объём", "speed": "Скорость", "time": "Время",
        "energy": "Энергия", "pressure": "Давление", "data": "Данные",
    }
    name = aliases.get(category, category)
    values = UNITS.get(name)
    if values is None or src not in values:
        raise ValueError(f"Неизвестная категория или единица: {category}, {src}")
    return {unit: value * values[src] / factor for unit, factor in values.items()}


def convert_length(value: float, src: str, dest: str) -> float:
    return convert(value, "Длина", src, dest)


def convert_weight(value: float, src: str, dest: str) -> float:
    return convert(value, "Масса", src, dest)
