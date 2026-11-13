"""Проверки расширенного Office: сохранение исходных объектов и операции диапазонов."""
from __future__ import annotations

from pathlib import Path

from docx import Document
from openpyxl import Workbook
from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.util import Inches

from pulpit.engines import office_pro, office_suite


def test_word_template_keeps_headers_and_roundtrips_images(tmp_path: Path) -> None:
    picture = tmp_path / "word-image.png"
    Image.new("RGB", (64, 32), (120, 80, 40)).save(picture)
    source = tmp_path / "source.docx"
    template = Document()
    template.sections[0].orientation = 1
    template.sections[0].header.paragraphs[0].text = "Корпоративная шапка"
    template.add_paragraph("Старое содержимое")
    template.add_picture(str(picture), width=Inches(1.5))
    template.save(source)

    editor_text = office_pro.read_word_document(source)
    assert "![Изображение]" in editor_text
    assert "Старое содержимое" in editor_text
    editor_text += "\n\n## Новый раздел\n\n[Официальный сайт](https://example.com)\n\n[[PAGE_BREAK]]"
    output = office_pro.create_word_document(
        tmp_path / "result.docx", "Отчёт", editor_text,
        author="Пульт", template_path=source, orientation="landscape", page_numbers=True,
    )
    result = Document(output)
    assert result.core_properties.title == "Отчёт"
    assert result.sections[0].header.paragraphs[0].text == "Корпоративная шапка"
    assert len(result.inline_shapes) == 1
    assert result.sections[0].page_width > result.sections[0].page_height
    assert any("Новый раздел" in p.text for p in result.paragraphs)
    assert any("hyperlink" in child.tag for p in result.paragraphs for child in p._p.iter())


def test_excel_bulk_range_formatting_validation_and_search(tmp_path: Path) -> None:
    book = Workbook()
    sheet = book.active
    sheet.title = "Сводка"
    office_pro.excel_paste_tsv(book, "Сводка", "A1", "Товар\tКол-во\tСтатус\nЧай\t10\tЕсть\nКофе\t20\tНет")
    assert sheet["B2"].value == 10
    assert sheet["B3"].value == 20
    assert office_pro.excel_copy_range(book, "Сводка", "A1:B2") == "Товар\tКол-во\nЧай\t10"

    office_pro.excel_format_range(book, "Сводка", "A1:C1", bold=True, fill="7A4B32", font_color="FFFFFF")
    assert sheet["A1"].font.bold
    assert sheet["A1"].fill.fgColor.rgb.endswith("7A4B32")
    office_pro.excel_add_dropdown(book, "Сводка", "C2:C20", ["Есть", "Нет", "Ожидается"])
    office_pro.excel_add_color_scale(book, "Сводка", "B2:B20")
    office_pro.excel_add_data_bar(book, "Сводка", "B2:B20")
    table_name = office_pro.excel_add_table(book, "Сводка", "A1:C3", name="Sales")
    assert table_name == "Sales"
    assert office_pro.excel_find_replace(book, "Кофе", "Чайный кофе") == 1
    assert sheet["A3"].value == "Чайный кофе"

    office_pro.excel_insert_rows(book, "Сводка", 2)
    office_pro.excel_insert_columns(book, "Сводка", 2)
    assert sheet.max_row == 4
    assert sheet.max_column == 4
    office_pro.excel_delete_rows(book, "Сводка", 2)
    office_pro.excel_delete_columns(book, "Сводка", 2)
    assert sheet.max_row == 3
    assert sheet.max_column == 3

    path = office_suite.save_excel_workbook(book, tmp_path / "advanced.xlsx")
    saved = office_suite.open_excel_workbook(path)
    assert saved["Сводка"]["A1"].font.bold
    assert "Sales" in saved["Сводка"].tables
    assert len(saved["Сводка"].data_validations.dataValidation) == 1

    office_pro.excel_insert_rows(book, "Сводка", 2)
    office_pro.excel_insert_columns(book, "Сводка", 2)
    assert sheet.max_row == 4
    assert sheet.max_column == 4
    office_pro.excel_delete_rows(book, "Сводка", 2)
    office_pro.excel_delete_columns(book, "Сводка", 2)
    assert sheet.max_row == 3
    assert sheet.max_column == 3


def test_powerpoint_template_preserves_shapes_and_images(tmp_path: Path) -> None:
    picture = tmp_path / "slide-image.png"
    Image.new("RGB", (48, 48), (30, 80, 140)).save(picture)
    source = tmp_path / "source.pptx"
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    slide.shapes.title.text = "Старый заголовок"
    slide.placeholders[1].text = "Старый текст"
    slide.shapes.add_picture(str(picture), Inches(7), Inches(2), width=Inches(2))
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1), Inches(4), Inches(2), Inches(1))
    shape.text = "Не трогать"
    slide.notes_slide.notes_text_frame.text = "Заметка докладчика"
    presentation.save(source)

    loaded = office_pro.read_presentation(source)
    assert loaded["slides"][0]["notes"] == "Заметка докладчика"
    loaded["slides"][0]["title"] = "Обновлённый заголовок"
    loaded["slides"][0]["body"] = "Обновлённый текст"
    loaded["slides"].append({
        "title": "Новый слайд", "body": "Новый контент", "notes": "Заметки",
        "images": [str(picture)], "table": [["Колонка 1", "Колонка 2"], ["A", "B"]], "_source_index": None,
    })
    output = office_pro.create_presentation(
        tmp_path / "edited.pptx", "Шаблон сохранён", loaded["slides"],
        author="Тест", template_path=source,
    )
    updated = Presentation(output)
    assert len(updated.slides) == 2
    first = updated.slides[0]
    assert first.shapes.title.text == "Обновлённый заголовок"
    assert any(s.shape_type == MSO_SHAPE_TYPE.PICTURE for s in first.shapes)
    assert any(getattr(s, "has_text_frame", False) and "Не трогать" in s.text for s in first.shapes)
    assert len([s for s in updated.slides[1].shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]) == 1
    assert any(s.has_table for s in updated.slides[1].shapes)
    assert updated.core_properties.title == "Шаблон сохранён"


def test_generated_powerpoint_cover_survives_second_save(tmp_path: Path) -> None:
    first = office_pro.create_presentation(
        tmp_path / "created.pptx", "Титульный лист",
        [{"title": "Первый", "body": "Текст", "_source_index": None}],
    )
    opened = office_pro.read_presentation(first)
    assert len(opened["slides"]) == 2
    # The Pulpit editor displays content slides separately from its generated cover.
    content_slide = opened["slides"][1]
    second = office_pro.create_presentation(
        tmp_path / "saved-again.pptx", opened["title"], [content_slide],
        template_path=first,
    )
    reopened = Presentation(second)
    assert len(reopened.slides) == 2
    assert reopened.slides[0].placeholders[1].text == "Создано в Пульте"
