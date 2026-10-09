"""Собирает три файла Office и локальный сайт, чтобы показать совместимость без кликов."""

from pathlib import Path

from pulpit.engines import office_bridge, site_builder


def main() -> None:
    out = Path("exports")
    out.mkdir(exist_ok=True)
    docx = office_bridge.write_docx(out / "pulpit.docx", "Пульт и Word", ["Файл DOCX. Открой в Microsoft Word."])
    xlsx = office_bridge.write_xlsx(out / "pulpit.xlsx", "Пульт", [["инструмент", "Office"], ["docx", "Word"], ["xlsx", "Excel"], ["pptx", "PowerPoint"]])
    pptx = office_bridge.write_pptx(out / "pulpit.pptx", "Пульт и PowerPoint", [("Совместимость", "PPTX открывается в PowerPoint как обычная презентация.")])
    site = site_builder.build_site(
        out / "local-site",
        "Локальный сайт Пульта",
        "Картинки в zip, интернет опционален",
        "#c45c26",
        [{"title": "Главная", "body": "Распакуй zip и открой index.html."}],
    )
    print(docx)
    print(xlsx)
    print(pptx)
    print(site["zip"])
    print(office_bridge.read_docx(docx).splitlines()[0])
    print(office_bridge.read_xlsx(xlsx).splitlines()[0])
    print(office_bridge.read_pptx(pptx).splitlines()[0])


if __name__ == "__main__":
    main()
