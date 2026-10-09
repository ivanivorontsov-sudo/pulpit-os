# Пульт

Мини-оболочка поверх Windows 11. Не вторая операционка и не драйвер видеокарты. Это рабочий стол инструментов, которых в системе нет из коробки: конвертеры, редакторы, сборщик локального сайта в zip и мост к Microsoft Office.

Ориентиры по устройству: локальные утилиты вроде DeskUtility и MarkItDown Desktop на CustomTkinter, плюс Open XML через python-docx, openpyxl и python-pptx. Office ставить не обязательно, чтобы файл родился. Если Word, Excel или PowerPoint стоят, Windows открывает файл своей ассоциацией.

## Что умеет

- Конвертер картинок: PNG, JPEG, WEBP, BMP, GIF, TIFF.
- JSON в CSV и обратно. Папка в zip и zip обратно в папку.
- Редактор текста со статистикой, markdown в HTML, ужатие картинки.
- Сборщик мини-сайта: страницы, картинки, `index.html`, рядом zip. Открывается без интернета.
- Office: создать и прочитать DOCX, XLSX, PPTX. Кнопка «Открыть в Office» отдаёт файл Windows.
- Единицы: метры, килограммы, температура.
- Карточка системы: видно, что под ногами Windows.

## Запуск на Windows 11

Нужен Python 3.10 или новее.

```bat
run.bat
```

Или вручную:

```bat
python -m pip install -r requirements.txt
python main.py
```

Проверка движков без окна:

```bat
python -m pip install -r requirements.txt pytest
python -m pytest tests
python examples/demo_office.py
```

`examples/demo_office.py` кладёт в `exports` три файла Office и zip сайта, затем читает их обратно.

## Совместимость с Microsoft Office

Пульт пишет обычный Office Open XML.

| Файл | Кто открывает |
| --- | --- |
| `.docx` | Microsoft Word |
| `.xlsx` | Microsoft Excel |
| `.pptx` | Microsoft PowerPoint |

Это не макросы и не COM-автоматизация. Файл можно унести на другой компьютер, и Office откроет его без Пульта.

## Установщик

GitHub Actions на `windows-latest` собирает `Pulpit.exe` через PyInstaller и упаковывает его в `Pulpit-Setup.exe` через Inno Setup. Готовый файл лежит в артефактах прогона:

https://github.com/ivanivorontsov-sudo/pulpit-os/actions

На Windows 11 установщик кладёт Пульт в папку программ и делает ярлык. Office по-прежнему не обязателен, чтобы файлы родились.

```
main.py
run.bat
pulpit/shell.py
pulpit/engines/converters.py
pulpit/engines/editors.py
pulpit/engines/office_bridge.py
pulpit/engines/site_builder.py
pulpit/engines/units.py
examples/demo_office.py
tests/test_engines.py
```
