#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bootstrap.py — документация для API-first финтеха в один клик.

Что делает:
  1. Проверяет окружение (Node 20+, npm, npx).
  2. Разворачивает ЭТАЛОННЫЙ сайт официальным генератором мейнтейнеров
     openapi-плагина (create-docusaurus-openapi-docs) — не самосбор.
  3. Накладывает поверх авторский контент: структуру разделов, сценарии,
     каталог ошибок, spectral-пресет, CI для GitLab и GitHub.
  4. Персонализирует (4 вопроса), подключает вашу OpenAPI-спеку.
  5. Ставит зависимости, генерирует референс, запускает предпросмотр.

Запуск:
  python3 bootstrap.py                  # интерактивно, сайт в ./api-docs
  python3 bootstrap.py my-docs          # своё имя папки
  python3 bootstrap.py --defaults       # без вопросов, демо-значения
  python3 bootstrap.py --no-start       # всё сделать, но dev-сервер не запускать
  python3 bootstrap.py --skip-scaffold  # если эталонный сайт уже развёрнут в папке

Зависимости самого скрипта: только Python 3.9+.
"""
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULTS = ["PayFlow API", "PayFlow", "https://docs.payflow.example", ""]

# ------------------------------------------------------------------ вывод
USE_COLOR = sys.stdout.isatty()


def c(code, s):
    return f"\033[{code}m{s}\033[0m" if USE_COLOR else s


def step(n, total, title):
    print(f"\n{c('1;36', f'[{n}/{total}]')} {c('1', title)}")


def ok(msg):
    print(f"  {c('32', '✓')} {msg}")


def warn(msg):
    print(f"  {c('33', '!')} {msg}")


def fail(msg, hint=None):
    print(f"  {c('31', '✗')} {msg}")
    if hint:
        print(f"    {c('2', hint)}")
    sys.exit(1)


def run(cmd, cwd=None, interactive=False):
    """Запуск команды; interactive=True — вывод и ввод идут пользователю."""
    if interactive:
        return subprocess.run(cmd, cwd=cwd).returncode
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return r


# ------------------------------------------------------------------ шаги
def preflight():
    step(1, 7, "Проверка окружения")
    for tool, hint in [("node", "Установите Node.js 20+ с nodejs.org (LTS) или через nvm: nvm install 22"),
                       ("npm", "npm ставится вместе с Node.js"),
                       ("npx", "npx ставится вместе с npm >= 5.2")]:
        path = shutil.which(tool)
        if not path:
            fail(f"{tool} не найден в PATH", hint)
    v = run(["node", "--version"]).stdout.strip()
    major = int(re.match(r"v(\d+)", v).group(1))
    if major < 20:
        fail(f"Node.js {v} — требуется 20 или новее (ограничение Docusaurus 3.10)",
             "nvm install 22 && nvm use 22 && nvm alias default 22 — затем перезапустите скрипт")
    ok(f"Node.js {v}")
    ok(f"npm {run(['npm', '--version']).stdout.strip()}")


def scaffold(target, skip):
    step(2, 7, "Эталонный сайт (официальный генератор openapi-плагина)")
    cfg = find_config(target)
    if skip or cfg:
        if not cfg:
            fail(f"--skip-scaffold, но в {target} нет docusaurus.config.*")
        ok(f"использую уже развёрнутый сайт в ./{target}")
        return
    if os.path.exists(target):
        fail(f"папка ./{target} существует, но сайта в ней нет",
             "удалите её или укажите другое имя: python3 bootstrap.py другое-имя")
    print(f"  запускаю: npx create-docusaurus-openapi-docs@latest {target}")
    print(c("2", "  (генератор может задать свои вопросы — отвечайте, это нормально)"))
    code = run(["npx", "-y", "create-docusaurus-openapi-docs@latest", target],
               interactive=True)
    if code != 0 or not find_config(target):
        fail("генератор не создал сайт",
             "проверьте доступ в интернет и повторите; лог ошибки выше — от самого генератора")
    ok(f"эталонный сайт создан в ./{target}")


def find_config(target):
    for ext in ("ts", "js", "mjs"):
        p = os.path.join(target, f"docusaurus.config.{ext}")
        if os.path.exists(p):
            return p
    return None


def personalize(defaults):
    step(3, 7, "Персонализация")
    if defaults:
        ok("режим --defaults: демо-значения PayFlow")
        return list(DEFAULTS)
    def ask(q, d):
        v = input(f"  {q} [{d or 'пропустить'}]: ").strip()
        return v or d
    return [ask("Название продукта (шапка портала)", DEFAULTS[0]),
            ask("Название компании (футер)", DEFAULTS[1]),
            ask("Публичный URL документации", DEFAULTS[2]),
            ask("Путь к вашей OpenAPI-спеке", DEFAULTS[3])]


def ask_s3(defaults):
    if defaults:
        return ["your-docs-staging", "your-docs-prod", "eu-west-1"]
    print(f"\n  {c('1', 'Деплой на S3')} (секреты AWS сюда не вводятся — только в GitLab CI/CD Variables)")
    def ask(q, d):
        v = input(f"  {q} [{d}]: ").strip()
        return v or d
    return [ask("S3-бакет staging", "your-docs-staging"),
            ask("S3-бакет production", "your-docs-prod"),
            ask("AWS-регион", "eu-west-1")]


def overlay(target, spec_path, product, company, url, s3=None):
    step(4, 7, "Наложение контента")
    # docs: демо-контент эталона заменяется нашей структурой
    dst_docs = os.path.join(target, "docs")
    if os.path.exists(dst_docs):
        shutil.rmtree(dst_docs)
    shutil.copytree(os.path.join(HERE, "docs"), dst_docs)
    # MDX 3 / Docusaurus 3.10 запрещает HTML-комментарии <!-- --> в md:
    # конвертируем в {/* */} на случай, если в docs попали файлы со старым синтаксисом
    converted = 0
    for root, _dirs, files in os.walk(dst_docs):
        for fname in files:
            if fname.endswith((".md", ".mdx")):
                p = os.path.join(root, fname)
                t = open(p, encoding="utf-8").read()
                n = re.sub(r"<!--(.*?)-->", lambda m: "{/*" + m.group(1) + "*/}",
                           t, flags=re.S)
                # плейсхолдеры в MDX — это JSX-выражения и роняют страницу:
                # подставляем ответы персонализации
                for token, value in (("{{PRODUCT_NAME}}", product),
                                     ("{{COMPANY}}", company),
                                     ("{{DOCS_URL}}", url)):
                    n = n.replace(token, value)
                if n != t:
                    open(p, "w", encoding="utf-8").write(n)
                    converted += 1
    msg = "docs/: Quickstart, Аутентификация, Сценарии, Ошибки, Changelog"
    if converted:
        msg += f" (комментарии приведены к MDX-синтаксису: {converted} файл(ов))"
    ok(msg)
    # спека
    os.makedirs(os.path.join(target, "openapi"), exist_ok=True)
    example = os.path.join(HERE, "openapi", "openapi.example.yaml")
    dst_spec = os.path.join(target, "openapi", "openapi.yaml")
    if spec_path and os.path.exists(spec_path):
        shutil.copy(spec_path, dst_spec)
        ok(f"спека: {spec_path} -> openapi/openapi.yaml")
    else:
        if spec_path:
            warn(f"спека {spec_path} не найдена — подключаю пример")
        shutil.copy(example, dst_spec)
        ok("спека: пример (openapi/openapi.yaml) — замените своей позже")
    # фирменный стиль: терминальная тема (логотип, favicon, css)
    img_dir = os.path.join(target, "static", "img")
    css_dir = os.path.join(target, "src", "css")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(css_dir, exist_ok=True)
    for f in ("logo.svg", "favicon.svg"):
        shutil.copy(os.path.join(HERE, "assets", "brand", f), img_dir)
    shutil.copy(os.path.join(HERE, "assets", "brand", "custom.css"),
                os.path.join(css_dir, "custom.css"))
    ok("бренд: логотип, favicon, терминальная тема (src/css/custom.css)")
    # линтер и CI
    shutil.copy(os.path.join(HERE, "assets", ".spectral.yaml"), target)
    gitlab_tpl = "gitlab-ci-s3.yml" if s3 else "gitlab-ci.yml"
    for src, dst in [(gitlab_tpl, ".gitlab-ci.yml"),
                     ("github-docs.yml", os.path.join(".github", "workflows", "docs.yml"))]:
        text = open(os.path.join(HERE, "assets", src)).read()
        text = text.replace("{{OPENAPI_PATH}}", "openapi/openapi.yaml")
        if s3:
            text = (text.replace("{{S3_BUCKET_STAGING}}", s3[0])
                        .replace("{{S3_BUCKET_PROD}}", s3[1])
                        .replace("{{AWS_REGION}}", s3[2]))
        dst_path = os.path.join(target, dst)
        os.makedirs(os.path.dirname(dst_path) or ".", exist_ok=True)
        open(dst_path, "w").write(text)
    ok("линтер спеки (.spectral.yaml) и CI: " + ("GitLab->S3 (staging авто, prod вручную) + GitHub Pages" if s3 else "GitLab Pages + GitHub Pages"))


def patch_config(target, product, company, url, s3=None):
    step(5, 7, "Настройка конфига эталона")
    cfg = find_config(target)
    text = open(cfg, encoding="utf-8").read()

    def sub(pattern, repl, label, count=1):
        nonlocal text
        new, n = re.subn(pattern, repl, text, count=count)
        if n:
            text = new
            ok(label)
        else:
            warn(f"{label} — не нашёл место в конфиге, поправьте руками в {os.path.basename(cfg)}")

    sub(r"(title:\s*)(['\"]).*?\2", rf"\g<1>\g<2>{product}\g<2>", f"заголовок сайта -> {product}")
    sub(r"(\n\s*url:\s*)(['\"]).*?\2", rf"\g<1>\g<2>{url}\g<2>", f"url -> {url}")
    sub(r"(organizationName:\s*)(['\"]).*?\2", rf"\g<1>\g<2>{company}\g<2>",
        f"organizationName -> {company}")
    sub(r"(specPath:\s*)(['\"]).*?\2", r"\g<1>\g<2>openapi/openapi.yaml\g<2>",
        "specPath -> openapi/openapi.yaml", count=0)
    # ссылки эталонного демо-контента могли остаться в navbar/footer — не роняем сборку
    if re.search(r"onBrokenLinks\s*:", text):
        text = re.sub(r"onBrokenLinks\s*:\s*(['\"])\w+\1", "onBrokenLinks: 'warn'", text)
    else:
        text = re.sub(r"(\n\s*baseUrl:.*?\n)", r"\1  onBrokenLinks: 'warn',\n", text, count=1)
    ok("onBrokenLinks -> warn (остаточные демо-ссылки не роняют сборку)")

    # навбар эталона ссылается на снесённый демо-док (docId: 'intro') —
    # заменяем этот пункт нашими; иначе рендер навбара падает
    navbar_items = ("{ type: 'doc', docId: 'index', position: 'left', label: 'Быстрый старт' },\n"
                    "        { type: 'doc', docId: 'scenarios/index', position: 'left', label: 'Сценарии' },\n"
                    "        { type: 'doc', docId: 'errors', position: 'left', label: 'Ошибки' },\n"
                    "        { to: '/reference', label: 'Справочник API', position: 'left' },\n"
                    "        { type: 'doc', docId: 'changelog', position: 'right', label: 'Changelog' },")
    new, n = re.subn(r"\{[^{}]*docId:\s*['\"]intro['\"][^{}]*\},?",
                     navbar_items, text, count=1)
    if n:
        text = new
        ok("навбар: демо-пункт Tutorial заменён на Quickstart/Сценарии/Ошибки/Changelog")
    else:
        warn("навбар: пункт с docId 'intro' не найден — если увидите ошибку рендера навбара, "
             "замените демо-пункты в themeConfig.navbar.items на ваши доки")

    # --- чистка демо-витрины эталона
    for junk in ("src/pages", "blog", "examples"):
        p = os.path.join(target, junk)
        if os.path.exists(p):
            shutil.rmtree(p)
    # демо-спека petstore кочует по версиям шаблона — сносим всё с этим
    # именем, где бы оно ни лежало (кроме node_modules)
    removed = 0
    for root, dirs, files in os.walk(target, topdown=True):
        dirs[:] = [d for d in dirs if d != "node_modules"]
        for name in list(dirs):
            if "petstore" in name.lower():
                shutil.rmtree(os.path.join(root, name))
                dirs.remove(name)
                removed += 1
        for name in files:
            if "petstore" in name.lower():
                os.remove(os.path.join(root, name))
                removed += 1
    ok(f"демо-витрина удалена (заглавная, блог, petstore: {removed} объект(ов))")
    # дока становится корнем сайта: заглавная = Quickstart
    if re.search(r"routeBasePath\s*:", text):
        text = re.sub(r"(routeBasePath\s*:\s*)(['\"]).*?\2", r"\g<1>\g<2>/\g<2>", text, count=1)
        ok("routeBasePath -> '/' (Quickstart вместо заглушки)")
    else:
        new, n = re.subn(r"(docs\s*:\s*\{)", r"\g<1>\n          routeBasePath: '/',", text, count=1)
        if n:
            text = new
            ok("routeBasePath: '/' добавлен (Quickstart вместо заглушки)")
        else:
            warn("не нашёл блок docs в пресете — добавьте routeBasePath: '/' руками")
    # блог выключаем
    new, n = re.subn(r"blog\s*:\s*\{(?:[^{}]|\{[^{}]*\})*\},?", "blog: false,", text, count=1)
    if n:
        text = new
        ok("blog -> false")
    elif "blog: false" not in text:
        warn("не смог выключить блог автоматически — поставьте blog: false в пресете")
    # демо-имя инстанса petstore -> api (светится в путях и крошках референса)
    # демо-пункт навбара "Petstore API" убираем ДО переименования,
    # иначе замена превратит его в бессмысленный "api API"
    text2, n = re.subn(r"\{[^{}]*label:\s*['\"][^'\"]*[Pp]etstore[^'\"]*['\"][^{}]*\},?\s*",
                       "", text)
    if n:
        text = text2
        ok(f"демо-пункт(ы) Petstore удалены из навбара: {n}")
    # страховка для уже переименованных конфигов
    text = re.sub(r"\{[^{}]*label:\s*['\"]api API['\"][^{}]*\},?\s*", "", text)
    if re.search(r"\bpetstore\b", text, flags=re.I):
        text = re.sub(r"\bpetstore\b", "api", text, flags=re.I)
        ok("все упоминания petstore в конфиге заменены на api")
    # пункт Blog в навбаре после blog:false вёл бы в 404
    text, n = re.subn(r"\{[^{}]*to:\s*['\"]/blog['\"][^{}]*\},?\s*", "", text, count=1)
    if n:
        ok("пункт Blog удалён из навбара")

    # --- бренд в конфиге: favicon, логотип, тёмная тема по умолчанию
    if re.search(r"favicon\s*:", text):
        text = re.sub(r"(favicon\s*:\s*)(['\"]).*?\2", r"\g<1>\g<2>img/favicon.svg\g<2>", text, count=1)
    else:
        text = re.sub(r"(\n\s*baseUrl:.*?\n)", r"\1  favicon: 'img/favicon.svg',\n", text, count=1)
    ok("favicon -> img/favicon.svg")
    if re.search(r"navbar\s*:\s*\{[^{}]*logo\s*:", text, flags=re.S):
        text = re.sub(r"(navbar\s*:\s*\{[^{}]*?logo\s*:\s*)\{[^{}]*\}",
                      r"\g<1>{ alt: 'logo', src: 'img/logo.svg' }", text, count=1, flags=re.S)
        ok("логотип навбара -> img/logo.svg")
    else:
        new, n = re.subn(r"(navbar\s*:\s*\{)", r"\g<1>\n      logo: { alt: 'logo', src: 'img/logo.svg' },",
                         text, count=1)
        if n:
            text = new
            ok("логотип добавлен в навбар")
        else:
            warn("не нашёл navbar — добавьте logo: { src: 'img/logo.svg' } руками")
    if re.search(r"colorMode\s*:", text):
        text = re.sub(r"(colorMode\s*:\s*\{[^{}]*?defaultMode\s*:\s*)(['\"]).*?\2",
                      r"\g<1>\g<2>dark\g<2>", text, count=1, flags=re.S)
        ok("тёмная тема — по умолчанию")
    else:
        new, n = re.subn(r"(themeConfig\s*:\s*\{)",
                         r"\g<1>\n    colorMode: { defaultMode: 'dark', respectPrefersColorScheme: false },",
                         text, count=1)
        if n:
            text = new
            ok("тёмная тема — по умолчанию")
        else:
            warn("не нашёл themeConfig — добавьте colorMode: { defaultMode: 'dark' } руками")

    # заголовок навбара -> название продукта
    text2, n = re.subn(r"(navbar\s*:\s*\{[^{]*?title:\s*)(['\"]).*?\2",
                       rf"\g<1>\g<2>{product}\g<2>", text, count=1)
    if n:
        text = text2
        ok(f"заголовок навбара -> {product}")

    # дока живёт в корне (routeBasePath '/'), а внутренние ссылки шаблона
    # (футер и пр.) указывают на /docs/... — переписываем
    text2, n = re.subn(r"(['\"])/docs/", r"\g<1>/", text)
    if n:
        text = text2
        ok(f"внутренние ссылки /docs/... переписаны на корень: {n}")

    if s3 and "trailingSlash" not in text:
        text = re.sub(r"(\n\s*baseUrl:.*?\n)", r"\g<1>  trailingSlash: true,\n", text, count=1)
        ok("trailingSlash: true (обязательно для роутинга статики на S3)")

    m = re.search(r"outputDir:\s*['\"]docs/([\w-]+)['\"]", text)
    api_dir = m.group(1) if m else "api"
    open(cfg, "w", encoding="utf-8").write(text)
    return api_dir


def write_sidebars(target, api_dir):
    sb = None
    for ext in ("ts", "js"):
        p = os.path.join(target, f"sidebars.{ext}")
        if os.path.exists(p):
            sb = p
            break
    if not sb:
        sb = os.path.join(target, "sidebars.ts")
    is_ts = sb.endswith(".ts")
    # референс подключаем "родным" каналом генератора: плагин при gen-api
    # создаёт docs/<api_dir>/sidebar.ts (группировка по тегам, бейджи методов) —
    # импортируем его, а не строим второй сайдбар autogenerated'ом
    if is_ts:
        api_import = f"import apiSidebar from './docs/{api_dir}/sidebar';"
        api_items = "apiSidebar"
        exports = "export default sidebars;"
    else:
        api_import = f"const apiSidebar = require('./docs/{api_dir}/sidebar.js');"
        api_items = "apiSidebar"
        exports = "module.exports = sidebars;"
    body = f"""// Порядок = порядок вопросов интегратора (методичка — в docs/scenarios/index.md)
// ВАЖНО: перед первой сборкой выполните `npx docusaurus gen-api-docs all` —
// импорт ниже указывает на файл, который создаёт генератор референса.
{api_import}

const sidebars = {{
  docs: [
    {{ type: 'doc', id: 'index', label: 'Быстрый старт' }},
    {{ type: 'doc', id: 'authentication', label: 'Аутентификация' }},
    {{
      type: 'category', label: 'Сценарии',
      link: {{ type: 'doc', id: 'scenarios/index' }},
      items: ['scenarios/payment-standard'],
    }},
    {{ type: 'doc', id: 'errors', label: 'Каталог ошибок' }},
    {{
      type: 'category', label: 'Справочник API',
      link: {{ type: 'generated-index', title: 'Справочник API', slug: '/reference' }},
      items: {api_items},
    }},
    {{ type: 'doc', id: 'changelog', label: 'Changelog' }},
  ],
}};

{exports}
"""
    open(sb, "w", encoding="utf-8").write(body)
    ok(f"сайдбар переписан ({os.path.basename(sb)}): референс — из сайдбара генератора "
       f"(docs/{api_dir}/sidebar)")


def patch_package(target):
    p_path = os.path.join(target, "package.json")
    p = json.load(open(p_path))
    p.setdefault("scripts", {})["lint:spec"] = \
        "spectral lint openapi/openapi.yaml --ruleset .spectral.yaml"
    p.setdefault("devDependencies", {})["@stoplight/spectral-cli"] = "^6.11.0"
    p["engines"] = {"node": ">=20.0"}
    json.dump(p, open(p_path, "w"), indent=2, ensure_ascii=False)
    ok("package.json: скрипт lint:spec, spectral, engines")


def build(target):
    step(6, 7, "Зависимости и генерация референса")
    print(c("2", "  npm install (первый раз — несколько минут)..."))
    r = run(["npm", "install"], cwd=target, interactive=True)
    if r != 0:
        fail("npm install завершился с ошибкой — лог выше")
    ok("зависимости установлены")
    # профилактика дублей @docusaurus/* (две копии theme-common ломают
    # React-контексты: "Hook useDoc is called outside the <DocProvider>")
    run(["npm", "dedupe"], cwd=target)
    ok("дерево зависимостей дедуплицировано")
    r = run(["npx", "docusaurus", "gen-api-docs", "all"], cwd=target)
    if isinstance(r, int) or r.returncode != 0:
        out = "" if isinstance(r, int) else (r.stderr or r.stdout)
        warn("генерация референса не удалась; проверьте спеку: npm run lint:spec")
        if out:
            print(c("2", "  " + out.strip().splitlines()[-1]))
    else:
        ok("референс сгенерирован из openapi/openapi.yaml")


def finish(target, no_start):
    step(7, 7, "Готово")
    print(f"""
  Портал: ./{target}
  Дальше:
    cd {target}
    npm start            # предпросмотр на http://localhost:3000
    npm run lint:spec    # линтинг вашей спеки
    git init && git add -A && git commit -m 'docs portal'
      (закоммитьте и package-lock.json — это фиксирует проверенные версии)
""")
    if not no_start:
        print(c("2", "  Запускаю предпросмотр (Ctrl+C для остановки)...\n"))
        run(["npm", "start"], cwd=target, interactive=True)


def main():
    args = [a for a in sys.argv[1:]]
    flags = {a for a in args if a.startswith("--")}
    names = [a for a in args if not a.startswith("--")]
    target = names[0] if names else "api-docs"

    print(c("1", "\n  Документация для API-first финтеха — установка в один клик"))
    print(c("2", "  эталон: официальный генератор openapi-плагина + авторский контент-пак\n"))

    preflight()
    scaffold(target, "--skip-scaffold" in flags)
    deploy_s3 = any(f in flags for f in ("--deploy=s3", "--s3"))
    product, company, url, spec = personalize("--defaults" in flags)
    s3 = ask_s3("--defaults" in flags) if deploy_s3 else None
    overlay(target, spec, product, company, url, s3)
    api_dir = patch_config(target, product, company, url, s3)
    write_sidebars(target, api_dir)
    patch_package(target)
    build(target)
    finish(target, "--no-start" in flags)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nПрервано.")
