"""Тесты офисного набора Пульта."""
from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook

from pulpit.engines import office_suite


def test_word_docx_roundtrip_with_styles_and_table(tmp_path: Path) -> None:
    target = office_suite.create_word_document(
        tmp_path / "brief.docx",
        "План проекта",
        "# Цель\n\nОбычный текст с **важным** и *курсивом*.\n\n"
        "- Первый пункт\n- Второй пункт\n\n"
        "| Имя | Значение |\n| --- | --- |\n| Тест | 42 |\n\n> Цитата",
        author="Автор",
        subject="Проверка",
    )
    assert target.is_file()
    text = office_suite.read_word_document(target)
    meta = office_suite.word_metadata(target)
    assert "# Цель" in text
    assert "**важным**" in text
    assert "| Имя | Значение |" in text
    assert meta["title"] == "План проекта"
    assert meta["author"] == "Автор"
    assert meta["tables"] == 1
    assert meta["paragraphs"] >= 4


def test_excel_cells_sheets_charts_and_save(tmp_path: Path) -> None:
    book = Workbook()
    sheet = book.active
    sheet.title = "Продажи"
    sheet.append(["Товар", "Количество"])
    sheet.append(["Карандаши", 10])
    sheet.append(["Тетради", 5])
    sheet.append(["Итого", "=SUM(B2:B3)"])
    office_suite.format_excel_sheet(sheet, headers=True)
    office_suite.add_excel_chart(book, "Продажи", chart_type="bar", title="Продажи")
    office_suite.set_excel_cell(book, "Продажи", "C2", "проверка")
    assert sheet["B4"].value == "=SUM(B2:B3)"
    assert len(sheet._charts) == 1

    path = office_suite.save_excel_workbook(book, tmp_path / "sales.xlsx")
    opened = office_suite.open_excel_workbook(path)
    snapshot = office_suite.excel_sheet_snapshot(opened, "Продажи")
    assert snapshot["rows"][1][0] == "Карандаши"
    assert opened["Продажи"]["C2"].value == "проверка"
    assert opened["Продажи"].freeze_panes == "A2"

    new_name = office_suite.add_excel_sheet(opened, "Архив")
    assert new_name == "Архив"
    assert office_suite.rename_excel_sheet(opened, "Архив", "История") == "История"
    office_suite.delete_excel_sheet(opened, "История")
    assert "История" not in opened.sheetnames


def test_excel_csv_import_export_and_value_parsing(tmp_path: Path) -> None:
    csv_path = tmp_path / "import.csv"
    csv_path.write_text("Имя;Количество\nКофе;12\nЧай;7\n", encoding="utf-8-sig")
    book = Workbook()
    imported_sheet = office_suite.import_csv_to_workbook(book, csv_path)
    assert imported_sheet == "import"
    assert book[imported_sheet]["B2"].value == 12
    assert office_suite.parse_cell_value("1,25") == 1.25
    assert office_suite.parse_cell_value("00125") == "00125"
    assert office_suite.parse_cell_value("=SUM(A1:A3)") == "=SUM(A1:A3)"
    exported = office_suite.export_excel_sheet_csv(book, imported_sheet, tmp_path / "roundtrip.csv")
    with exported.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle, delimiter=";"))
    assert rows[1] == ["Кофе", "12"]


def test_create_excel_workbook_formats_header(tmp_path: Path) -> None:
    path = office_suite.create_excel_workbook(
        tmp_path / "new.xlsx",
        [["Имя", "Возраст"], ["Анна", 25]],
        sheet_name="Люди",
        headers=True,
    )
    opened = office_suite.open_excel_workbook(path)
    sheet = opened["Люди"]
    assert sheet["A1"].value == "Имя"
    assert sheet.freeze_panes == "A2"
    assert sheet.auto_filter.ref


def test_powerpoint_roundtrip(tmp_path: Path) -> None:
    path = office_suite.create_presentation(
        tmp_path / "presentation.pptx",
        "Демо",
        [
            {"title": "Первый слайд", "body": "Главная мысль\n- Пункт один\n- Пункт два"},
            {"title": "Вывод", "body": "Готово"},
        ],
        author="Пульт",
    )
    slides = office_suite.read_presentation(path)
    assert any(slide["title"] == "Первый слайд" for slide in slides)
    assert any("Главная мысль" in slide["body"] for slide in slides)
    assert len(slides) == 2
