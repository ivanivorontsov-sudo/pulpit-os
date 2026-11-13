"""Создание, чтение и обмен документами Open XML (DOCX/XLSX/PPTX)."""

from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from pptx import Presentation
from pptx.util import Inches as PptInches, Pt as PptPt


def write_docx(path: str | Path, title: str, paragraphs: list[str]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.85)
    section.right_margin = Inches(0.85)
    document.styles["Normal"].font.name = "Aptos"
    document.styles["Normal"].font.size = Pt(11)
    document.add_heading(title or "Документ Пульта", level=1)
    for raw in paragraphs:
        line = raw.rstrip()
        if not line.strip():
            document.add_paragraph()
        elif line.startswith("### "):
            document.add_heading(line[4:], level=3)
        elif line.startswith("## "):
            document.add_heading(line[3:], level=2)
        elif line.startswith("# "):
            document.add_heading(line[2:], level=1)
        elif line.startswith(("- ", "* ")):
            document.add_paragraph(line[2:], style="List Bullet")
        elif line[:1].isdigit() and ". " in line[:5]:
            document.add_paragraph(line.split(". ", 1)[1], style="List Number")
        else:
            paragraph = document.add_paragraph(line)
            paragraph.paragraph_format.space_after = Pt(6)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("Создано в Пульте").italic = True
    document.save(target)
    return target


def read_docx(path: str | Path) -> str:
    document = Document(str(path))
    chunks: list[str] = []
    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            chunks.append(paragraph.text)
    for index, table in enumerate(document.tables, start=1):
        chunks.append(f"[Таблица {index}]")
        for row in table.rows:
            chunks.append(" | ".join(cell.text.strip().replace("\n", " / ") for cell in row.cells))
    return "\n".join(chunks)


def write_xlsx(
    path: str | Path,
    title: str,
    rows: list[list[Any]],
    headers: bool = False,
    autofilter: bool = True,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    book = Workbook()
    sheet = book.active
    sheet.title = (title or "Пульт")[:31]
    data = [list(row) for row in rows]
    if data:
        for row in data:
            sheet.append(row)
        if headers:
            for cell in sheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="9B4E28")
                cell.alignment = Alignment(vertical="center", wrap_text=True)
            sheet.freeze_panes = "A2"
            if autofilter:
                sheet.auto_filter.ref = sheet.dimensions
        for column in sheet.columns:
            values = [len(str(cell.value or "")) for cell in list(column)[:300]]
            width = min(48, max(12, max(values, default=10) + 2))
            sheet.column_dimensions[get_column_letter(column[0].column)].width = width
        for row in sheet.iter_rows():
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
    else:
        sheet.append(["Пульт", "Пустая таблица"])
    book.save(target)
    return target


def read_xlsx(path: str | Path, max_rows: int = 10000) -> str:
    book = load_workbook(path, data_only=True, read_only=True)
    lines: list[str] = []
    for sheet in book.worksheets:
        lines.append(f"# {sheet.title}")
        count = 0
        for row in sheet.iter_rows(values_only=True):
            values = ["" if cell is None else str(cell) for cell in row]
            if any(values):
                lines.append(" | ".join(values))
            count += 1
            if count >= max_rows:
                lines.append(f"... обрезано после {max_rows} строк")
                break
    book.close()
    return "\n".join(lines)


def write_pptx(path: str | Path, title: str, slides: list[tuple[str, str]]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    presentation = Presentation()
    presentation.slide_width = PptInches(13.333)
    presentation.slide_height = PptInches(7.5)
    cover = presentation.slides.add_slide(presentation.slide_layouts[0])
    cover.shapes.title.text = title or "Пульт"
    if len(cover.placeholders) > 1:
        cover.placeholders[1].text = "Создано в Пульте"
    for heading, body in slides:
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])
        slide.shapes.title.text = heading or "Слайд"
        body_shape = slide.placeholders[1]
        body_shape.text = body
        for paragraph in body_shape.text_frame.paragraphs:
            paragraph.font.size = PptPt(20)
    presentation.save(target)
    return target


def read_pptx(path: str | Path) -> str:
    presentation = Presentation(str(path))
    chunks: list[str] = []
    for index, slide in enumerate(presentation.slides, start=1):
        texts: list[str] = []
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False):
                value = shape.text_frame.text.strip()
                if value:
                    texts.append(value)
            if getattr(shape, "has_table", False):
                for row in shape.table.rows:
                    texts.append(" | ".join(cell.text.strip() for cell in row.cells))
        chunks.append(f"--- слайд {index} ---\n" + "\n".join(texts))
    return "\n\n".join(chunks)


def read_office(path: str | Path) -> str:
    source = Path(path)
    suffix = source.suffix.lower()
    readers = {".docx": read_docx, ".xlsx": read_xlsx, ".pptx": read_pptx}
    if suffix not in readers:
        raise ValueError("Поддерживаются DOCX, XLSX и PPTX")
    return readers[suffix](source)


def csv_to_xlsx(src: str | Path, dest: str | Path, sheet_name: str = "Данные") -> Path:
    source = Path(src)
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(8192)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            reader = csv.reader(handle, dialect)
        except csv.Error:
            reader = csv.reader(handle)
        rows = [row for row in reader]
    return write_xlsx(dest, sheet_name, rows, headers=bool(rows))


def open_with_associated_app(path: str | Path) -> str:
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise FileNotFoundError(target)
    if sys.platform == "win32":
        os.startfile(str(target))  # type: ignore[attr-defined]
        return "Файл передан Windows для открытия в приложении по умолчанию."
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(target)])
        return "Файл передан macOS."
    subprocess.Popen(["xdg-open", str(target)])
    return "Файл передан приложению, назначенному в системе."
