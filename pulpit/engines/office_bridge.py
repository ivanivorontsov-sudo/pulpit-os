"""Мост к Microsoft Office: docx, xlsx, pptx без установленного Office.

Файлы — обычный Open XML. Word, Excel и PowerPoint открывают их как родные.
Если Office стоит, Пульт ещё и запускает файл через ассоциацию Windows.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from docx import Document
from openpyxl import Workbook, load_workbook
from pptx import Presentation
from pptx.util import Inches, Pt


def write_docx(path: str | Path, title: str, paragraphs: list[str]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    document.add_heading(title or "Документ Пульта", level=1)
    document.add_paragraph("Собрано в Пульте. Формат DOCX, Word открывает без переводчика.")
    for paragraph in paragraphs:
        if paragraph.strip():
            document.add_paragraph(paragraph.strip())
    document.save(target)
    return target


def read_docx(path: str | Path) -> str:
    document = Document(str(path))
    chunks = [p.text for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            chunks.append(" | ".join(cell.text.strip() for cell in row.cells))
    return "\n".join(chunks)


def write_xlsx(path: str | Path, title: str, rows: list[list[str]]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    book = Workbook()
    sheet = book.active
    sheet.title = (title or "Пульт")[:31]
    sheet.append(["Пульт", "совместимость с Excel"])
    for row in rows:
        sheet.append(list(row))
    sheet.column_dimensions["A"].width = 28
    sheet.column_dimensions["B"].width = 42
    book.save(target)
    return target


def read_xlsx(path: str | Path) -> str:
    book = load_workbook(path, data_only=True)
    lines: list[str] = []
    for sheet in book.worksheets:
        lines.append(f"# {sheet.title}")
        for row in sheet.iter_rows(values_only=True):
            values = ["" if cell is None else str(cell) for cell in row]
            if any(values):
                lines.append(" | ".join(values))
    return "\n".join(lines)


def write_pptx(path: str | Path, title: str, slides: list[tuple[str, str]]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    presentation = Presentation()
    presentation.slide_width = Inches(13.333)
    presentation.slide_height = Inches(7.5)
    cover = presentation.slides.add_slide(presentation.slide_layouts[0])
    cover.shapes.title.text = title or "Пульт"
    if cover.placeholders and len(cover.placeholders) > 1:
        cover.placeholders[1].text = "Презентация в PPTX. PowerPoint ест без вопросов."
    for heading, body in slides:
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])
        slide.shapes.title.text = heading or "Слайд"
        body_shape = slide.placeholders[1]
        body_shape.text = body
        for paragraph in body_shape.text_frame.paragraphs:
            paragraph.font.size = Pt(20)
    presentation.save(target)
    return target


def read_pptx(path: str | Path) -> str:
    presentation = Presentation(str(path))
    chunks: list[str] = []
    for index, slide in enumerate(presentation.slides, start=1):
        texts = []
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False):
                text = shape.text_frame.text.strip()
                if text:
                    texts.append(text)
        chunks.append(f"--- слайд {index} ---\n" + "\n".join(texts))
    return "\n\n".join(chunks)


def open_with_associated_app(path: str | Path) -> str:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(target)
    if sys.platform == "win32":
        os.startfile(target)  # type: ignore[attr-defined]
        return "Отдал Windows. Если Word, Excel или PowerPoint назначены, они сами подхватят."
    if sys.platform == "darwin":
        os.system(f'open "{target}"')
        return "Отдал macOS."
    os.system(f'xdg-open "{target}"')
    return "Отдал системе. На Windows 11 это откроется в Office, если он установлен."
