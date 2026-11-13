"""Расширенный офисный движок Пульта на базе python-docx, openpyxl и python-pptx.

Поддерживает локальное создание и редактирование Open XML. LibreOffice используется
как необязательный внешний конвертер, если он установлен в системе.
"""
from __future__ import annotations

import csv
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt
from docx.table import Table as DocxTable
from docx.text.paragraph import Paragraph as DocxParagraph
from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt as PptPt


SUPPORTED_EXCEL = {".xlsx", ".xlsm"}
SUPPORTED_WORD = {".docx"}
SUPPORTED_POWERPOINT = {".pptx"}
OFFICE_EXTENSIONS = SUPPORTED_WORD | SUPPORTED_EXCEL | SUPPORTED_POWERPOINT
_CODE_MARKER = chr(96)
_INLINE_RE = re.compile(
    r"(\*\*.+?\*\*|__.+?__|~~.+?~~|"
    + re.escape(_CODE_MARKER) + r".+?" + re.escape(_CODE_MARKER)
    + r"|\*.+?\*)"
)


def _ensure_parent(path: str | Path) -> Path:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _inline_runs(paragraph: Any, text: str) -> None:
    """Записывает простой Markdown в форматированные Word runs."""
    cursor = 0
    for match in _INLINE_RE.finditer(text):
        if match.start() > cursor:
            paragraph.add_run(text[cursor:match.start()])
        token = match.group(0)
        if token.startswith("**") or token.startswith("__"):
            run = paragraph.add_run(token[2:-2])
            run.bold = True
        elif token.startswith("~~"):
            run = paragraph.add_run(token[2:-2])
            run.font.strike = True
        elif token.startswith(_CODE_MARKER):
            run = paragraph.add_run(token[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(10)
        else:
            run = paragraph.add_run(token[1:-1])
            run.italic = True
        cursor = match.end()
    if cursor < len(text):
        paragraph.add_run(text[cursor:])


def _markdown_table_rows(lines: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{2,}:?", cell.replace(" ", "")) for cell in cells):
            continue
        rows.append(cells)
    return rows


def _append_markdown(document: Any, text: str) -> None:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    index = 0
    in_code = False
    code_lines: list[str] = []
    fence = _CODE_MARKER * 3
    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        if stripped.startswith(fence):
            if in_code:
                for code_line in code_lines:
                    paragraph = document.add_paragraph(style="No Spacing")
                    run = paragraph.add_run(code_line or " ")
                    run.font.name = "Consolas"
                    run.font.size = Pt(9)
                code_lines.clear()
                in_code = False
            else:
                in_code = True
            index += 1
            continue
        if in_code:
            code_lines.append(raw)
            index += 1
            continue
        if not stripped:
            index += 1
            continue
        if stripped.startswith("|"):
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            rows = _markdown_table_rows(table_lines)
            if rows:
                columns = max(len(row) for row in rows)
                table = document.add_table(rows=0, cols=columns)
                table.style = "Light Shading Accent 1"
                for row_index, values in enumerate(rows):
                    cells = table.add_row().cells
                    for column_index in range(columns):
                        cell_text = values[column_index] if column_index < len(values) else ""
                        cell = cells[column_index]
                        cell.text = cell_text
                        for run in cell.paragraphs[0].runs:
                            if row_index == 0:
                                run.bold = True
            continue
        if stripped.startswith("# "):
            paragraph = document.add_heading(level=1)
            _inline_runs(paragraph, stripped[2:])
        elif stripped.startswith("## "):
            paragraph = document.add_heading(level=2)
            _inline_runs(paragraph, stripped[3:])
        elif stripped.startswith("### "):
            paragraph = document.add_heading(level=3)
            _inline_runs(paragraph, stripped[4:])
        elif stripped.startswith("> "):
            paragraph = document.add_paragraph(style="Quote")
            _inline_runs(paragraph, stripped[2:])
        elif stripped.startswith(("- ", "* ", "+ ")):
            paragraph = document.add_paragraph(style="List Bullet")
            _inline_runs(paragraph, stripped[2:])
        elif re.match(r"^\d+[.)]\s+", stripped):
            paragraph = document.add_paragraph(style="List Number")
            _inline_runs(paragraph, re.sub(r"^\d+[.)]\s+", "", stripped))
        elif stripped in {"---", "***", "___"}:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.space_after = Pt(4)
            p_pr = paragraph._p.get_or_add_pPr()
            borders = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "4")
            bottom.set(qn("w:space"), "1")
            bottom.set(qn("w:color"), "B7A18D")
            borders.append(bottom)
            p_pr.append(borders)
        else:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.space_after = Pt(6)
            _inline_runs(paragraph, raw)
        index += 1
    if in_code:
        for code_line in code_lines:
            paragraph = document.add_paragraph(style="No Spacing")
            run = paragraph.add_run(code_line or " ")
            run.font.name = "Consolas"
            run.font.size = Pt(9)


def create_word_document(
    path: str | Path,
    title: str,
    text: str,
    *,
    author: str = "",
    subject: str = "",
    orientation: str = "portrait",
    page_size: str = "A4",
    include_footer: bool = True,
) -> Path:
    """Создаёт DOCX с заголовками, Markdown-форматированием, списками и таблицами."""
    target = _ensure_parent(path)
    document = Document()
    section = document.sections[0]
    if page_size.upper() == "LETTER":
        width, height = Mm(215.9), Mm(279.4)
    else:
        width, height = Mm(210), Mm(297)
    if orientation.lower() == "landscape":
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width, section.page_height = height, width
    else:
        section.orientation = WD_ORIENT.PORTRAIT
        section.page_width, section.page_height = width, height
    section.top_margin = Mm(18)
    section.bottom_margin = Mm(18)
    section.left_margin = Mm(22)
    section.right_margin = Mm(18)
    normal = document.styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    for style_name in ("Title", "Heading 1", "Heading 2", "Heading 3"):
        document.styles[style_name].font.name = "Aptos Display"
    document.core_properties.title = title or "Документ Пульта"
    document.core_properties.author = author
    document.core_properties.subject = subject
    document.add_heading(title or "Документ Пульта", level=0)
    _append_markdown(document, text)
    if include_footer:
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = footer.add_run("Пульт · локальный офисный документ")
        run.italic = True
        run.font.size = Pt(8)
    document.save(target)
    return target


def _paragraph_markdown(paragraph: Any) -> str:
    content: list[str] = []
    for run in paragraph.runs:
        value = run.text
        if run.bold:
            value = f"**{value}**"
        if run.italic:
            value = f"*{value}*"
        if run.font.strike:
            value = f"~~{value}~~"
        content.append(value)
    text = "".join(content) if content else paragraph.text
    style = (paragraph.style.name or "").lower()
    if style.startswith("heading 1"):
        return "# " + text
    if style.startswith("heading 2"):
        return "## " + text
    if style.startswith("heading 3"):
        return "### " + text
    if "bullet" in style:
        return "- " + text
    if "number" in style:
        return "1. " + text
    if style == "quote":
        return "> " + text
    return text


def read_word_document(path: str | Path) -> str:
    """Извлекает структуру DOCX в удобный для дальнейшего редактирования текст."""
    document = Document(str(path))
    output: list[str] = []
    body = document.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            paragraph = DocxParagraph(child, document)
            value = _paragraph_markdown(paragraph)
            if value.strip():
                output.append(value)
        elif child.tag == qn("w:tbl"):
            table = DocxTable(child, document)
            output.append("")
            for row_index, row in enumerate(table.rows):
                values = [cell.text.replace("\n", " / ").replace("|", "\\|") for cell in row.cells]
                output.append("| " + " | ".join(values) + " |")
                if row_index == 0:
                    output.append("| " + " | ".join("---" for _ in values) + " |")
            output.append("")
    return "\n".join(output).strip()


def word_metadata(path: str | Path) -> dict[str, str | int]:
    document = Document(str(path))
    core = document.core_properties
    return {
        "title": core.title or Path(path).stem,
        "author": core.author or "",
        "subject": core.subject or "",
        "paragraphs": len(document.paragraphs),
        "tables": len(document.tables),
        "sections": len(document.sections),
    }


def create_excel_workbook(
    path: str | Path,
    rows: Iterable[Iterable[Any]] | None = None,
    *,
    sheet_name: str = "Лист1",
    headers: bool = True,
) -> Path:
    target = _ensure_parent(path)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = (sheet_name or "Лист1")[:31]
    for row in rows or []:
        sheet.append([parse_cell_value(value) if isinstance(value, str) else value for value in row])
    format_excel_sheet(sheet, headers=headers)
    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True
    workbook.calculation.calcMode = "auto"
    workbook.save(target)
    return target


def open_excel_workbook(path: str | Path) -> Any:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix not in SUPPORTED_EXCEL:
        raise ValueError("Поддерживаются книги XLSX и XLSM. Старые XLS можно импортировать через LibreOffice.")
    if not source.is_file():
        raise FileNotFoundError(source)
    return load_workbook(source, data_only=False, keep_vba=(suffix == ".xlsm"))


def save_excel_workbook(workbook: Any, path: str | Path) -> Path:
    target = _ensure_parent(path)
    suffix = target.suffix.lower()
    if suffix == ".xlsm" and not getattr(workbook, "vba_archive", None):
        raise ValueError("Эта книга не содержит VBA-макросы. Сохрани её как XLSX, чтобы не создавать пустой XLSM.")
    if suffix not in SUPPORTED_EXCEL:
        raise ValueError("Формат сохранения должен быть XLSX или XLSM.")
    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True
    workbook.calculation.calcMode = "auto"
    workbook.save(target)
    return target


def parse_cell_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    raw = value.strip()
    if not raw:
        return None
    if raw.startswith("="):
        return raw
    lowered = raw.lower()
    if lowered in {"true", "истина"}:
        return True
    if lowered in {"false", "ложь"}:
        return False
    normalized = raw.replace(" ", "").replace(",", ".")
    if re.fullmatch(r"0\d+", normalized):
        return raw
    if re.fullmatch(r"[+-]?\d+", normalized):
        try:
            return int(normalized)
        except ValueError:
            return raw
    if re.fullmatch(r"[+-]?(?:\d+\.\d*|\.\d+)(?:[eE][+-]?\d+)?", normalized):
        try:
            return float(normalized)
        except ValueError:
            return raw
    return raw


def excel_sheet_snapshot(workbook: Any, sheet_name: str | None = None, *, max_rows: int = 250, max_columns: int = 24) -> dict[str, Any]:
    if not workbook.worksheets:
        raise ValueError("В книге нет листов.")
    sheet = workbook[sheet_name] if sheet_name else workbook.active
    max_row = min(max(sheet.max_row, 1), max_rows)
    max_col = min(max(sheet.max_column, 1), max_columns)
    rows = []
    for row in sheet.iter_rows(min_row=1, max_row=max_row, min_col=1, max_col=max_col, values_only=True):
        rows.append(list(row))
    return {
        "sheet": sheet.title,
        "rows": rows,
        "max_row": sheet.max_row,
        "max_column": sheet.max_column,
        "truncated": sheet.max_row > max_rows or sheet.max_column > max_columns,
        "freeze_panes": str(sheet.freeze_panes or ""),
        "autofilter": str(sheet.auto_filter.ref or ""),
    }


def set_excel_cell(workbook: Any, sheet_name: str, cell_ref: str, value: Any) -> None:
    if sheet_name not in workbook.sheetnames:
        raise ValueError(f"Лист не найден: {sheet_name}")
    workbook[sheet_name][cell_ref.upper()] = parse_cell_value(value)


def append_excel_row(workbook: Any, sheet_name: str, values: Iterable[Any]) -> int:
    sheet = workbook[sheet_name]
    sheet.append([parse_cell_value(value) if isinstance(value, str) else value for value in values])
    return sheet.max_row


def add_excel_sheet(workbook: Any, name: str) -> str:
    cleaned = (name or "Лист").strip()[:31]
    if not cleaned:
        cleaned = "Лист"
    if cleaned in workbook.sheetnames:
        raise ValueError(f"Лист «{cleaned}» уже существует.")
    return workbook.create_sheet(cleaned).title


def rename_excel_sheet(workbook: Any, old_name: str, new_name: str) -> str:
    cleaned = (new_name or "").strip()[:31]
    if not cleaned:
        raise ValueError("Имя листа не может быть пустым.")
    if cleaned != old_name and cleaned in workbook.sheetnames:
        raise ValueError(f"Лист «{cleaned}» уже существует.")
    workbook[old_name].title = cleaned
    return cleaned


def delete_excel_sheet(workbook: Any, sheet_name: str) -> None:
    if len(workbook.worksheets) <= 1:
        raise ValueError("Нельзя удалить последний лист книги.")
    if sheet_name not in workbook.sheetnames:
        raise ValueError(f"Лист не найден: {sheet_name}")
    del workbook[sheet_name]


def format_excel_sheet(sheet: Any, *, headers: bool = True, autofilter: bool = True) -> None:
    header_fill = PatternFill("solid", fgColor="7A4B32")
    header_font = Font(bold=True, color="FFFFFF")
    bottom = Side(style="thin", color="D9C9BB")
    if headers and sheet.max_row >= 1 and sheet.max_column >= 1:
        for cell in sheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        sheet.row_dimensions[1].height = 28
        sheet.freeze_panes = "A2"
        if autofilter:
            sheet.auto_filter.ref = sheet.dimensions
    for row in sheet.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if cell.row > 1:
                cell.border = Border(bottom=bottom)
    for column_cells in sheet.columns:
        values = [len(str(cell.value or "")) for cell in list(column_cells)[:500]]
        width = min(48, max(10, max(values, default=8) + 2))
        sheet.column_dimensions[get_column_letter(column_cells[0].column)].width = width


def format_excel_header(workbook: Any, sheet_name: str) -> None:
    format_excel_sheet(workbook[sheet_name], headers=True)


def add_excel_chart(
    workbook: Any,
    sheet_name: str,
    *,
    chart_type: str = "bar",
    title: str = "Диаграмма",
    data_column: int = 2,
    category_column: int = 1,
    first_row: int = 1,
    last_row: int | None = None,
    anchor: str = "E2",
) -> None:
    sheet = workbook[sheet_name]
    end_row = last_row or sheet.max_row
    if end_row <= first_row:
        raise ValueError("Для диаграммы нужно минимум две строки: заголовок и данные.")
    chart_cls = {"bar": BarChart, "line": LineChart, "pie": PieChart}.get(chart_type)
    if chart_cls is None:
        raise ValueError("Тип диаграммы: bar, line или pie.")
    chart = chart_cls()
    chart.title = title
    chart.height = 8
    chart.width = 15
    data = Reference(sheet, min_col=data_column, min_row=first_row, max_row=end_row)
    categories = Reference(sheet, min_col=category_column, min_row=first_row + 1, max_row=end_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(categories)
    if chart_type == "bar":
        chart.y_axis.title = "Значение"
        chart.x_axis.title = "Категория"
    sheet.add_chart(chart, anchor)


def import_csv_to_workbook(
    workbook: Any,
    path: str | Path,
    *,
    sheet_name: str | None = None,
    delimiter: str | None = None,
) -> str:
    source = Path(path)
    content = None
    for encoding in ("utf-8-sig", "cp1251", "utf-8"):
        try:
            content = source.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    if content is None:
        raise ValueError("Не удалось определить кодировку CSV.")
    if delimiter is None:
        try:
            delimiter = csv.Sniffer().sniff(content[:8192], delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
    rows = list(csv.reader(content.splitlines(), delimiter=delimiter))
    name = sheet_name or source.stem or "Импорт"
    if name in workbook.sheetnames:
        name = (name[:26] + "_импорт")[:31]
        suffix = 1
        original = name
        while name in workbook.sheetnames:
            name = (original[:27] + str(suffix))[:31]
            suffix += 1
    sheet = workbook.create_sheet(name)
    for row in rows:
        sheet.append([parse_cell_value(value) for value in row])
    format_excel_sheet(sheet, headers=True)
    return sheet.title


def export_excel_sheet_csv(workbook: Any, sheet_name: str, path: str | Path, *, delimiter: str = ";") -> Path:
    target = _ensure_parent(path)
    sheet = workbook[sheet_name]
    with target.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, delimiter=delimiter)
        for row in sheet.iter_rows(values_only=True):
            writer.writerow(["" if value is None else value for value in row])
    return target


def create_presentation(
    path: str | Path,
    title: str,
    slides: list[dict[str, str]],
    *,
    author: str = "",
    theme_color: str = "7A4B32",
) -> Path:
    target = _ensure_parent(path)
    presentation = Presentation()
    presentation.slide_width = Inches(13.333)
    presentation.slide_height = Inches(7.5)
    presentation.core_properties.title = title or "Презентация Пульта"
    presentation.core_properties.author = author
    cover = presentation.slides.add_slide(presentation.slide_layouts[0])
    cover.shapes.title.text = title or "Презентация Пульта"
    if len(cover.placeholders) > 1:
        cover.placeholders[1].text = "Создано в Пульте"
    rgb = RGBColor.from_string(theme_color.upper().lstrip("#")[:6])
    for slide_data in slides:
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])
        slide.shapes.title.text = slide_data.get("title", "Слайд") or "Слайд"
        body = slide.placeholders[1].text_frame
        body.clear()
        raw_body = slide_data.get("body", "")
        lines = raw_body.splitlines() or [""]
        first = True
        for line in lines:
            paragraph = body.paragraphs[0] if first else body.add_paragraph()
            first = False
            stripped = line.strip()
            if stripped.startswith(("- ", "* ")):
                paragraph.text = stripped[2:]
                paragraph.level = 0
            else:
                paragraph.text = line
            paragraph.font.size = PptPt(20)
            paragraph.font.color.rgb = rgb
    presentation.save(target)
    return target


def read_presentation(path: str | Path) -> list[dict[str, str]]:
    presentation = Presentation(str(path))
    slides: list[dict[str, str]] = []
    for slide in presentation.slides:
        title = slide.shapes.title.text.strip() if slide.shapes.title else ""
        body_parts: list[str] = []
        for shape in slide.shapes:
            if not getattr(shape, "has_text_frame", False):
                continue
            value = shape.text_frame.text.strip()
            if value and value != title:
                body_parts.append(value)
        if title or body_parts:
            slides.append({"title": title or f"Слайд {len(slides) + 1}", "body": "\n".join(body_parts)})
    if slides and slides[0]["body"].strip() == "Создано в Пульте":
        slides = slides[1:]
    return slides


def find_libreoffice() -> str | None:
    """Ищет LibreOffice; отсутствие программы не мешает работе встроенного офиса."""
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return found
    if sys.platform == "win32":
        candidates = [
            Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "LibreOffice" / "program" / "soffice.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "LibreOffice" / "program" / "soffice.exe",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
    elif sys.platform == "darwin":
        candidate = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
        if candidate.is_file():
            return str(candidate)
    return None


def libreoffice_available() -> bool:
    return find_libreoffice() is not None


def convert_with_libreoffice(
    source: str | Path,
    output_format: str = "pdf",
    *,
    output_dir: str | Path | None = None,
    timeout: int = 180,
) -> Path:
    """Конвертирует документы LibreOffice в PDF, Open XML или открытые форматы.

    Результат сначала создаётся во временной папке, чтобы случайно не затереть
    исходник или предыдущую конвертацию с таким же именем.
    """
    source_path = Path(source).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    binary = find_libreoffice()
    if not binary:
        raise RuntimeError("LibreOffice не найден. Установи его для конвертации PDF и старых форматов Office.")
    allowed = {"pdf", "docx", "xlsx", "pptx", "odt", "ods", "odp"}
    fmt = output_format.lower().lstrip(".")
    if fmt not in allowed:
        raise ValueError(f"Неподдерживаемый формат экспорта: {fmt}")
    destination = Path(output_dir).expanduser().resolve() if output_dir else source_path.parent
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pulpit-lo-output-") as staging_dir:
        with tempfile.TemporaryDirectory(prefix="pulpit-lo-profile-") as profile_dir:
            profile_uri = Path(profile_dir).resolve().as_uri()
            command = [
                binary, "--headless", "--nologo", "--nodefault", "--nolockcheck",
                f"-env:UserInstallation={profile_uri}",
                "--convert-to", fmt, "--outdir", staging_dir, str(source_path),
            ]
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(f"LibreOffice не завершил конвертацию за {timeout} секунд.") from exc
        staged = Path(staging_dir) / f"{source_path.stem}.{fmt}"
        if result.returncode != 0 or not staged.is_file():
            details = (result.stderr or result.stdout or "Нет подробностей от LibreOffice").strip()
            raise RuntimeError(f"LibreOffice не смог создать файл {source_path.stem}.{fmt}: {details}")
        target = destination / staged.name
        if target.resolve() == source_path:
            raise ValueError("Нельзя конвертировать файл в тот же формат поверх исходника.")
        counter = 1
        while target.exists():
            target = destination / f"{source_path.stem}_converted_{counter}.{fmt}"
            counter += 1
        shutil.move(str(staged), str(target))
    return target

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
