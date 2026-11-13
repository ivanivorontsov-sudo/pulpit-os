from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from PIL import Image

from pulpit.builder_app import _map_asset_refs, _migrate_legacy
from pulpit.engines.site_export import export_site, slugify


def test_slugify_removes_paths_and_transliterates() -> None:
    assert slugify("../../Моя страница") == "moya-stranitsa"
    assert slugify("index", "page-2") == "page-2"


def test_export_multi_page_site_and_assets(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    Image.new("RGB", (12, 8), (120, 130, 140)).save(assets / "photo.png")
    payload = {
        "title": "Мой сайт",
        "language": "ru",
        "pages": [
            {
                "id": "home",
                "name": "Главная",
                "slug": "index",
                "title": "Главная — Мой сайт",
                "description": "Описание главной страницы",
                "html": '<section><h1>Привет</h1><img src="assets/photo.png" alt="Фото"></section>',
                "css": "h1 { color: #123456; }",
                "js": "window.siteReady = true;",
            },
            {
                "id": "about",
                "name": "О проекте",
                "slug": "o-proekte",
                "title": "О проекте",
                "description": "Вторая страница",
                "html": "<main><h1>О проекте</h1></main>",
                "css": "main { padding: 20px; }",
                "js": "",
            },
        ],
    }
    result = export_site(payload, assets, tmp_path / "release" / "site.zip")
    archive_path = Path(result["zip"])
    assert archive_path.is_file()
    assert result["pages"] == "2"
    assert result["assets"] == "1"
    with ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        assert {"index.html", "o-proekte.html", "style.css", "assets/photo.png", "README.md", "robots.txt"} <= names
        main = archive.read("index.html").decode("utf-8")
        second = archive.read("o-proekte.html").decode("utf-8")
        assert "<title>Главная — Мой сайт</title>" in main
        assert 'href="o-proekte.html"' in main
        assert 'src="assets/photo.png"' in main
        assert "window.siteReady = true;" in main
        assert "<title>О проекте</title>" in second


def test_export_escapes_metadata_and_unique_slugs(tmp_path: Path) -> None:
    result = export_site({
        "title": 'Сайт "Иван"',
        "pages": [
            {"name": "О нас", "slug": "about", "title": "<script>alert(1)</script>", "html": "<h1>О нас</h1>"},
            {"name": "О компании", "slug": "about", "html": "<h1>О компании</h1>"},
        ],
    }, tmp_path / "missing-assets", tmp_path / "site.zip")
    with ZipFile(result["zip"]) as archive:
        names = set(archive.namelist())
        assert "index.html" in names
        assert "about-2.html" in names
        first = archive.read("index.html").decode("utf-8")
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in first
        assert "<script>alert(1)</script>" not in first
        assert "about-2.html" in first


def test_legacy_project_migration_keeps_pages_and_blocks() -> None:
    migrated = _migrate_legacy({
        "title": "Старый сайт",
        "pages": [
            {"id": "home", "title": "Главная", "blocks": [
                {"type": "hero", "text": "Заголовок", "sub": "Подзаголовок"},
                {"type": "button", "text": "Открыть", "href": "about.html"},
            ]},
            {"id": "about", "title": "О нас", "blocks": [
                {"type": "text", "text": "Текст страницы"},
            ]},
        ],
    })
    assert migrated["format"] == "pulpit-page-project"
    pages = migrated["projectData"]["pages"]
    assert len(pages) == 2
    assert "Заголовок" in pages[0]["component"]
    assert 'href="about.html"' in pages[0]["component"]
    assert "Текст страницы" in pages[1]["component"]

def test_absolute_local_file_urls_become_portable_asset_paths(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    photo = assets / "portrait with spaces.png"
    Image.new("RGB", (9, 6), (10, 20, 30)).save(photo)
    file_url = photo.resolve().as_uri()
    result = export_site(
        {
            "title": "Портфолио",
            "pages": [
                {
                    "name": "Главная",
                    "html": f'<section><img src="{file_url}" alt="Портрет"></section>',
                    "css": f'.photo{{background-image:url("{file_url}")}}',
                }
            ],
        },
        assets,
        tmp_path / "portable.zip",
    )
    with ZipFile(result["zip"]) as archive:
        html = archive.read("index.html").decode("utf-8")
        assert 'src="assets/portrait%20with%20spaces.png"' in html
        assert "file:///" not in html
        assert "assets/portrait%20with%20spaces.png" in html
        assert "assets/portrait with spaces.png" in archive.namelist()

def test_project_asset_refs_are_reversible(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    photo = assets / "demo photo.png"
    Image.new("RGB", (3, 3), (60, 70, 80)).save(photo)
    project = {
        "projectData": {
            "pages": [
                {"component": '<img src="assets/demo photo.png" alt="demo">'}
            ]
        }
    }
    preview = _map_asset_refs(project, tmp_path, to_absolute=True)
    assert photo.resolve().as_uri() in preview["projectData"]["pages"][0]["component"]
    portable = _map_asset_refs(preview, tmp_path, to_absolute=False)
    assert portable["projectData"]["pages"][0]["component"] == project["projectData"]["pages"][0]["component"]
