"""Универсальный ИК-пульт Пульта.

Поддерживаются профили Flipper .ir / Pronto, Broadlink, USB-serial bridge
на ESP32 и named-remote команды Home Assistant. Аппаратные библиотеки
импортируются лениво, поэтому отсутствие адаптера не мешает запуску Пульта.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable


MAX_PULSES = 1024
DEFAULT_FREQUENCY = 38000
DEFAULT_BAUD = 115200
FLIPPER_HEADER = "Filetype: IR signals file\nVersion: 1\n"
COMMON_BUTTONS = [
    "Power", "Power_on", "Power_off", "Vol_up", "Vol_dn", "Mute",
    "Ch_next", "Ch_prev", "Up", "Down", "Left", "Right", "Ok",
    "Back", "Home", "Menu", "Input", "Play", "Pause", "Stop",
    "Next", "Prev", "Fast_forward", "Rewind",
]


def storage_dir() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    folder = root / "Pulpit" / "infrared"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def profiles_path() -> Path:
    return storage_dir() / "profiles.json"


def load_profiles() -> list[dict[str, Any]]:
    path = profiles_path()
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    profiles = payload.get("profiles", []) if isinstance(payload, dict) else []
    if not isinstance(profiles, list):
        return []
    cleaned = []
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        if not isinstance(profile.get("codes"), list):
            profile["codes"] = []
        profile.setdefault("name", "Мой пульт")
        profile.setdefault("category", "TV")
        profile.setdefault("brand", "")
        profile.setdefault("model", "")
        cleaned.append(profile)
    return cleaned


def save_profiles(profiles: list[dict[str, Any]]) -> Path:
    path = profiles_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(
        json.dumps({"version": 1, "profiles": profiles}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp.replace(path)
    return path


def validate_timings(timings: Iterable[int]) -> list[int]:
    values = [int(value) for value in timings]
    if not values:
        raise ValueError("ИК-сигнал не содержит импульсов.")
    if len(values) > MAX_PULSES:
        raise ValueError(f"Слишком длинный ИК-сигнал: максимум {MAX_PULSES} интервалов.")
    if len(values) < 3:
        raise ValueError("Слишком короткий ИК-сигнал.")
    if any(value <= 0 or value > 100000 for value in values):
        raise ValueError("Длительности должны быть положительными и не превышать 100000 мкс.")
    return values


def _bytes_le_hex(value: str) -> int:
    chunks = re.findall(r"[0-9A-Fa-f]{2}", value)
    if not chunks:
        raise ValueError("Пустое поле address/command.")
    return int.from_bytes(bytes(int(chunk, 16) for chunk in chunks), "little")


def _pulse_distance(data: int, bits: int, *, header: tuple[int, int], one: tuple[int, int],
                    zero: tuple[int, int], footer: int, lsb_first: bool = True) -> list[int]:
    output = [header[0], header[1]]
    positions = range(bits) if lsb_first else range(bits - 1, -1, -1)
    for position in positions:
        output.extend(one if (data >> position) & 1 else zero)
    output.append(footer)
    return output


def encode_flipper_parsed(protocol: str, address: str, command: str) -> tuple[int, list[int]]:
    """Кодирует часто встречающиеся parsed-сигналы из Flipper IR."""
    name = protocol.strip().upper()
    address_value = _bytes_le_hex(address)
    command_value = _bytes_le_hex(command)

    if name in {"NEC", "NECEXT", "NEC42", "NEC42EXT"}:
        if name in {"NEC", "NECEXT"}:
            address_bits = 8 if name == "NEC" else 16
            command_bits = 8 if name == "NEC" else 16
            data = (address_value & ((1 << address_bits) - 1))
            data |= (command_value & ((1 << command_bits) - 1)) << address_bits
            return DEFAULT_FREQUENCY, _pulse_distance(
                data, address_bits + command_bits,
                header=(9000, 4500), one=(560, 1690), zero=(560, 560), footer=560,
            )
        raise ValueError(f"Протокол {name} пока импортируется только как raw-сигнал.")

    if name == "SAMSUNG32":
        data = (address_value & 0xFFFF) | ((command_value & 0xFFFF) << 16)
        return DEFAULT_FREQUENCY, _pulse_distance(
            data, 32, header=(4500, 4500), one=(560, 1690), zero=(560, 560), footer=560,
        )

    if name in {"SIRC", "SIRC15", "SIRC20"}:
        address_bits = {"SIRC": 5, "SIRC15": 8, "SIRC20": 13}[name]
        command_bits = 7
        data = (command_value & 0x7F) | ((address_value & ((1 << address_bits) - 1)) << command_bits)
        output = [2400, 600]
        for position in range(command_bits + address_bits):
            output.extend((1200 if (data >> position) & 1 else 600, 600))
        return 40000, output[:-1]

    raise ValueError(f"Parsed-протокол {protocol} пока не поддерживается. Импортируй raw-вариант или обучи кнопку с пульта.")


def parse_flipper_ir(text: str, *, fallback_name: str = "Импортированный пульт") -> dict[str, Any]:
    """Читает стандартный Flipper .ir: raw-сигналы и основные parsed-протоколы."""
    blocks: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for raw_line in text.replace("\r", "").split("\n"):
        line = raw_line.strip()
        if not line or line.startswith("#") or line.lower().startswith(("filetype:", "version:")):
            if line == "#" and current:
                blocks.append(current)
                current = {}
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            current[key.strip().lower()] = value.strip()
    if current:
        blocks.append(current)

    codes: list[dict[str, Any]] = []
    skipped: list[str] = []
    for block in blocks:
        code_name = block.get("name", f"Кнопка {len(codes) + 1}")
        kind = block.get("type", "").lower()
        try:
            if kind == "raw":
                frequency = int(block.get("frequency", str(DEFAULT_FREQUENCY)))
                timings = validate_timings(int(value) for value in block.get("data", "").split())
            elif kind == "parsed":
                frequency, timings = encode_flipper_parsed(
                    block.get("protocol", ""),
                    block.get("address", ""),
                    block.get("command", ""),
                )
            else:
                raise ValueError("неизвестный тип сигнала")
            codes.append({
                "name": code_name,
                "kind": "raw",
                "frequency": frequency,
                "timings": timings,
                "repeat": 1,
            })
        except (ValueError, TypeError) as exc:
            skipped.append(f"{code_name}: {exc}")

    if not codes:
        reason = "; ".join(skipped[:4]) or "в файле нет кодов"
        raise ValueError(f"Не найдено поддерживаемых ИК-команд: {reason}")
    stem = fallback_name.strip() or "Импортированный пульт"
    return {
        "name": stem,
        "category": "Other",
        "brand": "",
        "model": "",
        "codes": codes,
        "import_warnings": skipped,
    }


def export_flipper_ir(profile: dict[str, Any]) -> str:
    lines = [FLIPPER_HEADER, f"# {profile.get('name', 'Pulpit remote')}"]
    exported = 0
    for code in profile.get("codes", []):
        if code.get("kind", "raw") != "raw":
            continue
        timings = validate_timings(code.get("timings", []))
        exported += 1
        name = re.sub(r"[^A-Za-z0-9_ -]", "_", str(code.get("name", "Button")))
        lines.extend([
            "#",
            f"name: {name or 'Button'}",
            "type: raw",
            f"frequency: {int(code.get('frequency', DEFAULT_FREQUENCY))}",
            "duty_cycle: 0.330000",
            "data: " + " ".join(str(value) for value in timings),
        ])
    if exported == 0:
        raise ValueError("В профиле пока нет raw-команд для экспорта в .ir.")
    return "\n".join(lines) + "\n"


def parse_pronto_hex(value: str, *, name: str = "Pronto") -> dict[str, Any]:
    """Импортирует стандартный learned Pronto HEX-код (формат 0000)."""
    words = re.findall(r"[0-9A-Fa-f]{4}", value)
    if len(words) < 6:
        raise ValueError("Pronto HEX должен содержать заголовок и хотя бы одну пару импульсов.")
    values = [int(word, 16) for word in words]
    if values[0] != 0:
        raise ValueError("Пока поддерживается только learned Pronto raw format 0000.")
    frequency_word, intro_pairs, repeat_pairs = values[1:4]
    if frequency_word <= 0:
        raise ValueError("Некорректная частота Pronto.")
    pair_count = intro_pairs + repeat_pairs
    if pair_count <= 0 or len(values) < 4 + pair_count * 2:
        raise ValueError("Pronto HEX обрезан: число импульсов не совпадает с заголовком.")
    unit_us = frequency_word * 0.241246
    frequency = int(round(1_000_000 / unit_us))
    timings = validate_timings(round(item * unit_us) for item in values[4:4 + pair_count * 2])
    return {
        "name": name.strip() or "Pronto",
        "kind": "raw",
        "frequency": frequency,
        "timings": timings,
        "repeat": 1,
    }


def broadlink_packet_from_timings(timings: Iterable[int], *, tick_us: float = 30.45) -> bytes:
    """Преобразует интервалы в Broadlink RM packet, по формату python-broadlink."""
    pulses = validate_timings(timings)
    packet = bytearray(4)
    packet[0] = 0x26
    for pulse in pulses:
        ticks = int(round(pulse / tick_us))
        if ticks <= 0:
            ticks = 1
        high, low = divmod(ticks, 256)
        if high:
            if high > 255:
                raise ValueError("ИК-импульс слишком длинный для Broadlink.")
            packet.extend((0, high, low))
        else:
            packet.append(low)
    # Broadlink IR frames use the 0x0D 0x05 trailing-silence marker.
    packet.extend((0x0D, 0x05))
    data_length = len(packet) - 4
    packet[2] = data_length & 0xFF
    packet[3] = (data_length >> 8) & 0xFF
    return bytes(packet)


def timings_from_broadlink_packet(packet: bytes, *, tick_us: float = 30.45) -> list[int]:
    if len(packet) < 5 or packet[0] != 0x26:
        raise ValueError("Неизвестный формат пакета Broadlink.")
    end = min(4 + packet[2] + (256 * packet[3]), len(packet))
    # Strip the fixed trailing-silence marker before decoding pulse lengths.
    if end - 4 >= 2 and packet[end - 2:end] == b"\x0d\x05":
        end -= 2
    values: list[int] = []
    index = 4
    while index < end:
        chunk = packet[index]
        index += 1
        if chunk == 0:
            if index + 1 >= end:
                raise ValueError("Повреждённый пакет Broadlink.")
            chunk = packet[index] * 256 + packet[index + 1]
            index += 2
        values.append(max(1, int(round(chunk * tick_us))))
    return validate_timings(values)


def make_serial_command(timings: Iterable[int], *, frequency: int = DEFAULT_FREQUENCY,
                        repeats: int = 1) -> bytes:
    values = validate_timings(timings)
    if not 20000 <= int(frequency) <= 60000:
        raise ValueError("Частота ИК-несущей должна быть в диапазоне 20–60 кГц.")
    if not 1 <= int(repeats) <= 10:
        raise ValueError("Повтор команды должен быть от 1 до 10.")
    if any(value > 65535 for value in values):
        raise ValueError("USB-ИК прошивка использует интервалы до 65535 мкс. Для более длинных кадров используй Broadlink.")
    return (
        f"SEND,{int(frequency)},{int(repeats)},"
        + ",".join(str(value) for value in values)
        + "\n"
    ).encode("ascii")


def list_serial_ports() -> list[dict[str, str]]:
    try:
        from serial.tools import list_ports
    except ImportError as exc:
        raise RuntimeError("pyserial не установлен. Обнови Пульт через requirements.txt.") from exc
    return [
        {"device": item.device, "description": item.description or item.device}
        for item in list_ports.comports()
    ]


def serial_send(port: str, timings: Iterable[int], *, frequency: int = DEFAULT_FREQUENCY,
                repeats: int = 1, baud: int = DEFAULT_BAUD) -> str:
    try:
        import serial
    except ImportError as exc:
        raise RuntimeError("pyserial не установлен.") from exc
    payload = make_serial_command(timings, frequency=frequency, repeats=repeats)
    with serial.Serial(port, baudrate=baud, timeout=2, write_timeout=3) as connection:
        connection.reset_input_buffer()
        connection.write(payload)
        connection.flush()
        response = connection.readline().decode("ascii", errors="replace").strip()
    if not response.startswith("OK"):
        raise RuntimeError(response or "USB-ИК адаптер не подтвердил передачу.")
    return response


def serial_learn(port: str, *, timeout: int = 30, baud: int = DEFAULT_BAUD) -> dict[str, Any]:
    try:
        import serial
    except ImportError as exc:
        raise RuntimeError("pyserial не установлен.") from exc
    if not 3 <= timeout <= 120:
        raise ValueError("Время обучения должно быть от 3 до 120 секунд.")
    with serial.Serial(port, baudrate=baud, timeout=0.5, write_timeout=2) as connection:
        connection.reset_input_buffer()
        connection.write(b"LEARN\n")
        connection.flush()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            line = connection.readline().decode("ascii", errors="replace").strip()
            if not line:
                continue
            if line.startswith("ERR"):
                raise RuntimeError(line)
            if line.startswith("CAPTURE,"):
                parts = line.split(",")
                frequency = int(parts[1])
                timings = validate_timings(int(value) for value in parts[2:])
                return {"frequency": frequency, "timings": timings, "kind": "raw"}
    raise TimeoutError("ИК-команда не получена. Направь пульт на приёмник и нажми кнопку ещё раз.")


def home_assistant_ping(base_url: str, token: str, *, timeout: int = 8) -> dict[str, Any]:
    base = base_url.strip().rstrip("/")
    if not base.startswith(("http://", "https://")):
        raise ValueError("Адрес Home Assistant должен начинаться с http:// или https://.")
    if not token.strip():
        raise ValueError("Укажи долгосрочный токен доступа Home Assistant.")
    request = urllib.request.Request(
        base + "/api/",
        headers={"Authorization": f"Bearer {token.strip()}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8", errors="replace")
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Home Assistant вернул HTTP {exc.code}: {details[:300]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Не удалось подключиться к Home Assistant: {exc.reason}") from exc


def home_assistant_url(base_url: str, service: str) -> str:
    base = base_url.strip().rstrip("/")
    if not base.startswith(("http://", "https://")):
        raise ValueError("Адрес Home Assistant должен начинаться с http:// или https://.")
    if service not in {"remote/send_command", "remote/learn_command"}:
        raise ValueError("Недопустимый сервис Home Assistant.")
    return f"{base}/api/services/{service}"


def home_assistant_service(base_url: str, token: str, service: str, payload: dict[str, Any],
                           *, timeout: int = 90) -> Any:
    if not token.strip():
        raise ValueError("Укажи долгосрочный токен доступа Home Assistant.")
    url = home_assistant_url(base_url, service)
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token.strip()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content = response.read().decode("utf-8", errors="replace")
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Home Assistant вернул HTTP {exc.code}: {details[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Не удалось подключиться к Home Assistant: {exc.reason}") from exc


def home_assistant_send(base_url: str, token: str, entity_id: str,
                        device: str, command: str, *, repeats: int = 1) -> Any:
    if not entity_id.strip().startswith("remote."):
        raise ValueError("Укажи сущность дистанционного управления вида remote.living_room.")
    if not command.strip():
        raise ValueError("Название команды не должно быть пустым.")
    payload: dict[str, Any] = {
        "entity_id": entity_id.strip(),
        "command": command.strip(),
        "num_repeats": max(1, min(int(repeats), 10)),
    }
    if device.strip():
        payload["device"] = device.strip()
    return home_assistant_service(base_url, token, "remote/send_command", payload)


def home_assistant_learn(base_url: str, token: str, entity_id: str,
                         device: str, command: str, *, timeout: int = 30) -> Any:
    if not entity_id.strip().startswith("remote."):
        raise ValueError("Укажи сущность дистанционного управления вида remote.living_room.")
    if not device.strip() or not command.strip():
        raise ValueError("Для обучения нужны название устройства и кнопки.")
    payload = {
        "entity_id": entity_id.strip(),
        "device": device.strip(),
        "command": command.strip(),
        "command_type": "ir",
        "timeout": max(3, min(int(timeout), 120)),
    }
    return home_assistant_service(base_url, token, "remote/learn_command", payload, timeout=timeout + 15)


def broadlink_discover(timeout: int = 5) -> list[Any]:
    """Находит совместимые RM-адаптеры через локальный UDP broadcast."""
    try:
        import broadlink
    except ImportError as exc:
        raise RuntimeError("Библиотека broadlink не установлена. Установи обновление Пульта.") from exc
    if not 2 <= timeout <= 30:
        raise ValueError("Время поиска должно быть от 2 до 30 секунд.")
    devices = list(broadlink.discover(timeout=timeout) or [])
    for device in devices:
        try:
            device.auth()
        except Exception:
            # Не скрываем устройство из списка: пользователь увидит ошибку при отправке.
            pass
    return devices


def broadlink_send(device: Any, packet: bytes) -> None:
    if not packet or packet[0] != 0x26:
        raise ValueError("Broadlink ожидает корректный ИК-пакет.")
    device.send_data(packet)


def broadlink_learn(device: Any, timeout: int = 25) -> dict[str, Any]:
    """Обучает кнопку через Broadlink RM, используя его штатный learn/check API."""
    if not 3 <= timeout <= 120:
        raise ValueError("Время обучения должно быть от 3 до 120 секунд.")
    device.enter_learning()
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            packet = bytes(device.check_data())
            if packet and packet[0] == 0x26:
                timings = timings_from_broadlink_packet(packet)
                return {
                    "kind": "raw",
                    "frequency": DEFAULT_FREQUENCY,
                    "timings": timings,
                    "broadlink_hex": packet.hex(),
                }
        except Exception as exc:  # noqa: BLE001
            # Legacy broadlink 0.19 signals "no code yet" with ReadError/StorageError.
            if type(exc).__name__ not in {"ReadError", "StorageError", "NetworkTimeoutError"}:
                raise
            last_error = exc
        time.sleep(0.5)
    if last_error is not None:
        raise TimeoutError("Broadlink не получил команду за отведённое время.") from last_error
    raise TimeoutError("Broadlink не получил сигнал. Направь штатный пульт на RM и нажми кнопку.")


class BroadlinkManager:
    """Тонкая оболочка синхронной библиотеки Broadlink 0.19."""
    def __init__(self) -> None:
        self.devices: list[Any] = []

    def discover(self, timeout: int = 5) -> list[Any]:
        self.devices = broadlink_discover(timeout=timeout)
        return self.devices

    def send(self, device: Any, code: dict[str, Any]) -> None:
        packet_hex = code.get("broadlink_hex")
        packet = bytes.fromhex(packet_hex) if packet_hex else broadlink_packet_from_timings(code.get("timings", []))
        broadlink_send(device, packet)

    def learn(self, device: Any, timeout: int = 25) -> dict[str, Any]:
        return broadlink_learn(device, timeout=timeout)


BROADLINK = BroadlinkManager()

def device_label(device: Any) -> str:
    host = getattr(device, "host", None)
    if isinstance(host, (tuple, list)) and host:
        host_value = str(host[0])
    else:
        host_value = str(host or getattr(device, "ip", "неизвестный IP"))
    model = str(getattr(device, "model", "") or getattr(device, "type", "") or "Broadlink")
    return f"{model} · {host_value}"


def send_code_broadlink(device: Any, code: dict[str, Any]) -> None:
    """Совместимый синхронный помощник для Broadlink worker thread."""
    if code.get("kind", "raw") != "raw":
        raise ValueError("Для Broadlink требуется raw-ИК-код.")
    packet_hex = code.get("broadlink_hex")
    packet = bytes.fromhex(packet_hex) if packet_hex else broadlink_packet_from_timings(code.get("timings", []))
    broadlink_send(device, packet)


def learn_code_broadlink(device: Any, timeout: int = 25) -> dict[str, Any]:
    return broadlink_learn(device, timeout=timeout)


def import_pronto_file(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    return parse_pronto_hex(source.read_text(encoding="utf-8-sig"), name=source.stem)


def import_flipper_file(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    return parse_flipper_ir(source.read_text(encoding="utf-8-sig"), fallback_name=source.stem)


def make_profile(name: str, category: str = "TV", brand: str = "", model: str = "") -> dict[str, Any]:
    return {
        "id": f"{int(time.time() * 1000):x}",
        "name": name.strip() or "Мой пульт",
        "category": category.strip() or "Other",
        "brand": brand.strip(),
        "model": model.strip(),
        "codes": [],
    }


def add_code(profile: dict[str, Any], code: dict[str, Any]) -> None:
    name = str(code.get("name", "")).strip()
    if not name:
        raise ValueError("У кнопки должно быть название.")
    if any(str(existing.get("name", "")).casefold() == name.casefold() for existing in profile.get("codes", [])):
        raise ValueError(f"Кнопка «{name}» уже существует.")
    normalized = dict(code)
    normalized["name"] = name
    if normalized.get("kind", "raw") == "raw":
        normalized["timings"] = validate_timings(normalized.get("timings", []))
        normalized["frequency"] = int(normalized.get("frequency", DEFAULT_FREQUENCY))
    profile.setdefault("codes", []).append(normalized)


def remove_code(profile: dict[str, Any], code_name: str) -> bool:
    before = len(profile.get("codes", []))
    profile["codes"] = [code for code in profile.get("codes", []) if code.get("name") != code_name]
    return len(profile["codes"]) != before
