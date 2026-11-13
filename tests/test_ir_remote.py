"""Тесты универсального ИК-пульта: форматы, профили и адаптерные payloads."""
from __future__ import annotations

import re

import pytest

from pulpit.engines import ir_remote


RAW_FILE = """Filetype: IR signals file
Version: 1
#
name: Power
type: raw
frequency: 38000
duty_cycle: 0.330000
data: 9000 4500 560 560 560 1690 560
#
name: Volume_Up
type: raw
frequency: 38000
duty_cycle: 0.330000
data: 9000 4500 560 1690 560 560 560
"""

PARSED_NEC_FILE = """Filetype: IR signals file
Version: 1
#
name: Power
type: parsed
protocol: NEC
address: 01 00 00 00
command: 15 00 00 00
"""


def test_parse_and_export_flipper_raw_roundtrip() -> None:
    profile = ir_remote.parse_flipper_ir(RAW_FILE, fallback_name="LG TV")
    assert profile["name"] == "LG TV"
    assert len(profile["codes"]) == 2
    assert profile["codes"][0]["timings"] == [9000, 4500, 560, 560, 560, 1690, 560]

    exported = ir_remote.export_flipper_ir(profile)
    restored = ir_remote.parse_flipper_ir(exported, fallback_name="Again")
    assert [item["name"] for item in restored["codes"]] == ["Power", "Volume_Up"]
    assert restored["codes"][1]["timings"] == profile["codes"][1]["timings"]


def test_parsed_nec_is_encoded_to_raw_timings() -> None:
    profile = ir_remote.parse_flipper_ir(PARSED_NEC_FILE)
    code = profile["codes"][0]
    assert code["frequency"] == 38000
    assert code["timings"][:2] == [9000, 4500]
    assert len(code["timings"]) == 2 + 16 * 2 + 1
    assert code["timings"][-1] == 560


def test_parsed_samsung_and_sony_protocols() -> None:
    samsung = ir_remote.encode_flipper_parsed("Samsung32", "01 00 00 00", "10 00 00 00")
    sony = ir_remote.encode_flipper_parsed("SIRC15", "02 00 00 00", "15 00 00 00")
    assert samsung[0] == 38000
    assert len(samsung[1]) == 2 + 32 * 2 + 1
    assert sony[0] == 40000
    assert sony[1][:2] == [2400, 600]
    assert len(sony[1]) == 2 + 15 * 2 - 1


def test_unsupported_parsed_signal_is_reported_not_silently_faked() -> None:
    file_text = PARSED_NEC_FILE.replace("protocol: NEC", "protocol: RC6")
    with pytest.raises(ValueError, match="поддерживаемых"):
        ir_remote.parse_flipper_ir(file_text)


def test_pronto_hex_conversion() -> None:
    code = ir_remote.parse_pronto_hex(
        "0000 006D 0002 0000 015B 00AD 0016 0016", name="Power"
    )
    assert code["name"] == "Power"
    assert 37000 <= code["frequency"] <= 39000
    assert len(code["timings"]) == 4
    assert code["timings"][0] > code["timings"][1]


def test_broadlink_packet_roundtrip_is_within_tick_precision() -> None:
    timings = [9000, 4500, 560, 1690, 560, 560, 560]
    packet = ir_remote.broadlink_packet_from_timings(timings)
    assert packet[0] == 0x26
    assert packet.endswith(b"\x0d\x05")
    restored = ir_remote.timings_from_broadlink_packet(packet)
    assert len(restored) == len(timings)
    assert all(abs(left - right) <= 16 for left, right in zip(timings, restored))


def test_serial_command_is_validated_and_framed() -> None:
    packet = ir_remote.make_serial_command([9000, 4500, 560, 560, 560], frequency=38000, repeats=2)
    assert packet.startswith(b"SEND,38000,2,")
    assert packet.endswith(b"\n")
    with pytest.raises(ValueError, match="65535"):
        ir_remote.make_serial_command([100000, 4500, 560])
    with pytest.raises(ValueError, match="20"):
        ir_remote.make_serial_command([9000, 4500, 560], frequency=1000)


def test_home_assistant_rest_service_validation() -> None:
    assert ir_remote.home_assistant_url(
        "http://homeassistant.local:8123/", "remote/send_command"
    ) == "http://homeassistant.local:8123/api/services/remote/send_command"
    with pytest.raises(ValueError):
        ir_remote.home_assistant_url("file:///tmp", "remote/send_command")
    with pytest.raises(ValueError):
        ir_remote.home_assistant_url("http://ha", "light/turn_on")


def test_profile_code_management() -> None:
    profile = ir_remote.make_profile("Samsung", "TV", "Samsung", "UE55")
    ir_remote.add_code(profile, {
        "name": "Power", "kind": "raw", "frequency": 38000,
        "timings": [9000, 4500, 560, 560, 560],
    })
    assert len(profile["codes"]) == 1
    with pytest.raises(ValueError, match="уже существует"):
        ir_remote.add_code(profile, {
            "name": "Power", "kind": "raw", "frequency": 38000,
            "timings": [9000, 4500, 560],
        })
    assert ir_remote.remove_code(profile, "Power")
    assert not ir_remote.remove_code(profile, "Power")


def test_home_assistant_named_command_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}
    def fake_service(base_url, token, service, payload, **kwargs):
        captured.update({"base_url": base_url, "token": token, "service": service, "payload": payload})
        return {"ok": True}
    monkeypatch.setattr(ir_remote, "home_assistant_service", fake_service)
    result = ir_remote.home_assistant_send(
        "http://ha:8123", "secret-token", "remote.living_room", "television", "vol_up", repeats=2
    )
    assert result == {"ok": True}
    assert captured["service"] == "remote/send_command"
    assert captured["payload"]["entity_id"] == "remote.living_room"
    assert captured["payload"]["device"] == "television"
    assert captured["payload"]["command"] == "vol_up"
    assert captured["payload"]["num_repeats"] == 2


def test_broadlink_manager_uses_sync_device_api(monkeypatch: pytest.MonkeyPatch) -> None:
    class ReadError(Exception):
        pass

    packet = ir_remote.broadlink_packet_from_timings([9000, 4500, 560, 560, 560])
    class FakeDevice:
        host = ("192.168.1.50", 80)
        type = "RM4"
        def __init__(self):
            self.authenticated = False
            self.sent = []
            self.learning = False
            self.reads = 0
        def auth(self):
            self.authenticated = True
        def send_data(self, data):
            self.sent.append(data)
        def enter_learning(self):
            self.learning = True
        def check_data(self):
            self.reads += 1
            if self.reads == 1:
                raise ReadError("No learned code yet")
            return packet

    device = FakeDevice()
    class FakeBroadlink:
        @staticmethod
        def discover(timeout=5):
            return [device]
    monkeypatch.setitem(__import__("sys").modules, "broadlink", FakeBroadlink)

    manager = ir_remote.BroadlinkManager()
    assert manager.discover() == [device]
    assert device.authenticated
    manager.send(device, {"kind": "raw", "timings": [9000, 4500, 560, 560, 560]})
    assert device.sent[-1][0] == 0x26
    learned = manager.learn(device, timeout=3)
    assert device.learning
    assert learned["kind"] == "raw"
    assert len(learned["timings"]) == 5
    assert all(abs(left - right) <= 16 for left, right in zip(
        learned["timings"], [9000, 4500, 560, 560, 560]
    ))
