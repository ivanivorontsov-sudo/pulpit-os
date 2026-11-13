"use strict";

const $ = (id) => document.getElementById(id);
const DEFAULT_CSS = [
  "body{margin:0;font-family:Inter,system-ui,sans-serif;color:#172033;background:#fff;line-height:1.6}",
  "h1,h2,h3{line-height:1.15;letter-spacing:-.03em}",
  ".container{width:min(1120px,calc(100% - 40px));margin:0 auto}",
  ".hero{padding:88px 24px;background:linear-gradient(135deg,#17213b,#535fc0);color:#fff;text-align:center}",
  ".hero h1{font-size:clamp(38px,7vw,72px);margin:12px auto;max-width:900px}",
  ".hero p{max-width:680px;margin:12px auto 24px;font-size:18px;opacity:.86}",
  ".section{padding:64px 24px}",
  ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px}",
  ".card{padding:24px;border:1px solid #e4e8f0;border-radius:16px;background:#fff;box-shadow:0 8px 28px #1720330c}",
  ".button{display:inline-block;padding:12px 20px;border-radius:10px;background:#6674e6;color:#fff;text-decoration:none;font-weight:700}",
  ".button.secondary{background:#eff1ff;color:#3c4dbd}",
  "img{max-width:100%;height:auto}",
  "blockquote{margin:24px 0;padding:18px 24px;border-left:4px solid #7581e9;background:#f4f5ff}",
  "@media(max-width:640px){.hero{padding:54px 16px}.section{padding:42px 16px}.container{width:calc(100% - 28px)}}"
].join("\n");
const DEFAULT_HTML = '<header class="hero"><div class="container"><p>СТУДИЯ · ПОРТФОЛИО · БИЗНЕС</p><h1>Сайт, который работает на вас</h1><p>Расскажите о себе или продукте, покажите сильные стороны и помогите посетителю сделать следующий шаг.</p><a class="button" href="#features">Посмотреть возможности</a></div></header><section class="section container" id="features"><h2>Почему выбирают нас</h2><div class="grid"><article class="card"><h3>Быстрый запуск</h3><p>Готовая структура и понятная навигация.</p></article><article class="card"><h3>Адаптивный дизайн</h3><p>Страница аккуратно выглядит на телефоне и компьютере.</p></article><article class="card"><h3>Полный контроль</h3><p>Проект, изображения и экспорт остаются у вас.</p></article></div></section><section class="section container"><h2>Давайте обсудим проект</h2><p>Добавьте контакты и призыв к действию.</p><a class="button secondary" href="mailto:hello@example.com">Связаться</a></section>';
const TEMPLATES = {
  landing: {name:"Лендинг продукта", description:"Первый экран, преимущества, тарифы и призыв к действию", icon:"✦", html:'<header class="hero"><div class="container"><p>ВАШ ПРОДУКТ · 2026</p><h1>Превратите идею в результат</h1><p>Понятное предложение для людей, которым нужен хороший результат.</p><a class="button" href="#benefits">Начать</a></div></header><section class="section container" id="benefits"><h2>Что вы получите</h2><div class="grid"><article class="card"><h3>Просто</h3><p>Без сложных шагов.</p></article><article class="card"><h3>Надёжно</h3><p>Понятный и предсказуемый результат.</p></article><article class="card"><h3>Быстро</h3><p>Сосредоточьтесь на главном.</p></article></div></section><section class="section container"><h2>Готовы начать?</h2><a class="button" href="mailto:hello@example.com">Связаться с нами</a></section>'},
  portfolio: {name:"Портфолио", description:"Кейсы, навыки, отзывы и контакты", icon:"▣", html:'<header class="hero"><div class="container"><p>ПОРТФОЛИО · ИМЯ ФАМИЛИЯ</p><h1>Создаю вещи, которыми пользуются</h1><p>Коротко расскажите, чем занимаетесь и кому помогаете.</p><a class="button" href="#projects">Мои работы</a></div></header><section class="section container" id="projects"><h2>Избранные проекты</h2><div class="grid"><article class="card"><h3>Проект № 1</h3><p>Задача, процесс и измеримый результат.</p></article><article class="card"><h3>Проект № 2</h3><p>Задача, процесс и измеримый результат.</p></article><article class="card"><h3>Проект № 3</h3><p>Задача, процесс и измеримый результат.</p></article></div></section><section class="section container"><h2>Связаться</h2><p>Почта, телефон или ссылка на профиль.</p><a class="button" href="mailto:hello@example.com">Написать</a></section>'},
  business: {name:"Сайт компании", description:"Услуги, преимущества, команда и контакты", icon:"▤", html:'<header class="hero"><div class="container"><p>НАЗВАНИЕ КОМПАНИИ</p><h1>Помогаем бизнесу расти</h1><p>Опишите специализацию и главную ценность для заказчика.</p><a class="button" href="#services">Наши услуги</a></div></header><section class="section container" id="services"><h2>Услуги</h2><div class="grid"><article class="card"><h3>Консультация</h3><p>Разберём задачу и предложим план.</p></article><article class="card"><h3>Реализация</h3><p>Выполним работу и покажем результат.</p></article><article class="card"><h3>Поддержка</h3><p>Останемся рядом после запуска.</p></article></div></section><section class="section container"><h2>Контакты</h2><p>Адрес, часы работы, телефон и почта.</p><a class="button" href="mailto:hello@example.com">Оставить заявку</a></section>'},
  blog: {name:"Блог / журнал", description:"Обложка, статьи, категории и подписка", icon:"▧", html:'<header class="hero"><div class="container"><p>ЖУРНАЛ · БЛОГ</p><h1>Мысли и наблюдения</h1><p>Тема вашего блога и причина, по которой его стоит читать.</p></div></header><section class="section container"><h2>Последние материалы</h2><div class="grid"><article class="card"><p>12 ноября 2026</p><h3>Первая статья</h3><p>Краткое описание публикации и ссылка на полный материал.</p><a href="#">Читать →</a></article><article class="card"><p>10 ноября 2026</p><h3>Вторая статья</h3><p>Краткое описание публикации и ссылка на полный материал.</p><a href="#">Читать →</a></article><article class="card"><p>8 ноября 2026</p><h3>Третья статья</h3><p>Краткое описание публикации и ссылка на полный материал.</p><a href="#">Читать →</a></article></div></section>'},
  catalog: {name:"Каталог / магазин", description:"Карточки товаров, категории и преимущества", icon:"▦", html:'<header class="hero"><div class="container"><p>КАТАЛОГ</p><h1>Найдите то, что вам нужно</h1><p>Расскажите об ассортименте и условиях заказа.</p></div></header><section class="section container"><h2>Популярное</h2><div class="grid"><article class="card"><h3>Товар № 1</h3><p>Описание, характеристики и цена.</p><a class="button" href="mailto:hello@example.com">Заказать</a></article><article class="card"><h3>Товар № 2</h3><p>Описание, характеристики и цена.</p><a class="button" href="mailto:hello@example.com">Заказать</a></article><article class="card"><h3>Товар № 3</h3><p>Описание, характеристики и цена.</p><a class="button" href="mailto:hello@example.com">Заказать</a></article></div></section>'}
};
const BLOCKS = [
  {id:"section",label:"Секция",category:"Структура",content:'<section class="section"><div class="container"><h2>Новая секция</h2><p>Добавьте содержимое секции.</p></div></section>'},
  {id:"container",label:"Контейнер",category:"Структура",content:'<div class="container"><h2>Заголовок контейнера</h2><p>Содержимое.</p></div>'},
  {id:"hero",label:"Первый экран",category:"Структура",content:'<header class="hero"><div class="container"><p>КАТЕГОРИЯ</p><h1>Главный заголовок</h1><p>Объясните ценность одним предложением.</p><a class="button" href="#">Действие</a></div></header>'},
  {id:"columns",label:"2 колонки",category:"Структура",content:'<section class="section"><div class="container grid" style="grid-template-columns:repeat(2,minmax(0,1fr))"><div><h2>Левая часть</h2><p>Текст.</p></div><div><h2>Правая часть</h2><p>Текст.</p></div></div></section>'},
  {id:"three-columns",label:"3 колонки",category:"Структура",content:'<section class="section container"><div class="grid"><article class="card">Первая колонка</article><article class="card">Вторая колонка</article><article class="card">Третья колонка</article></div></section>'},
  {id:"navbar",label:"Навигация",category:"Структура",content:'<nav class="container" style="display:flex;gap:20px;padding:20px;align-items:center;justify-content:space-between"><strong>Бренд</strong><div style="display:flex;gap:16px;flex-wrap:wrap"><a href="#about">О нас</a><a href="#services">Услуги</a><a href="#contacts">Контакты</a></div></nav>'},
  {id:"footer",label:"Подвал",category:"Структура",content:'<footer class="section" style="background:#172033;color:white"><div class="container"><h2>Название компании</h2><p>Контакты · Социальные сети · Правовая информация</p></div></footer>'},
  {id:"heading",label:"Заголовок",category:"Текст",content:"<h2>Новый заголовок</h2>"},
  {id:"paragraph",label:"Абзац",category:"Текст",content:"<p>Начните писать текст здесь. Выделите его на странице, чтобы отредактировать.</p>"},
  {id:"rich-text",label:"Текстовый блок",category:"Текст",content:'<div class="container"><h2>Заголовок раздела</h2><p>Первый абзац текста. <strong>Важная мысль</strong> и <a href="#">полезная ссылка</a>.</p><p>Второй абзац с дополнительной информацией.</p><ul><li>Первый пункт</li><li>Второй пункт</li></ul></div>'},
  {id:"quote",label:"Цитата",category:"Текст",content:'<blockquote><p>«Хороший дизайн делает сложное простым»</p><cite>— Автор</cite></blockquote>'},
  {id:"list",label:"Список",category:"Текст",content:"<ul><li>Первый пункт</li><li>Второй пункт</li><li>Третий пункт</li></ul>"},
  {id:"button",label:"Кнопка",category:"Текст",content:'<p><a class="button" href="#">Нажмите здесь</a></p>'},
  {id:"link",label:"Ссылка",category:"Текст",content:'<p><a href="https://example.com">Текст ссылки →</a></p>'},
  {id:"image",label:"Изображение",category:"Медиа",content:'<figure><img src="https://placehold.co/900x520/e9edf7/26324a?text=Your+image" alt="Описание изображения"><figcaption>Подпись к изображению</figcaption></figure>'},
  {id:"gallery",label:"Галерея",category:"Медиа",content:'<section class="section container"><h2>Галерея</h2><div class="grid"><img src="https://placehold.co/600x420?text=1" alt="Изображение 1"><img src="https://placehold.co/600x420?text=2" alt="Изображение 2"><img src="https://placehold.co/600x420?text=3" alt="Изображение 3"></div></section>'},
  {id:"video",label:"Видео",category:"Медиа",content:'<section class="container section"><div style="aspect-ratio:16/9"><iframe title="Видео" src="https://www.youtube-nocookie.com/embed/VIDEO_ID" loading="lazy" allowfullscreen style="width:100%;height:100%;border:0"></iframe></div></section>'},
  {id:"map",label:"Карта",category:"Медиа",content:'<section class="container section"><iframe title="Карта" src="https://www.openstreetmap.org/export/embed.html?bbox=37.5%2C55.6%2C37.7%2C55.8&amp;layer=mapnik" style="width:100%;height:360px;border:0;border-radius:14px" loading="lazy"></iframe></section>'},
  {id:"cards",label:"Карточки",category:"Функции",content:'<section class="section container"><div class="grid"><article class="card"><h3>Карточка 1</h3><p>Краткое описание.</p></article><article class="card"><h3>Карточка 2</h3><p>Краткое описание.</p></article><article class="card"><h3>Карточка 3</h3><p>Краткое описание.</p></article></div></section>'},
  {id:"features",label:"Преимущества",category:"Функции",content:'<section class="section container"><h2>Наши преимущества</h2><div class="grid"><div><h3>✓ Быстро</h3><p>Описание преимущества.</p></div><div><h3>✓ Удобно</h3><p>Описание преимущества.</p></div><div><h3>✓ Надёжно</h3><p>Описание преимущества.</p></div></div></section>'},
  {id:"faq",label:"Вопросы / FAQ",category:"Функции",content:'<section class="section container"><h2>Частые вопросы</h2><details><summary>Как это работает?</summary><p>Добавьте ответ.</p></details><details><summary>Сколько это стоит?</summary><p>Добавьте ответ.</p></details></section>'},
  {id:"form",label:"Форма связи",category:"Функции",content:'<section class="section container"><h2>Оставить заявку</h2><form action="mailto:hello@example.com" method="post" enctype="text/plain"><label>Ваше имя<br><input name="name" required style="padding:11px;width:100%;max-width:440px"></label><p><label>Электронная почта<br><input type="email" name="email" required style="padding:11px;width:100%;max-width:440px"></label></p><p><label>Сообщение<br><textarea name="message" rows="4" style="padding:11px;width:100%;max-width:440px"></textarea></label></p><button class="button" type="submit">Отправить</button></form></section>'},
  {id:"pricing",label:"Тарифы",category:"Бизнес",content:'<section class="section container"><h2>Тарифы</h2><div class="grid"><article class="card"><h3>Старт</h3><p style="font-size:28px;font-weight:800">Бесплатно</p><p>Описание тарифа.</p><a class="button" href="#">Выбрать</a></article><article class="card"><h3>Профи</h3><p style="font-size:28px;font-weight:800">2 990 ₽</p><p>Описание тарифа.</p><a class="button" href="#">Выбрать</a></article><article class="card"><h3>Бизнес</h3><p style="font-size:28px;font-weight:800">По запросу</p><p>Описание тарифа.</p><a class="button" href="#">Связаться</a></article></div></section>'},
  {id:"testimonial",label:"Отзыв",category:"Бизнес",content:'<section class="section container"><blockquote><p>«Отличный результат, всё понятно и вовремя»</p><cite>— Имя клиента, компания</cite></blockquote></section>'},
  {id:"contact",label:"Контакты",category:"Бизнес",content:'<section class="section container" id="contacts"><h2>Контакты</h2><p>Телефон: +7 (000) 000-00-00</p><p>Почта: hello@example.com</p><p>Адрес и часы работы.</p></section>'},
  {id:"divider",label:"Разделитель",category:"Прочее",content:'<hr style="border:0;border-top:1px solid #d9dfeb;margin:32px 0">'},
  {id:"spacer",label:"Пустое место",category:"Прочее",content:'<div style="height:48px"></div>'},
  {id:"social",label:"Социальные ссылки",category:"Прочее",content:'<div class="container" style="display:flex;gap:18px;padding:16px"><a href="#">Telegram</a><a href="#">ВКонтакте</a><a href="#">YouTube</a></div>'},
  {id:"table",label:"Таблица",category:"Прочее",content:'<div class="container section"><table style="width:100%;border-collapse:collapse"><thead><tr><th style="text-align:left;padding:10px;border-bottom:2px solid #ccd3e0">Параметр</th><th style="text-align:left;padding:10px;border-bottom:2px solid #ccd3e0">Значение</th></tr></thead><tbody><tr><td style="padding:10px;border-bottom:1px solid #e2e6ed">Пример</td><td style="padding:10px;border-bottom:1px solid #e2e6ed">Данные</td></tr></tbody></table></div>'},
  {id:"code",label:"Код / встраивание",category:"Прочее",content:'<div class="container section"><pre style="padding:18px;background:#172033;color:#e8edff;border-radius:12px;overflow:auto"><code>Ваш код или встроенный виджет</code></pre></div>'}
];

let api = null;
let editor = null;
let editorMode = "grapes";
let currentPath = "";
let projectTitle = "Мой сайт";
let pageMeta = {};
let activePageId = null;
let saveTimer = null;
let saving = false;
let dirty = false;
let fallback = null;
const defaultDocument = {
  format:"pulpit-page-project", version:1, title:"Мой сайт", language:"ru", pageMeta:{},
  projectData:{pages:[{id:"home",name:"Главная",component:DEFAULT_HTML,styles:""}],styles:[]}
};

function toast(message, kind) {
  const item = document.createElement("div");
  item.className = "toast " + (kind || "");
  item.textContent = message;
  $("toast-region").appendChild(item);
  window.setTimeout(() => item.remove(), 3600);
}
function status(text, bad) {
  $("dirty-indicator").textContent = text;
  $("dirty-indicator").style.color = bad ? "#ff9e9e" : "";
  $("save-status").textContent = text;
}
function showModal(title, content, buttons) {
  $("modal-title").textContent = title;
  $("modal-body").innerHTML = content;
  $("modal-foot").innerHTML = "";
  (buttons || []).forEach((item) => {
    const b = document.createElement("button");
    b.className = "modal-button " + (item.primary ? "primary" : "");
    b.textContent = item.label;
    b.addEventListener("click", item.action);
    $("modal-foot").appendChild(b);
  });
  $("modal-overlay").hidden = false;
}
function closeModal() {
  $("modal-overlay").hidden = true;
  $("modal-body").innerHTML = "";
}
function slugify(value) {
  const map = {"а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"yo","ж":"zh","з":"z","и":"i","й":"y","к":"k","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r","с":"s","т":"t","у":"u","ф":"f","х":"kh","ц":"ts","ч":"ch","ш":"sh","щ":"sch","ъ":"","ы":"y","ь":"","э":"e","ю":"yu","я":"ya"};
  return String(value || "").toLowerCase().split("").map(ch => map[ch] === undefined ? ch : map[ch]).join("").replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"").slice(0,72) || "page";
}
function currentGrapesPage() {
  return editor ? editor.Pages.getSelected() : null;
}
function pageId(page) {
  return page ? (page.getId ? page.getId() : page.get("id")) : "home";
}
function currentPageMeta() {
  const page = currentGrapesPage();
  const id = pageId(page);
  if (!pageMeta[id]) pageMeta[id] = {title: page && page.get("name") || "Страница", description:"", slug:slugify(page && page.get("name") || "page")};
  return pageMeta[id];
}
function defaultProject() {
  return JSON.parse(JSON.stringify(defaultDocument));
}
function makeGrapesEditor(doc) {
  editorMode = "grapes";
  document.body.classList.remove("offline-mode");
  $("editor-mode").textContent = "GrapesJS · визуальный режим";
  $("fallback-frame").hidden = true;
  $("gjs").style.display = "block";
  const project = doc && doc.projectData && doc.projectData.pages && doc.projectData.pages.length ? doc.projectData : defaultDocument.projectData;
  pageMeta = Object.assign({}, doc && doc.pageMeta || {});
  window.projectLanguage = doc && doc.language || "ru";
  const first = project.pages[0];
  editor = grapesjs.init({
    container:"#gjs",
    height:"100%",
    width:"100%",
    fromElement:false,
    storageManager:false,
    noticeOnUnload:false,
    panels:{defaults:[]},
    components:first && first.component || DEFAULT_HTML,
    style:first && first.styles || DEFAULT_CSS,
    blockManager:{appendTo:"#blocks"},
    layerManager:{appendTo:"#layers"},
    styleManager:{
      appendTo:"#styles",
      sectors:[
        {name:"Размеры и расположение",open:true,properties:["display","position","width","height","max-width","min-height","margin","padding","gap","flex-direction","justify-content","align-items","grid-template-columns"]},
        {name:"Текст",open:false,properties:["font-family","font-size","font-weight","color","line-height","letter-spacing","text-align","text-decoration"]},
        {name:"Фон и границы",open:false,properties:["background-color","background","border","border-radius","box-shadow","opacity"]},
        {name:"Дополнительно",open:false,properties:["overflow","cursor","transition","transform"]}
      ]
    },
    traitManager:{appendTo:"#traits"},
    selectorManager:{componentFirst:true},
    deviceManager:{devices:[
      {id:"Desktop",name:"Desktop",width:""},
      {id:"Tablet",name:"Tablet",width:"768px",height:"1024px"},
      {id:"Mobile",name:"Mobile",width:"390px",height:"844px"}
    ]},
    assetManager:{assets:[],upload:false,embedAsBase64:false},
    canvas:{styles:[]}
  });
  if (project.pages && project.pages.length > 1) {
    editor.loadProjectData(project);
  } else if (doc && doc.projectData && doc.projectData.pages) {
    editor.loadProjectData(project);
  }
  registerBlocks();
  editor.on("update", markDirty);
  editor.on("page", () => { refreshPages(); syncSeoFields(); markDirty(); });
  editor.on("component:selected", (component) => {
    $("selection-status").textContent = component ? "Элемент выбран" : "Ничего не выбрано";
    $("component-type").textContent = component ? (component.getName ? component.getName() : component.get("type") || "Элемент") : "Выберите элемент";
    $("right-styles").scrollTop = 0;
    showRightTab("styles");
  });
  editor.on("component:deselected", () => {
    $("selection-status").textContent = "Ничего не выбрано";
    $("component-type").textContent = "Выберите элемент";
  });
  editor.on("asset:add", markDirty);
  refreshPages();
  syncSeoFields();
  $("loading").hidden = true;
}
function registerBlocks() {
  const manager = editor.BlockManager;
  BLOCKS.forEach((block) => manager.add(block.id,{
    label:block.label,
    category:block.category,
    content:block.content,
    media:"<span style='font-size:20px'>＋</span>",
    select:true
  }));
}
function refreshPages() {
  if (editorMode !== "grapes" || !editor) return;
  const select = $("page-select");
  const pages = editor.Pages.getAll();
  const selected = currentGrapesPage();
  const selectedId = pageId(selected);
  select.innerHTML = "";
  pages.forEach((page,index) => {
    const option = document.createElement("option");
    option.value = pageId(page);
    option.textContent = page.get("name") || "Страница " + (index + 1);
    select.appendChild(option);
  });
  select.value = selectedId;
  activePageId = selectedId;
  syncSeoFields();
}
function selectPage(id) {
  if (editorMode === "grapes" && editor) {
    editor.Pages.select(id);
    refreshPages();
    syncSeoFields();
  } else if (fallback) {
    fallback.index = Math.max(0,fallback.pages.findIndex(p => p.id === id));
    renderFallback();
  }
}
function addPage() {
  const name = window.prompt("Название новой страницы", "Новая страница");
  if (!name || !name.trim()) return;
  if (editorMode === "grapes") {
    const id = slugify(name) + "-" + Math.random().toString(36).slice(2,6);
    const page = editor.Pages.add({id,name:name.trim(),component:'<main class="container section"><h1>'+escapeHtml(name.trim())+'</h1><p>Начните наполнять страницу.</p></main>',styles:""});
    editor.Pages.select(page);
    pageMeta[id] = {title:name.trim() + " — " + projectTitle,description:"",slug:id};
    refreshPages();
  } else {
    const id = slugify(name) + "-" + Math.random().toString(36).slice(2,6);
    fallback.pages.push({id,name:name.trim(),title:name.trim() + " — " + projectTitle,description:"",slug:id,html:'<main><h1>'+escapeHtml(name.trim())+'</h1><p>Начните наполнять страницу.</p></main>'});
    fallback.index = fallback.pages.length - 1;
    renderFallback();
  }
  markDirty();
}
function renamePage() {
  const page = editorMode === "grapes" ? currentGrapesPage() : fallback && fallback.pages[fallback.index];
  if (!page) return;
  const old = editorMode === "grapes" ? page.get("name") : page.name;
  const name = window.prompt("Название страницы", old || "");
  if (!name || !name.trim()) return;
  if (editorMode === "grapes") {
    page.set("name",name.trim());
    const meta = currentPageMeta();
    meta.title = name.trim() + " — " + projectTitle;
    refreshPages();
  } else {
    page.name = name.trim();
    page.title = name.trim() + " — " + projectTitle;
    renderFallback();
  }
  markDirty();
}
function deletePage() {
  if (editorMode === "grapes") {
    const pages = editor.Pages.getAll();
    if (pages.length <= 1) return toast("В проекте должна остаться хотя бы одна страница.","error");
    const page = currentGrapesPage();
    if (!window.confirm("Удалить страницу «" + (page.get("name") || "Страница") + "»?")) return;
    const id = pageId(page);
    editor.Pages.remove(page);
    delete pageMeta[id];
    refreshPages();
  } else if (fallback && fallback.pages.length > 1) {
    if (!window.confirm("Удалить текущую страницу?")) return;
    fallback.pages.splice(fallback.index,1);
    fallback.index = Math.max(0,fallback.index-1);
    renderFallback();
  } else {
    return toast("Нельзя удалить последнюю страницу.","error");
  }
  markDirty();
}
function syncSeoFields() {
  if (editorMode === "grapes" && editor) {
    const page = currentGrapesPage();
    if (!page) return;
    const meta = currentPageMeta();
    $("seo-title").value = meta.title || page.get("name") || "";
    $("seo-description").value = meta.description || "";
    $("seo-slug").value = meta.slug || slugify(page.get("name") || "page");
    $("site-language").value = window.projectLanguage || "ru";
  } else if (fallback) {
    const page = fallback.pages[fallback.index];
    if (!page) return;
    $("seo-title").value = page.title || page.name;
    $("seo-description").value = page.description || "";
    $("seo-slug").value = page.slug || slugify(page.name);
    $("site-language").value = fallback.language || "ru";
  }
  $("description-count").textContent = $("seo-description").value.length + " / 320";
}
function updateSeoFields() {
  if (editorMode === "grapes" && editor) {
    const meta = currentPageMeta();
    meta.title = $("seo-title").value;
    meta.description = $("seo-description").value;
    meta.slug = slugify($("seo-slug").value);
    window.projectLanguage = $("site-language").value;
  } else if (fallback) {
    const page = fallback.pages[fallback.index];
    page.title = $("seo-title").value;
    page.description = $("seo-description").value;
    page.slug = slugify($("seo-slug").value);
    fallback.language = $("site-language").value;
  }
  $("description-count").textContent = $("seo-description").value.length + " / 320";
  markDirty();
}
function showLeftTab(name) {
  document.querySelectorAll("[data-left-tab]").forEach((b) => b.classList.toggle("active",b.dataset.leftTab === name));
  ["blocks","layers","media"].forEach((key) => $("left-" + key).classList.toggle("active",key === name));
  if (name === "layers" && editor) editor.trigger("component:mount");
}
function showRightTab(name) {
  document.querySelectorAll("[data-right-tab]").forEach((b) => b.classList.toggle("active",b.dataset.rightTab === name));
  ["styles","traits","seo"].forEach((key) => $("right-" + key).classList.toggle("active",key === name));
}
function getGrapesExportPages() {
  return editor.Pages.getAll().map((page,index) => {
    const id = pageId(page);
    const meta = pageMeta[id] || {};
    const component = page.getMainComponent();
    return {
      id:id,name:page.get("name") || "Страница " + (index+1),
      slug:meta.slug || slugify(page.get("name") || "page"),
      title:meta.title || page.get("name") || projectTitle,
      description:meta.description || "",
      html:editor.getHtml({component:component}),
      css:editor.getCss({component:component}),
      js:editor.getJs ? editor.getJs({component:component}) : ""
    };
  });
}
function snapshotDocument() {
  if (editorMode === "grapes" && editor) {
    return {
      format:"pulpit-page-project",version:1,title:projectTitle,
      language:window.projectLanguage || $("site-language").value || "ru",
      pageMeta:pageMeta,projectData:editor.getProjectData()
    };
  }
  return {
    format:"pulpit-page-project",version:1,title:projectTitle,language:fallback.language || "ru",
    pageMeta:{},
    projectData:{fallback:true,pages:fallback.pages.map(p => ({...p})),css:fallback.css}
  };
}
function exportPayload() {
  return {
    title:projectTitle,
    language:editorMode === "grapes" ? (window.projectLanguage || "ru") : fallback.language || "ru",
    pages:editorMode === "grapes" ? getGrapesExportPages() : fallback.pages.map(p => ({
      id:p.id,name:p.name,slug:p.slug,title:p.title,description:p.description,
      html:p.html,css:fallback.css,js:""
    }))
  };
}
function markDirty() {
  dirty = true;
  status("Есть изменения · сохраняю…");
  if (saveTimer) window.clearTimeout(saveTimer);
  saveTimer = window.setTimeout(autoSave,1200);
}
async function autoSave() {
  if (!api || saving) return;
  saving = true;
  try {
    await api.save_project(JSON.stringify(snapshotDocument()));
    dirty = false;
    status("Сохранено локально");
  } catch (error) {
    status("Ошибка автосохранения",true);
    console.warn(error);
  } finally { saving = false; }
}
async function saveProject(showMessage) {
  if (!api) return toast("Локальный мост ещё не готов.","error");
  try {
    const result = await api.save_project(JSON.stringify(snapshotDocument()));
    dirty = false;
    status("Сохранено локально");
    if (showMessage !== false) toast("Проект сохранён: " + result.path,"success");
  } catch (error) {
    toast("Не удалось сохранить проект: " + error.message,"error");
  }
}
async function saveProjectAs() {
  if (!api) return;
  try {
    const result = await api.save_project_as(JSON.stringify(snapshotDocument()));
    if (result) {
      dirty = false;
      currentPath = result.path;
      status("Сохранено: " + result.path);
      toast("Проект сохранён в выбранный файл.","success");
    }
  } catch (error) { toast("Ошибка сохранения: " + error.message,"error"); }
}
async function openProject() {
  if (!api) return;
  try {
    const result = await api.open_project();
    if (!result) return;
    projectTitle = result.document.title || "Мой сайт";
    $("project-title").value = projectTitle;
    if (result.document.projectData && result.document.projectData.fallback) {
      initializeFallback(result.document);
    } else if (window.grapesjs) {
      if (editor) editor.destroy();
      makeGrapesEditor(result.document);
      $("site-language").value = result.document.language || "ru";
    } else {
      initializeFallback(result.document);
    }
    currentPath = result.projectPath || "";
    renderMedia(result.assets || []);
    dirty = false;
    status("Проект открыт");
    toast("Проект загружен.","success");
  } catch (error) { toast("Не удалось открыть проект: " + error.message,"error"); }
}
async function exportSite() {
  if (!api) return toast("Экспорт ZIP доступен из настольного приложения.","error");
  try {
    const result = await api.export_site(JSON.stringify(exportPayload()));
    if (result) toast("Сайт экспортирован · страниц: " + result.pages + " · ресурсов: " + result.assets + " · " + result.bytes + " байт","success");
  } catch (error) { toast("Ошибка экспорта: " + error.message,"error"); }
}
function addAssetToGrapes(item) {
  if (editorMode === "grapes" && editor) editor.AssetManager.add({src:item.src,name:item.name,type:"image"});
}
async function importAssets(files) {
  const chosen = Array.from(files || []);
  if (!chosen.length) return;
  const imageFiles = chosen.filter(f => /^image\/(png|jpeg|webp|gif|bmp)$/i.test(f.type));
  if (imageFiles.length !== chosen.length) toast("Пропущены файлы неподдерживаемого типа.","error");
  const encoded = await Promise.all(imageFiles.map(file => new Promise((resolve,reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve({name:file.name,data:String(reader.result)});
    reader.onerror = () => reject(new Error("Не удалось прочитать " + file.name));
    reader.readAsDataURL(file);
  })));
  try {
    const stored = await api.import_assets(JSON.stringify(encoded));
    stored.forEach(addAssetToGrapes);
    renderMedia((await api.get_initial_state()).assets || stored);
    showLeftTab("media");
    if (editorMode === "grapes") editor.AssetManager.open();
    markDirty();
    toast("Добавлено изображений: " + stored.length,"success");
  } catch (error) { toast("Ошибка импорта: " + error.message,"error"); }
}
function renderMedia(items) {
  const root = $("media-list");
  root.innerHTML = "";
  (items || []).forEach(item => {
    const card = document.createElement("div");
    card.className = "media-item";
    const img = document.createElement("img");
    img.src = item.src;
    img.alt = item.name;
    const name = document.createElement("span");
    name.textContent = item.name;
    const use = document.createElement("button");
    use.textContent = "Добавить на страницу";
    use.addEventListener("click",() => {
      if (editorMode === "grapes" && editor) {
        const selected = editor.getSelected();
        if (selected && selected.is && selected.is("image")) selected.addAttributes({src:item.src,alt:item.name});
        else editor.addComponents('<figure><img src="' + item.src + '" alt="' + escapeHtml(item.name) + '"></figure>');
      } else if (fallback) {
        appendFallback('<figure><img src="' + item.src + '" alt="' + escapeHtml(item.name) + '"></figure>');
      }
      markDirty();
    });
    card.append(img,name,use);
    root.appendChild(card);
  });
  if (!items || !items.length) root.innerHTML = '<p class="panel-note">Медиатека пока пуста. Добавьте фотографии или логотипы.</p>';
}
function showCodeModal() {
  let html = "", css = "";
  if (editorMode === "grapes" && editor) {
    html = editor.getHtml();
    css = editor.getCss();
  } else if (fallback) {
    const p = fallback.pages[fallback.index];
    html = p.html;
    css = fallback.css;
  }
  const body = '<p class="modal-help">Это исходный код текущей страницы. Изменения можно применить обратно в проект.</p><label class="modal-label" for="source-html">HTML</label><textarea id="source-html" class="modal-code" spellcheck="false"></textarea><label class="modal-label" for="source-css">CSS</label><textarea id="source-css" class="modal-code" spellcheck="false"></textarea>';
  showModal("HTML и CSS",body,[
    {label:"Скопировать",action:() => copyCode()},
    {label:"Применить код",primary:true,action:() => applyCode()}
  ]);
  $("source-html").value = html;
  $("source-css").value = css;
}
async function copyCode() {
  const text = $("source-html").value + "\n\n/* CSS */\n" + $("source-css").value;
  try { await navigator.clipboard.writeText(text); toast("Код скопирован.","success"); }
  catch (error) { toast("Браузер запретил доступ к буферу обмена.","error"); }
}
function applyCode() {
  const html = $("source-html").value;
  const css = $("source-css").value;
  if (editorMode === "grapes" && editor) {
    editor.setComponents(html);
    editor.setStyle(css);
  } else if (fallback) {
    fallback.pages[fallback.index].html = html;
    fallback.css = css;
    renderFallback();
  }
  closeModal();
  markDirty();
  toast("HTML и CSS применены.","success");
}
function showTemplates() {
  let cards = "";
  Object.keys(TEMPLATES).forEach(key => {
    const item = TEMPLATES[key];
    cards += '<button class="template-card" data-template="' + key + '"><div class="template-preview">' + item.icon + '</div><strong>' + item.name + '</strong><small>' + item.description + '</small></button>';
  });
  showModal("Готовые шаблоны",'<p class="modal-help">Выберите основу — всё содержимое останется редактируемым. Это не картинка, а настоящие блоки и текст.</p><div class="modal-grid">' + cards + '</div>',[]);
  document.querySelectorAll("[data-template]").forEach(button => button.addEventListener("click",() => applyTemplate(button.dataset.template)));
}
function applyTemplate(key) {
  const item = TEMPLATES[key];
  if (!item) return;
  if (editorMode === "grapes" && editor) {
    const id = "home";
    editor.loadProjectData({pages:[{id:id,name:"Главная",component:item.html,styles:DEFAULT_CSS}],styles:[]});
    pageMeta = {home:{title:item.name,description:item.description,slug:"index"}};
    refreshPages();
  } else if (fallback) {
    fallback.pages = [{id:"home",name:"Главная",title:item.name,description:item.description,slug:"index",html:item.html}];
    fallback.css = DEFAULT_CSS;
    fallback.index = 0;
    renderFallback();
  }
  projectTitle = item.name;
  $("project-title").value = projectTitle;
  closeModal();
  markDirty();
  toast("Шаблон загружен. Замените демонстрационные тексты своими.","success");
}
function auditPage() {
  const data = exportPayload();
  const page = data.pages.find(p => p.id === activePageId) || data.pages[0];
  const parser = new DOMParser();
  const doc = parser.parseFromString(page.html || "","text/html");
  const issues = [];
  const h1 = doc.querySelectorAll("h1").length;
  const images = Array.from(doc.querySelectorAll("img"));
  const missingAlt = images.filter(img => !img.hasAttribute("alt")).length;
  const emptyLinks = Array.from(doc.querySelectorAll("a")).filter(a => !a.getAttribute("href")).length;
  const emptyButtons = Array.from(doc.querySelectorAll("button")).filter(b => !b.textContent.trim() && !b.getAttribute("aria-label")).length;
  const headingSequence = Array.from(doc.querySelectorAll("h1,h2,h3,h4,h5,h6")).map(x => Number(x.tagName.slice(1)));
  const skipped = headingSequence.some((level,i) => i > 0 && level > headingSequence[i-1] + 1);
  if (!h1) issues.push("Добавьте главный заголовок H1.");
  if (h1 > 1) issues.push("На странице несколько H1. Проверьте иерархию заголовков.");
  if (missingAlt) issues.push("У " + missingAlt + " изображений отсутствует alt-текст.");
  if (emptyLinks) issues.push("У " + emptyLinks + " ссылок нет адреса href.");
  if (emptyButtons) issues.push("У " + emptyButtons + " кнопок нет текста или aria-label.");
  if (skipped) issues.push("В заголовках пропущен уровень (например, H2 → H4).");
  if (!(page.description || "").trim()) issues.push("Добавьте SEO-описание страницы.");
  const textLength = doc.body.textContent.trim().length;
  if (textLength < 120) issues.push("На странице мало текстового содержания.");
  const result = $("seo-result");
  if (issues.length) {
    result.className = "audit-result warn";
    result.innerHTML = "<b>Найдено замечаний: " + issues.length + "</b><ul>" + issues.map(x => "<li>" + escapeHtml(x) + "</li>").join("") + "</ul>";
  } else {
    result.className = "audit-result good";
    result.textContent = "Базовая проверка пройдена: главный заголовок, описание, ссылки, изображения и структура выглядят корректно. Это не полный SEO-аудит и не проверка контрастности.";
  }
  showRightTab("seo");
  return issues;
}
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
}
function togglePreview() {
  document.body.classList.toggle("preview-mode");
  if (editorMode === "grapes" && editor) {
    try { editor.runCommand("core:preview"); } catch (error) { console.debug(error); }
    window.setTimeout(() => editor.refresh(),120);
  }
  $("btn-preview").textContent = document.body.classList.contains("preview-mode") ? "✕" : "▷";
}
function initializeFallback(doc) {
  if (editor) { try { editor.destroy(); } catch (error) { console.debug(error); } editor = null; }
  editorMode = "fallback";
  document.body.classList.add("offline-mode");
  $("gjs").style.display = "none";
  $("fallback-frame").hidden = false;
  $("editor-mode").textContent = "Автономный режим · без CDN";
  const data = doc && doc.projectData && doc.projectData.pages ? doc.projectData : defaultDocument.projectData;
  let pages;
  if (data.fallback) pages = data.pages;
  else pages = data.pages.map((page,i) => ({
    id:page.id || "page-"+i,name:page.name || "Страница "+(i+1),title:page.name || "",description:"",
    slug:i===0?"index":"page-"+i,html:page.component || "<h1>Новая страница</h1>"
  }));
  fallback = {pages:pages,css:data.css || DEFAULT_CSS,index:0,language:doc && doc.language || "ru"};
  const custom = $("fallback-properties");
  custom.innerHTML = '<label class="modal-label" for="fallback-css">CSS текущего проекта</label><textarea id="fallback-css" class="modal-code" style="height:230px"></textarea><p class="panel-note">Автономный режим сохраняет редактирование HTML в холсте, добавление блоков и CSS. Для расширенной панели стилей подключите интернет и перезапустите конструктор.</p>';
  $("fallback-css").value = fallback.css;
  $("fallback-css").addEventListener("input",() => {
    fallback.css = $("fallback-css").value;
    markDirty();
  });
  renderFallback();
  $("loading").hidden = true;
}
function renderFallback() {
  if (!fallback) return;
  const select = $("page-select");
  select.innerHTML = "";
  fallback.pages.forEach((p,i) => {
    const o = document.createElement("option");
    o.value = p.id;
    o.textContent = p.name || "Страница "+(i+1);
    select.appendChild(o);
  });
  select.value = fallback.pages[fallback.index].id;
  const page = fallback.pages[fallback.index];
  activePageId = page.id;
  const frame = $("fallback-frame");
  frame.srcdoc = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>' + fallback.css + '</style><style>body{min-height:100vh;outline:0;}</style></head><body contenteditable="true">' + page.html + '</body></html>';
  frame.onload = () => {
    try {
      const body = frame.contentDocument.body;
      body.contentEditable = "true";
      body.addEventListener("input",() => {
        page.html = body.innerHTML;
        markDirty();
      });
    } catch (error) { console.warn(error); }
  };
  $("seo-title").value = page.title || page.name;
  $("seo-description").value = page.description || "";
  $("seo-slug").value = page.slug || slugify(page.name);
  $("site-language").value = fallback.language;
  $("description-count").textContent = $("seo-description").value.length + " / 320";
  $("selection-status").textContent = "Редактирование в автономном режиме";
  $("component-type").textContent = "HTML-страница";
}
function appendFallback(snippet) {
  if (!fallback) return;
  fallback.pages[fallback.index].html += snippet;
  renderFallback();
  markDirty();
}
function fallbackAddBlock(id) {
  const block = BLOCKS.find(x => x.id === id);
  if (block) appendFallback(block.content);
}
function initFallbackBlocks() {
  $("fallback-blocks").innerHTML = "";
  BLOCKS.forEach(block => {
    const button = document.createElement("button");
    button.textContent = block.label;
    button.addEventListener("click",() => fallbackAddBlock(block.id));
    $("fallback-blocks").appendChild(button);
  });
}
function getFallbackExportPages() {
  return fallback.pages.map(p => ({id:p.id,name:p.name,slug:p.slug,title:p.title,description:p.description,html:p.html,css:fallback.css,js:""}));
}
function loadDocument(doc) {
  projectTitle = doc.title || "Мой сайт";
  $("project-title").value = projectTitle;
  if (doc.projectData && doc.projectData.fallback) {
    initializeFallback(doc);
  } else if (window.grapesjs && !window.PULPIT_GRAPES_UNAVAILABLE) {
    if (editor) editor.destroy();
    makeGrapesEditor(doc);
  } else {
    initializeFallback(doc);
  }
}
async function initializeApp() {
  initFallbackBlocks();
  $("loading").hidden = false;
  if (api) {
    try {
      const initial = await api.get_initial_state();
      if (initial.document) loadDocument(initial.document);
      else if (window.grapesjs && !window.PULPIT_GRAPES_UNAVAILABLE) makeGrapesEditor(defaultProject());
      else initializeFallback(defaultProject());
      currentPath = initial.projectPath || "";
      renderMedia(initial.assets || []);
    } catch (error) {
      initializeFallback(defaultProject());
      toast("Локальный проект не удалось прочитать: " + error.message,"error");
    }
  } else {
    initializeFallback(defaultProject());
  }
  $("loading").hidden = true;
}
function handleProjectTitle() {
  projectTitle = $("project-title").value.trim() || "Мой сайт";
  markDirty();
}
function bindEvents() {
  document.querySelectorAll("[data-left-tab]").forEach(b => b.addEventListener("click",() => showLeftTab(b.dataset.leftTab)));
  document.querySelectorAll("[data-right-tab]").forEach(b => b.addEventListener("click",() => showRightTab(b.dataset.rightTab)));
  $("btn-open").addEventListener("click",openProject);
  $("btn-save").addEventListener("click",() => saveProject(true));
  $("btn-save-as").addEventListener("click",saveProjectAs);
  $("btn-export").addEventListener("click",exportSite);
  $("btn-code").addEventListener("click",showCodeModal);
  $("btn-templates").addEventListener("click",showTemplates);
  $("btn-preview").addEventListener("click",togglePreview);
  $("btn-audit").addEventListener("click",auditPage);
  $("btn-page-audit").addEventListener("click",auditPage);
  $("btn-add-page").addEventListener("click",addPage);
  $("btn-rename-page").addEventListener("click",renamePage);
  $("btn-delete-page").addEventListener("click",deletePage);
  $("btn-deselect").addEventListener("click",() => { if (editor) editor.select(null); });
  $("btn-delete-component").addEventListener("click",() => { if (editor && editor.getSelected()) { editor.getSelected().remove(); markDirty(); } });
  $("btn-add-media").addEventListener("click",() => $("file-assets").click());
  $("btn-open-assets").addEventListener("click",() => { showLeftTab("media"); if (editor) editor.AssetManager.open(); });
  $("file-assets").addEventListener("change",async e => { await importAssets(e.target.files); e.target.value = ""; });
  $("page-select").addEventListener("change",e => selectPage(e.target.value));
  $("project-title").addEventListener("input",handleProjectTitle);
  ["seo-title","seo-description","seo-slug","site-language"].forEach(id => $(id).addEventListener("input",updateSeoFields));
  $("modal-close").addEventListener("click",closeModal);
  $("modal-overlay").addEventListener("click",e => { if (e.target === $("modal-overlay")) closeModal(); });
  document.querySelectorAll("[data-device]").forEach(b => b.addEventListener("click",() => {
    document.querySelectorAll("[data-device]").forEach(x => x.classList.toggle("active",x===b));
    $("viewport-label").textContent = b.dataset.device;
    if (editorMode === "grapes" && editor) {
      editor.Devices.select(b.dataset.device);
      window.setTimeout(() => editor.refresh(),80);
    }
  }));
  $("btn-undo").addEventListener("click",() => {if (editor) editor.runCommand("core:undo");});
  $("btn-redo").addEventListener("click",() => {if (editor) editor.runCommand("core:redo");});
  document.addEventListener("keydown",e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {e.preventDefault();saveProject(true);}
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z" && editor) {e.preventDefault();editor.runCommand(e.shiftKey ? "core:redo" : "core:undo");}
    if (e.key === "Escape" && !$("modal-overlay").hidden) closeModal();
  });
}
let eventsBound = false;
let bootstrapped = false;
function bindEventsOnce() {
  if (eventsBound) return;
  eventsBound = true;
  bindEvents();
}
window.addEventListener("pywebviewready",async() => {
  if (bootstrapped) return;
  bootstrapped = true;
  api = window.pywebview.api;
  bindEventsOnce();
  await initializeApp();
});
window.addEventListener("DOMContentLoaded",() => {
  window.setTimeout(() => {
    if (!bootstrapped && !api) {
      bootstrapped = true;
      bindEventsOnce();
      initializeFallback(defaultProject());
      $("loading").hidden = true;
      toast("Запущен автономный предпросмотр. Файловый экспорт доступен в настольном приложении.","warn");
    }
  },2500);
});
