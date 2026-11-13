"""Дополнительные операции офисного пакета Пульта."""
from __future__ import annotations

import csv
import hashlib
import io
import re
import tempfile
from copy import copy
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Mm, Pt
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule
from openpyxl.styles import Alignment, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils.cell import range_boundaries
from pptx import Presentation
from pptx.util import Inches as PptInches, Pt as PptPt

from pulpit.engines import office_suite

_CODE = chr(96)
_IMAGE_LINE = re.compile(r"!\[([^\]]*)\]\((.+?)\)")
_LINK_TOKEN = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+|mailto:[^\s)]+)\)")
_INLINE_TOKEN = re.compile(
    r"(\*\*.+?\*\*|__.+?__|~~.+?~~|"
    + re.escape(_CODE) + r".+?" + re.escape(_CODE)
    + r"|\*.+?\*)"
)


def _safe_hyperlink(url: str) -> bool:
    compact = "".join(char for char in url.strip() if char >= " " and char != "\x7f")
    return urlsplit(compact).scheme.lower() in {"http", "https", "mailto"}


def _add_hyperlink(paragraph: Any, text: str, url: str) -> None:
    if not _safe_hyperlink(url):
        paragraph.add_run(text)
        return
    relation = paragraph.part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relation)
    run = OxmlElement("w:r")
    properties = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0563C1")
    properties.append(color)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    properties.append(underline)
    run.append(properties)
    node = OxmlElement("w:t")
    node.text = text
    run.append(node)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def _add_inline(paragraph: Any, text: str) -> None:
    cursor = 0
    while cursor < len(text):
        link = _LINK_TOKEN.search(text, cursor)
        token = _INLINE_TOKEN.search(text, cursor)
        candidates = [match for match in (link, token) if match is not None]
        if not candidates:
            paragraph.add_run(text[cursor:])
            break
        match = min(candidates, key=lambda item: item.start())
        if match.start() > cursor:
            paragraph.add_run(text[cursor:match.start()])
        raw = match.group(0)
        if match.re is _LINK_TOKEN:
            _add_hyperlink(paragraph, match.group(1), match.group(2))
        elif raw.startswith("**") or raw.startswith("__"):
            paragraph.add_run(raw[2:-2]).bold = True
        elif raw.startswith("~~"):
            paragraph.add_run(raw[2:-2]).font.strike = True
        elif raw.startswith(_CODE):
            run = paragraph.add_run(raw[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(10)
        else:
            paragraph.add_run(raw[1:-1]).italic = True
        cursor = match.end()


def _parse_table(lines: list[str]) -> list[list[str]]:
    result = []
    for line in lines:
        cells = [cell.strip().replace(r"\|", "|") for cell in line.strip().strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{2,}:?", cell.replace(" ", "")) for cell in cells):
            continue
        result.append(cells)
    return result


def append_word_content(document: Any, text: str) -> None:
    """Рендерит подмножество Markdown в нативные элементы DOCX."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    index = 0
    fenced = False
    code: list[str] = []
    fence = _CODE * 3
    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        if stripped.startswith(fence):
            if fenced:
                for value in code:
                    paragraph = document.add_paragraph(style="No Spacing")
                    run = paragraph.add_run(value or " ")
                    run.font.name = "Consolas"
                    run.font.size = Pt(9)
                code.clear()
                fenced = False
            else:
                fenced = True
            index += 1
            continue
        if fenced:
            code.append(raw)
            index += 1
            continue
        if stripped == "[[PAGE_BREAK]]":
            document.add_page_break()
            index += 1
            continue
        image = _IMAGE_LINE.fullmatch(stripped)
        if image:
            image_path = Path(image.group(2).strip().strip('"')).expanduser()
            if image_path.is_file():
                paragraph = document.add_paragraph()
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                paragraph.add_run().add_picture(str(image_path), width=Inches(5.8))
                if image.group(1):
                    caption = document.add_paragraph(image.group(1))
                    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for run in caption.runs:
                        run.italic = True
                        run.font.size = Pt(9)
            else:
                document.add_paragraph(f"[Изображение не найдено: {image_path}]")
            index += 1
            continue
        if not stripped:
            index += 1
            continue
        if stripped.startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            rows = _parse_table(table_lines)
            if rows:
                columns = max(len(row) for row in rows)
                table = document.add_table(rows=0, cols=columns)
                table.style = "Light Shading Accent 1"
                for row_index, values in enumerate(rows):
                    cells = table.add_row().cells
                    for column_index in range(columns):
                        paragraph = cells[column_index].paragraphs[0]
                        paragraph.clear()
                        _add_inline(paragraph, values[column_index] if column_index < len(values) else "")
                        if row_index == 0:
                            for run in paragraph.runs:
                                run.bold = True
            continue
        if stripped.startswith("# "):
            paragraph = document.add_heading(level=1)
            _add_inline(paragraph, stripped[2:])
        elif stripped.startswith("## "):
            paragraph = document.add_heading(level=2)
            _add_inline(paragraph, stripped[3:])
        elif stripped.startswith("### "):
            paragraph = document.add_heading(level=3)
            _add_inline(paragraph, stripped[4:])
        elif stripped.startswith("> "):
            paragraph = document.add_paragraph(style="Quote")
            _add_inline(paragraph, stripped[2:])
        elif stripped.startswith(("- ", "* ", "+ ")):
            paragraph = document.add_paragraph(style="List Bullet")
            _add_inline(paragraph, stripped[2:])
        elif re.match(r"^\d+[.)]\s+", stripped):
            paragraph = document.add_paragraph(style="List Number")
            _add_inline(paragraph, re.sub(r"^\d+[.)]\s+", "", stripped))
        elif stripped in {"---", "***", "___"}:
            paragraph = document.add_paragraph()
            borders = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            for key, value in (("val", "single"), ("sz", "4"), ("space", "1"), ("color", "B7A18D")):
                bottom.set(qn(f"w:{key}"), value)
            borders.append(bottom)
            paragraph._p.get_or_add_pPr().append(borders)
        else:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.space_after = Pt(6)
            _add_inline(paragraph, raw)
        index += 1
    if fenced:
        for value in code:
            paragraph = document.add_paragraph(style="No Spacing")
            paragraph.add_run(value or " ").font.name = "Consolas"


def _set_page_number(paragraph: Any) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    visible = OxmlElement("w:t")
    visible.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for node in (begin, instruction, separate, visible, end):
        run._r.append(node)


def create_word_document(
    path: str | Path,
    title: str,
    text: str,
    *,
    author: str = "",
    subject: str = "",
    orientation: str = "portrait",
    page_size: str = "A4",
    header_text: str = "",
    footer_text: str = "",
    page_numbers: bool = False,
    template_path: str | Path | None = None,
) -> Path:
    """Создаёт DOCX или пересобирает содержимое исходного DOCX, сохраняя его секции."""
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    template = Path(template_path).expanduser() if template_path else None
    document = Document(str(template)) if template and template.is_file() else Document()
    if template and template.is_file():
        body = document.element.body
        for child in list(body):
            has_section_properties = child.tag == qn("w:p") and bool(child.xpath(".//w:sectPr"))
            if child.tag != qn("w:sectPr") and not has_section_properties:
                body.remove(child)
    section = document.sections[0]
    width, height = (Mm(215.9), Mm(279.4)) if page_size.upper() == "LETTER" else (Mm(210), Mm(297))
    if orientation.lower() == "landscape":
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width, section.page_height = height, width
    elif orientation.lower() == "portrait":
        section.orientation = WD_ORIENT.PORTRAIT
        section.page_width, section.page_height = width, height
    document.styles["Normal"].font.name = document.styles["Normal"].font.name or "Aptos"
    document.styles["Normal"].font.size = document.styles["Normal"].font.size or Pt(11)
    document.core_properties.title = title or "Документ Пульта"
    if author:
        document.core_properties.author = author
    if subject:
        document.core_properties.subject = subject
    first = text.lstrip().splitlines()
    if title and not (first and first[0].strip() == f"# {title}"):
        document.add_heading(title, level=0)
    append_word_content(document, text)
    if header_text:
        section.header.paragraphs[0].text = header_text
    if footer_text:
        section.footer.paragraphs[0].text = footer_text
    if page_numbers:
        _set_page_number(section.footer.paragraphs[0])
    document.save(target)
    return target


def _asset_dir(source: Path) -> Path:
    digest = hashlib.sha256(str(source.resolve()).encode("utf-8")).hexdigest()[:16]
    folder = Path(tempfile.gettempdir()) / "PulpitOffice" / "docx-assets" / digest
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def read_word_document(path: str | Path, *, export_images: bool = True) -> str:
    source = Path(path)
    document = Document(str(source))
    assets = _asset_dir(source) if export_images else None
    output: list[str] = []
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            from docx.text.paragraph import Paragraph
            paragraph = Paragraph(child, document)
            value = office_suite._paragraph_markdown(paragraph)
            if paragraph.style.name.lower() == "title":
                value = "# " + paragraph.text
            if value.strip():
                output.append(value)
            page_break = bool(child.xpath(".//w:br[@w:type='page']"))
            page_break_before = bool(child.xpath("./w:pPr/w:pageBreakBefore"))
            if page_break or page_break_before:
                output.append("[[PAGE_BREAK]]")
            if assets is not None:
                for blip in child.xpath(".//a:blip"):
                    rid = blip.get(qn("r:embed"))
                    part = document.part.related_parts.get(rid) if rid else None
                    if part is None:
                        continue
                    suffix = Path(str(part.partname)).suffix or ".png"
                    digest = hashlib.sha256(part.blob).hexdigest()[:20]
                    image_path = assets / f"{digest}{suffix}"
                    if not image_path.exists():
                        image_path.write_bytes(part.blob)
                    output.append(f"![Изображение]({image_path.as_posix()})")
        elif child.tag == qn("w:tbl"):
            from docx.table import Table as DocxTable
            table = DocxTable(child, document)
            output.append("")
            for row_index, row in enumerate(table.rows):
                values = [cell.text.replace("\n", " / ").replace("|", r"\|") for cell in row.cells]
                output.append("| " + " | ".join(values) + " |")
                if row_index == 0:
                    output.append("| " + " | ".join("---" for _ in values) + " |")
            output.append("")
    return "\n".join(output).strip()


def word_metadata(path: str | Path) -> dict[str, Any]:
    document = Document(str(path))
    section = document.sections[0]
    core = document.core_properties
    return {
        "title": core.title or Path(path).stem,
        "author": core.author or "",
        "subject": core.subject or "",
        "paragraphs": len(document.paragraphs),
        "tables": len(document.tables),
        "inline_images": len(document.inline_shapes),
        "sections": len(document.sections),
        "orientation": "landscape" if section.orientation == WD_ORIENT.LANDSCAPE else "portrait",
        "page_width_mm": round(section.page_width / 36000, 1),
        "page_height_mm": round(section.page_height / 36000, 1),
    }


# Excel: работа с диапазонами, стилями, формами и поиском.
def excel_copy_range(workbook: Any, sheet_name: str, cell_range: str) -> str:
    sheet = workbook[sheet_name]
    min_col, min_row, max_col, max_row = range_boundaries(cell_range)
    return "\n".join(
        "\t".join("" if cell.value is None else str(cell.value) for cell in row)
        for row in sheet.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col)
    )


def excel_paste_tsv(workbook: Any, sheet_name: str, start_cell: str, text: str) -> tuple[int, int]:
    sheet = workbook[sheet_name]
    start = sheet[start_cell]
    rows = list(csv.reader(io.StringIO(text), delimiter="\t"))
    for row_offset, values in enumerate(rows):
        for column_offset, value in enumerate(values):
            sheet.cell(start.row + row_offset, start.column + column_offset).value = office_suite.parse_cell_value(value)
    return len(rows), max((len(row) for row in rows), default=0)


def excel_format_range(
    workbook: Any, sheet_name: str, cell_range: str, *,
    bold: bool | None = None, italic: bool | None = None, underline: bool | None = None,
    fill: str | None = None, font_color: str | None = None,
    number_format: str | None = None, horizontal: str | None = None,
) -> None:
    sheet = workbook[sheet_name]
    min_col, min_row, max_col, max_row = range_boundaries(cell_range)
    for row in sheet.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
        for cell in row:
            font = copy(cell.font)
            if bold is not None:
                font.bold = bold
            if italic is not None:
                font.italic = italic
            if underline is not None:
                font.underline = "single" if underline else None
            if font_color:
                font.color = font_color.lstrip("#").upper()
            cell.font = font
            if fill:
                cell.fill = PatternFill("solid", fgColor=fill.lstrip("#").upper())
            if number_format:
                cell.number_format = number_format
            if horizontal:
                alignment = copy(cell.alignment)
                alignment.horizontal = horizontal
                cell.alignment = alignment


def excel_insert_rows(workbook: Any, sheet_name: str, row: int, amount: int = 1) -> None:
    if row < 1 or amount < 1:
        raise ValueError("Строка и количество должны быть положительными.")
    workbook[sheet_name].insert_rows(row, amount)


def excel_delete_rows(workbook: Any, sheet_name: str, row: int, amount: int = 1) -> None:
    if row < 1 or amount < 1:
        raise ValueError("Строка и количество должны быть положительными.")
    workbook[sheet_name].delete_rows(row, amount)


def excel_insert_columns(workbook: Any, sheet_name: str, column: int, amount: int = 1) -> None:
    if column < 1 or amount < 1:
        raise ValueError("Столбец и количество должны быть положительными.")
    workbook[sheet_name].insert_cols(column, amount)


def excel_delete_columns(workbook: Any, sheet_name: str, column: int, amount: int = 1) -> None:
    if column < 1 or amount < 1:
        raise ValueError("Столбец и количество должны быть положительными.")
    workbook[sheet_name].delete_cols(column, amount)


def excel_merge_range(workbook: Any, sheet_name: str, cell_range: str) -> None:
    workbook[sheet_name].merge_cells(cell_range)


def excel_unmerge_range(workbook: Any, sheet_name: str, cell_range: str) -> None:
    workbook[sheet_name].unmerge_cells(cell_range)


def excel_add_table(workbook: Any, sheet_name: str, cell_range: str, *, name: str = "PulpitTable") -> str:
    sheet = workbook[sheet_name]
    existing = {table.displayName for ws in workbook.worksheets for table in ws.tables.values()}
    base = re.sub(r"[^A-Za-z0-9_]", "_", name)[:200] or "PulpitTable"
    cleaned, index = base, 1
    while cleaned in existing:
        cleaned = f"{base}_{index}"
        index += 1
    table = Table(displayName=cleaned, ref=cell_range)
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=False)
    sheet.add_table(table)
    return cleaned


def excel_add_dropdown(workbook: Any, sheet_name: str, cell_range: str, choices: Iterable[str]) -> None:
    values = [str(value).strip() for value in choices if str(value).strip()]
    if not values or any("," in value for value in values):
        raise ValueError("Для списка нужны значения без запятых.")
    formula = '"' + ",".join(values) + '"'
    if len(formula) > 255:
        raise ValueError("Встроенный список Excel ограничен 255 символами.")
    validation = DataValidation(type="list", formula1=formula, allow_blank=True)
    validation.error = "Выбери значение из списка."
    validation.errorTitle = "Недопустимое значение"
    workbook[sheet_name].add_data_validation(validation)
    validation.add(cell_range)


def excel_add_color_scale(workbook: Any, sheet_name: str, cell_range: str) -> None:
    workbook[sheet_name].conditional_formatting.add(
        cell_range, ColorScaleRule(start_type="min", start_color="F8696B", mid_type="percentile",
        mid_value=50, mid_color="FFEB84", end_type="max", end_color="63BE7B")
    )


def excel_add_data_bar(workbook: Any, sheet_name: str, cell_range: str) -> None:
    workbook[sheet_name].conditional_formatting.add(
        cell_range, DataBarRule(start_type="min", end_type="max", color="638EC6", showValue=True)
    )


def excel_find_replace(workbook: Any, search: str, replacement: str, *, match_case: bool = False, formulas: bool = False) -> int:
    if not search:
        raise ValueError("Строка поиска не должна быть пустой.")
    count = 0
    pattern = re.compile(re.escape(search), 0 if match_case else re.IGNORECASE)
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if not isinstance(cell.value, str) or (cell.value.startswith("=") and not formulas):
                    continue
                cell.value, changed = pattern.subn(lambda _match: replacement, cell.value)
                count += changed
    return count


# PowerPoint: обновление исходной презентации без удаления нетронутых объектов.
def _slide_body_shape(slide: Any) -> Any | None:
    title = slide.shapes.title
    candidates = [shape for shape in slide.shapes if shape is not title and getattr(shape, "has_text_frame", False)]
    placeholders = [shape for shape in candidates if getattr(shape, "is_placeholder", False)]
    return (placeholders or candidates or [None])[0]


def _set_slide_text(shape: Any, value: str) -> None:
    frame = shape.text_frame
    frame.clear()
    for index, line in enumerate(value.splitlines() or [""]):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        raw = line.strip()
        if raw.startswith(("- ", "* ")):
            paragraph.text = raw[2:]
            paragraph.level = 0
        else:
            paragraph.text = line
        paragraph.font.size = PptPt(20)


def read_presentation(path: str | Path) -> dict[str, Any]:
    presentation = Presentation(str(path))
    slides = []
    for index, slide in enumerate(presentation.slides):
        title = slide.shapes.title.text.strip() if slide.shapes.title else ""
        body_shape = _slide_body_shape(slide)
        body = body_shape.text_frame.text.strip() if body_shape is not None else ""
        notes = ""
        try:
            notes = slide.notes_slide.notes_text_frame.text.strip()
        except (AttributeError, KeyError, ValueError):
            pass
        slides.append({"title": title or f"Слайд {index + 1}", "body": body, "notes": notes,
                       "_source_index": index, "images": []})
    return {"title": presentation.core_properties.title or Path(path).stem,
            "author": presentation.core_properties.author or "", "slides": slides}


def create_presentation(
    path: str | Path, title: str, slides: list[dict[str, Any]], *,
    author: str = "", template_path: str | Path | None = None,
) -> Path:
    """Сохраняет исходные диаграммы, изображения, фигуры, темы и макеты PPTX."""
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    template = Path(template_path).expanduser() if template_path else None
    if template and template.is_file():
        presentation = Presentation(str(template))
        originals = list(presentation.slides)
        original_nodes = list(presentation.slides._sldIdLst)
        id_to_node = {index: node for index, node in enumerate(original_nodes)}
        used: set[int] = set()
        ordered_nodes: list[Any] = []
        keep_generated_cover = bool(
            not any(data.get("_source_index") == 0 for data in slides)
            and len(originals) > 1
            and len(originals[0].placeholders) > 1
            and originals[0].placeholders[1].text.strip() == "Создано в Пульте"
        )
        if keep_generated_cover:
            used.add(0)
            ordered_nodes.append(id_to_node[0])
        for data in slides:
            source_index = data.get("_source_index")
            if isinstance(source_index, int) and source_index in range(len(originals)) and source_index not in used:
                slide = originals[source_index]
                node = id_to_node[source_index]
                used.add(source_index)
                new_slide = False
            else:
                layout_index = 1 if len(presentation.slide_layouts) > 1 else 0
                slide = presentation.slides.add_slide(presentation.slide_layouts[layout_index])
                node = presentation.slides._sldIdLst[-1]
                new_slide = True

            if slide.shapes.title is not None:
                slide.shapes.title.text = data.get("title", "Слайд")
            elif new_slide:
                title_box = slide.shapes.add_textbox(PptInches(0.6), PptInches(0.35), PptInches(11.8), PptInches(0.8))
                title_box.text = data.get("title", "Слайд")
            body_shape = _slide_body_shape(slide)
            if body_shape is not None:
                _set_slide_text(body_shape, data.get("body", ""))
            elif new_slide:
                body_shape = slide.shapes.add_textbox(PptInches(0.8), PptInches(1.6), PptInches(6.0), PptInches(5.0))
                _set_slide_text(body_shape, data.get("body", ""))
            image_paths = [Path(raw).expanduser() for raw in data.get("images", []) if Path(raw).expanduser().is_file()]
            if image_paths:
                body_shape = _slide_body_shape(slide)
                if body_shape is not None:
                    body_shape.width = PptInches(6.0)
                    body_shape.height = PptInches(4.7)
                for image_index, image_path in enumerate(image_paths):
                    slide.shapes.add_picture(
                        str(image_path), PptInches(7.1), PptInches(1.7 + image_index * 2.0),
                        width=PptInches(5.5),
                    )
            table_rows = data.get("table") or []
            if table_rows:
                rows = len(table_rows)
                columns = max((len(row) for row in table_rows), default=0)
                if rows and columns:
                    body_shape = _slide_body_shape(slide)
                    if body_shape is not None:
                        body_shape.height = PptInches(3.0)
                    graphic = slide.shapes.add_table(
                        rows, columns, PptInches(0.8), PptInches(4.6),
                        PptInches(11.7), PptInches(2.0),
                    )
                    for row_index, values in enumerate(table_rows):
                        for column_index in range(columns):
                            graphic.table.cell(row_index, column_index).text = (
                                str(values[column_index]) if column_index < len(values) else ""
                            )
            if data.get("notes"):
                try:
                    slide.notes_slide.notes_text_frame.text = data["notes"]
                except (AttributeError, KeyError, ValueError):
                    pass
            ordered_nodes.append(node)

        for index, node in enumerate(original_nodes):
            if index not in used:
                rel_id = node.get(qn("r:id"))
                if rel_id:
                    presentation.part.drop_rel(rel_id)
        slide_list = presentation.slides._sldIdLst
        for node in list(slide_list):
            slide_list.remove(node)
        for node in ordered_nodes:
            slide_list.append(node)
    else:
        presentation = Presentation()
        presentation.slide_width = PptInches(13.333)
        presentation.slide_height = PptInches(7.5)
        cover = presentation.slides.add_slide(presentation.slide_layouts[0])
        cover.shapes.title.text = title or "Презентация Пульта"
        if len(cover.placeholders) > 1:
            cover.placeholders[1].text = "Создано в Пульте"
        for data in slides:
            layout_index = 1 if len(presentation.slide_layouts) > 1 else 0
            slide = presentation.slides.add_slide(presentation.slide_layouts[layout_index])
            if slide.shapes.title is not None:
                slide.shapes.title.text = data.get("title", "Слайд")
            body = _slide_body_shape(slide)
            if body is not None:
                _set_slide_text(body, data.get("body", ""))
            for image_path in data.get("images", []):
                image = Path(image_path).expanduser()
                if image.is_file():
                    slide.shapes.add_picture(str(image), PptInches(7.1), PptInches(1.7), width=PptInches(5.5))
            if data.get("notes"):
                try:
                    slide.notes_slide.notes_text_frame.text = data["notes"]
                except (AttributeError, KeyError, ValueError):
                    pass
    presentation.core_properties.title = title or "Презентация Пульта"
    if author:
        presentation.core_properties.author = author
    presentation.save(target)
    return target
