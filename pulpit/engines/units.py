"""Единицы измерения. Калькулятор Windows это умеет, но прячет."""

from __future__ import annotations

LENGTH = {"мм": 0.001, "см": 0.01, "м": 1.0, "км": 1000.0, "дюйм": 0.0254, "фут": 0.3048, "миля": 1609.344}
WEIGHT = {"мг": 0.000001, "г": 0.001, "кг": 1.0, "т": 1000.0, "унция": 0.0283495, "фунт": 0.453592}


def convert_length(value: float, src: str, dest: str) -> float:
    return value * LENGTH[src] / LENGTH[dest]


def convert_weight(value: float, src: str, dest: str) -> float:
    return value * WEIGHT[src] / WEIGHT[dest]


def convert_temperature(value: float, src: str, dest: str) -> float:
    celsius = value
    if src == "F":
        celsius = (value - 32) * 5 / 9
    elif src == "K":
        celsius = value - 273.15
    if dest == "C":
        return celsius
    if dest == "F":
        return celsius * 9 / 5 + 32
    if dest == "K":
        return celsius + 273.15
    raise ValueError(dest)
