"""Проверка движков без окна. Office открывать не обязан."""

from pathlib import Path

from PIL import Image

from pulpit.engines import converters, editors, office_bridge, site_builder, units


def test_image_roundtrip_and_site_zip(tmp_path: Path) -> None:
    image = tmp_path / "кот.png"
    Image.new("RGBA", (24, 12), (196, 92, 38, 255)).save(image)
    jpeg = converters.convert_image(image, tmp_path / "кот.jpg")
    png = converters.convert_image(jpeg, tmp_path / "back.png")
    assert jpeg.stat().st_size > 16
    assert png.read_bytes().startswith(b"\x89PNG")
    result = site_builder.build_site(
        tmp_path / "site",
        "Галерея",
        "Без сети",
        "#c45c26",
        [{"title": "Главная", "body": "Привет из zip"}],
        [str(image)],
    )
    archive = Path(result["zip"])
    assert archive.exists() and archive.stat().st_size > 32
    from zipfile import ZipFile

    names = ZipFile(archive).namelist()
    assert any(name.startswith("images/") and name.endswith(".png") for name in names)
    assert "Привет из zip" in (tmp_path / "site" / "index.html").read_text(encoding="utf-8")


def test_editors() -> None:
    stats = editors.text_stats("раз два")
    assert stats["words"] == 2
    html = editors.markdown_to_html("# Заголовок\n\n- пункт")
    assert "<h1>" in html and "<li>" in html


def test_office_roundtrip(tmp_path: Path) -> None:
    docx = office_bridge.write_docx(tmp_path / "note.docx", "Отчёт", ["Строка для Word"])
    xlsx = office_bridge.write_xlsx(tmp_path / "sheet.xlsx", "Пульт", [["1", "Excel видит"]])
    pptx = office_bridge.write_pptx(tmp_path / "deck.pptx", "Пульт", [("Слайд", "PowerPoint видит")])
    assert "Word" in office_bridge.read_docx(docx) or "Строка" in office_bridge.read_docx(docx)
    assert "Excel" in office_bridge.read_xlsx(xlsx)
    assert "PowerPoint" in office_bridge.read_pptx(pptx)


def test_site_zip(tmp_path: Path) -> None:
    image = tmp_path / "pic.png"
    Image.new("RGB", (8, 8), (20, 20, 20)).save(image)
    result = site_builder.build_site(
        tmp_path / "site",
        "Галерея",
        "Без сети",
        "#c45c26",
        [{"title": "Главная", "body": "Привет из zip"}],
        [str(image)],
    )
    assert Path(result["zip"]).exists()
    assert (tmp_path / "site" / "index.html").exists()
    assert "Привет из zip" in (tmp_path / "site" / "index.html").read_text(encoding="utf-8")


def test_units() -> None:
    assert abs(units.convert_temperature(0, "C", "F") - 32) < 0.01
    assert abs(units.convert_length(1, "м", "см") - 100) < 0.01
