"""Проверка движков без запуска окон Windows."""

from __future__ import annotations

from pathlib import Path
import json
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from PIL import Image

from pulpit.engines import converters, editors, office_bridge, site_builder, units
from pulpit.engines.images import edit_image, image_info


def test_image_roundtrip_and_site_zip(tmp_path: Path) -> None:
    image = tmp_path / "кот.png"
    Image.new("RGBA", (24, 12), (196, 92, 38, 255)).save(image)
    jpeg = converters.convert_image(image, tmp_path / "кот.jpg")
    png = converters.convert_image(jpeg, tmp_path / "back.png")
    assert jpeg.stat().st_size > 16
    assert png.read_bytes().startswith(b"\x89PNG")
    result = site_builder.build_site(tmp_path / "site", "Галерея", "Без сети", "#c45c26", [{"title": "Главная", "body": "Привет из zip"}], [str(image)])
    archive = Path(result["zip"])
    assert archive.exists() and archive.stat().st_size > 32
    with ZipFile(archive) as packed:
        names = packed.namelist()
    assert any(name.startswith("images/") and name.endswith(".png") for name in names)
    assert "Привет из zip" in (tmp_path / "site" / "index.html").read_text(encoding="utf-8")


def test_editors_and_markdown_safety() -> None:
    stats = editors.text_stats("раз два")
    assert stats["words"] == 2
    html = editors.markdown_to_html("# Заголовок\n\n- пункт\n\n**важно**")
    assert "<h1>" in html and "<li>" in html and "<strong>важно</strong>" in html
    unsafe = editors.markdown_to_html('<img src=x onerror="alert(1)">\n\n[опасно](javascript:alert(1))')
    assert "<img" not in unsafe and "javascript:" not in unsafe
    encoded_scheme = editors.markdown_to_html("[обход](javascript&#58;alert(1))")
    assert "javascript" not in encoded_scheme
    assert editors.transform_text("б\nа\nб", "unique_lines") == "б\nа"
    replaced, count = editors.find_replace("Кот кот", "кот", "пёс", ignore_case=True)
    assert replaced == "пёс пёс" and count == 2
    assert "Кот" in editors.compare_text("Кот\n", "Пёс\n")


def test_office_roundtrip(tmp_path: Path) -> None:
    docx = office_bridge.write_docx(tmp_path / "note.docx", "Отчёт", ["Строка для Word", "## Раздел"])
    xlsx = office_bridge.write_xlsx(tmp_path / "sheet.xlsx", "Пульт", [["Имя", "Значение"], ["1", "Excel видит"]], headers=True)
    pptx = office_bridge.write_pptx(tmp_path / "deck.pptx", "Пульт", [("Слайд", "PowerPoint видит")])
    assert "Word" in office_bridge.read_docx(docx) and "Раздел" in office_bridge.read_docx(docx)
    assert "Excel" in office_bridge.read_xlsx(xlsx)
    assert "PowerPoint" in office_bridge.read_pptx(pptx)
    assert "Excel" in office_bridge.read_office(xlsx)


def test_site_zip(tmp_path: Path) -> None:
    image = tmp_path / "pic.png"
    Image.new("RGB", (8, 8), (20, 20, 20)).save(image)
    result = site_builder.build_site(tmp_path / "site", "Галерея", "Без сети", "#c45c26", [{"title": "Главная", "body": "Привет из zip"}], [str(image)])
    assert Path(result["zip"]).exists()
    assert (tmp_path / "site" / "index.html").exists()
    assert "Привет из zip" in (tmp_path / "site" / "index.html").read_text(encoding="utf-8")


def test_constructor_template_undo_and_export(tmp_path: Path) -> None:
    from pulpit.engines.constructor import Constructor
    from pulpit.engines.site_project import save_project
    from pulpit.engines.site_render import export_project

    doc = Constructor()
    doc.apply_template("landing")
    assert any(block["type"] == "features" for block in doc.page()["blocks"])
    before = len(doc.page()["blocks"])
    doc.add("faq")
    assert len(doc.page()["blocks"]) == before + 1
    assert doc.undo()
    assert len(doc.page()["blocks"]) == before
    save_project(tmp_path / "project", doc.project)
    result = export_project(tmp_path / "project", tmp_path / "site")
    html = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert "features" in html
    assert Path(result["zip"]).stat().st_size > 32


def test_drag_and_button_constructor(tmp_path: Path) -> None:
    from pulpit.engines.constructor import Constructor
    from pulpit.engines.site_project import save_project
    from pulpit.engines.site_render import export_project

    doc = Constructor()
    doc.page()["blocks"] = []
    first = doc.add("text")
    second = doc.add("heading")
    doc.move_to(second["id"], 0)
    assert doc.page()["blocks"][0]["id"] == second["id"]
    assert doc.page()["blocks"][1]["id"] == first["id"]
    doc.insert_button({"text": "Жми", "href": "page-1.html", "style": "outline", "size": "lg", "shape": "pill", "color": "#112233"})
    save_project(tmp_path / "project", doc.project)
    export_project(tmp_path / "project", tmp_path / "site")
    html = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert "button outline lg pill" in html and "Жми" in html


def test_preview_inlines_style_and_image(tmp_path: Path) -> None:
    from pulpit.engines.preview_doc import standalone

    assets = tmp_path / "assets"
    assets.mkdir()
    file = assets / "pic.png"
    Image.new("RGB", (4, 4), (10, 20, 30)).save(file)
    document = standalone('<link rel="stylesheet" href="style.css"><img src="assets/pic.png" alt="pic">', "body { color: #112233; }", tmp_path)
    assert "<style>" in document and "style.css" not in document
    assert "data:image/png;base64," in document


def test_units() -> None:
    assert abs(units.convert_temperature(0, "C", "F") - 32) < 0.01
    assert abs(units.convert_length(1, "м", "см") - 100) < 0.01
    assert abs(units.convert(1, "Площадь", "га", "м²") - 10000) < 0.01
    assert abs(units.convert(1, "Данные", "ГиБ", "МиБ") - 1024) < 0.01
    assert abs(units.convert(1, "Скорость", "км/ч", "м/с") - (1 / 3.6)) < 0.0001
    with pytest.raises(ValueError):
        units.convert_temperature(-300, "C", "K")


def test_json_csv_and_xml_conversions(tmp_path: Path) -> None:
    source = tmp_path / "data.json"
    source.write_text('[{"name":"Иван","age":22,"tags":["a","b"]},{"name":"Анна","age":25}]', encoding="utf-8")
    csv_path = converters.json_to_csv(source, tmp_path / "data.csv", delimiter=";")
    assert "name;age;tags" in csv_path.read_text(encoding="utf-8-sig")
    json_path = converters.csv_to_json(csv_path, tmp_path / "back.json")
    assert json.loads(json_path.read_text(encoding="utf-8"))[0]["name"] == "Иван"
    xml_path = converters.json_to_xml(source, tmp_path / "data.xml")
    back = converters.xml_to_json(xml_path, tmp_path / "back.xml.json")
    assert "Иван" in back.read_text(encoding="utf-8")
    assert converters.validate_json('{"ok":true}') == (True, "JSON корректен")
    assert not converters.validate_json("{bad")[0]


def test_zip_safe_unpack_and_traversal_rejection(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "file.txt").write_text("полезное содержимое", encoding="utf-8")
    archive_path = converters.pack_zip(source, tmp_path / "bundle.zip")
    info = converters.inspect_zip(archive_path)
    assert info["files"] == 1
    out = converters.unpack_zip(archive_path, tmp_path / "out")
    assert (out / "file.txt").read_text(encoding="utf-8") == "полезное содержимое"
    malicious = tmp_path / "bad.zip"
    with ZipFile(malicious, "w", ZIP_DEFLATED) as archive:
        archive.writestr("../outside.txt", "не должен появиться")
    with pytest.raises(ValueError, match="Небезопасный путь"):
        converters.unpack_zip(malicious, tmp_path / "bad-out")
    assert not (tmp_path / "outside.txt").exists()


def test_zip_rejects_windows_absolute_paths(tmp_path: Path) -> None:
    archive_path = tmp_path / "windows.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("C:\\Windows\\evil.txt", "no")
    with pytest.raises(ValueError):
        converters.unpack_zip(archive_path, tmp_path / "windows-out")


def test_image_transform_and_metadata(tmp_path: Path) -> None:
    source = tmp_path / "photo.png"
    Image.new("RGBA", (40, 20), (120, 80, 40, 255)).save(source)
    target = edit_image(source, tmp_path / "edited.png", width=20, height=20, fit="cover", rotate=90, grayscale=True, brightness=1.1, watermark="Пульт")
    info = image_info(target)
    assert info["width"] == 20 and info["height"] == 20
    assert info["format"] == "PNG"


def test_system_snapshot() -> None:
    from pulpit.system_info import format_snapshot, snapshot
    info = snapshot()
    assert "os" in info and "disk_free" in info and "python" in info
    report = format_snapshot(info)
    assert "Операционная система" in report and "Свободно на диске" in report
