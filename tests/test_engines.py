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
    assert "button outline lg pill" in html
    assert "Жми" in html


def test_preview_inlines_style_and_image(tmp_path: Path) -> None:
    from pulpit.engines.preview_doc import standalone

    image = tmp_path / "assets"
    image.mkdir()
    file = image / "pic.png"
    Image.new("RGB", (4, 4), (10, 20, 30)).save(file)
    html = '<link rel="stylesheet" href="style.css"><img src="assets/pic.png" alt="pic">'
    document = standalone(html, "body { color: #112233; }", tmp_path)
    assert "<style>" in document
    assert "style.css" not in document
    assert "data:image/png;base64," in document


def test_units() -> None:
    assert abs(units.convert_temperature(0, "C", "F") - 32) < 0.01
    assert abs(units.convert_length(1, "м", "см") - 100) < 0.01
