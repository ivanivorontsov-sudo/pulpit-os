"""Проверка движков без окна. Office открывать не обязан."""

from pathlib import Path

from PIL import Image

from pulpit.engines import converters, editors, office_bridge, site_builder, units


def test_image_and_tables(tmp_path: Path) -> None:
    image = tmp_path / "cat.png"
    Image.new("RGB", (32, 16), (196, 92, 38)).save(image)
    webp = converters.convert_image(image, tmp_path / "cat.webp")
    assert webp.exists()
    payload = tmp_path / "rows.json"
    payload.write_text('[{"имя": "Пульт", "дело": "zip"}]', encoding="utf-8")
    csv_path = converters.json_to_csv(payload, tmp_path / "rows.csv")
    back = converters.csv_to_json(csv_path, tmp_path / "back.json")
    assert "Пульт" in back.read_text(encoding="utf-8")


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
