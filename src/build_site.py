"""Build the whole kanjidoku.net site from the two page sources.

    python3 build_site.py            ->  ../docs/

Output tree, which is what GitHub Pages serves:

    index.html          English
    es/ it/ ja/         the same page, prerendered
    strokes/            the stroke-order page at the URL printed in the books
    strokes/*.pdf       the five supplements
    samples/*.pdf       the five samplers
    img/*.webp          shared by every page
    og/*.png            link-preview cards
    CNAME 404.html robots.txt sitemap.xml

Two things differ from the Claude-artifact build this replaces. Images are
files rather than data URIs, because a real server can cache them and the
artifact CSP no longer applies. And each language is a document of its own,
with its language in the markup, so a crawler and a shared link both get the
language they asked for.
"""
import io
import json
import os
import re
import shutil

from PIL import Image

from i18n_extract import extract

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "docs")
DOMAIN = "kanjidoku.net"
ORIGIN = "https://" + DOMAIN

LANGS = ["en", "es", "it", "ja"]
PATH = {"en": "/", "es": "/es/", "it": "/it/", "ja": "/ja/"}

# Page-level copy. Not element copy, so it lives here rather than in the
# markup: a title and a description have no element to hang off.
META = {
    "en": {
        "title": "Kanjidoku — sudoku that leaves you with a word",
        "desc": "Sudoku played with kanji. Fill the grid, read the shaded "
                "cells in order, and they spell a real Japanese word. Four "
                "JLPT levels and Kanadoku, with free sample puzzles and "
                "stroke-order references.",
        "og_alt": "A Kanjidoku grid with three shaded cells spelling 日本語.",
    },
    "es": {
        "title": "Kanjidoku — sudoku que te deja una palabra",
        "desc": "Sudoku jugado con kanji. Completa la cuadrícula, lee las "
                "casillas sombreadas en orden y deletrean una palabra "
                "japonesa real. Cuatro niveles JLPT y Kanadoku, con puzles "
                "de muestra gratis y guías de orden de trazos.",
        "og_alt": "Una cuadrícula de Kanjidoku con tres casillas sombreadas que deletrean 日本語.",
    },
    "it": {
        "title": "Kanjidoku — sudoku che ti lascia una parola",
        "desc": "Sudoku giocato con i kanji. Completa lo schema, leggi le "
                "caselle ombreggiate in ordine e compongono una vera parola "
                "giapponese. Quattro livelli JLPT e Kanadoku, con schemi di "
                "prova gratis e guide all'ordine dei tratti.",
        "og_alt": "Uno schema Kanjidoku con tre caselle ombreggiate che compongono 日本語.",
    },
    "ja": {
        "title": "Kanjidoku — 解いたあとに、言葉が残る数独",
        "desc": "漢字で解く数独。盤面を埋め、網かけのマスを番号順に読むと、"
                "実在する日本語の言葉になります。JLPTの四つのレベルと Kanadoku。"
                "無料の見本と筆順の資料もあります。",
        "og_alt": "三つの網かけマスが日本語を綴る Kanjidoku の盤面。",
    },
}

STROKES_META = {
    "title": "Stroke order — Kanjidoku",
    "desc": "Free stroke-order references for every character in the "
            "Kanjidoku books, and every kana in Kanadoku. One PDF per "
            "volume, 8.5 x 11, free to print and to share.",
    "og_alt": "Three characters drawn large with every stroke numbered.",
}

LABEL = {"en": "EN", "es": "ES", "it": "IT", "ja": "日本語"}
NAME = {"en": "English", "es": "Español", "it": "Italiano", "ja": "日本語"}
OG_LOCALE = {"en": "en_US", "es": "es_ES", "it": "it_IT", "ja": "ja_JP"}

IMG = {
    "__HERO_V1__": "hero-v1.webp",
    "__COVER_V1__": "cover-v1.webp",
    "__COVER_V2__": "cover-v2.webp",
    "__COVER_V3__": "cover-v3.webp",
    "__COVER_V4__": "cover-v4.webp",
    "__COVER_V5__": "cover-v5.webp",
    "__PAGE_PUZZLE__": "page-puzzle.webp",
    "__PAGE_SOL__": "page-solutions.webp",
    "__PAGE_INDEX__": "page-index.webp",
    "__PAGE_PRACTICE__": "page-practice.webp",
    "__ROW_THREE__": "row-three.webp",
    "__WORKED__": "strokes-worked.webp",
    "__BODYPAGE__": "strokes-page.webp",
}
# the one image above the fold, which must not be lazy
EAGER = {"__HERO_V1__"}

SAMPLERS = {
    "vol1": "kanjidoku-vol1-N5.N4-sampler.pdf",
    "n3": "kanjidoku-vol2-N3-sampler.pdf",
    "n2": "kanjidoku-vol3-N2-sampler.pdf",
    "n1": "kanjidoku-vol4-N1-sampler.pdf",
    "kana": "kanadoku-sampler.pdf",
}
SUPPLEMENTS = [
    "kanjidoku-vol1-N5.N4-strokes.pdf",
    "kanjidoku-vol2-N3-strokes.pdf",
    "kanjidoku-vol3-N2-strokes.pdf",
    "kanjidoku-vol4-N1-strokes.pdf",
    "kanadoku-strokes.pdf",
]


# ---------------------------------------------------------------- helpers
def read(p):
    return io.open(os.path.join(HERE, p), encoding="utf-8").read()


def write(rel, text):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8").write(text)
    return p


def once(text, old, new, what):
    n = text.count(old)
    if n != 1:
        raise SystemExit("%s: expected 1 match, found %d\n  %r" % (what, n, old[:90]))
    return text.replace(old, new)


def size(name):
    with Image.open(os.path.join(HERE, "img", name)) as im:
        return im.size


def images(markup):
    """Data-URI tokens become real files, with dimensions so nothing reflows."""
    for token, name in IMG.items():
        if token not in markup:
            continue
        w, h = size(name)
        extra = "" if token in EAGER else ' loading="lazy" decoding="async"'
        markup = re.sub(
            r'<img([^>]*?)src="%s"' % re.escape(token),
            lambda m: '<img%ssrc="/img/%s" width="%d" height="%d"%s'
                      % (m.group(1), name, w, h, extra),
            markup,
        )
    return markup


def cut(text, start, end, what):
    """Remove a block of script, from `start` up to `end` (or to the end)."""
    i = text.index(start)
    j = len(text) if end is None else text.index(end, i)
    if i < 0:
        raise SystemExit("%s: not found" % what)
    return text[:i] + text[j:]


def config(script, name):
    """Read a config object literal out of the page script."""
    i = script.index("const %s = {" % name)
    body = script[script.index("{", i) + 1:script.index("};", i)]
    out = {}
    for m in re.finditer(r'(\w+)\s*:\s*"([^"]*)"', body):
        out[m.group(1)] = m.group(2)
    return out


def buttons(body, script):
    """Write the Buy and sample controls into the markup.

    They used to be built by JS from the AMAZON and SAMPLES tables. That
    left a visitor without JavaScript, and any crawler that does not run
    it, looking at a page with no way to buy anything. The tables are
    known at build time, so the anchors belong in the HTML.
    """
    amazon = config(script, "AMAZON")

    for key in ("vol1", "n3", "n2", "n1", "kana"):
        url = (amazon.get(key) or "").strip()
        if url:
            buy = ('<a class="btn" href="%s" target="_blank" rel="noopener" '
                   'data-i18n="btn.buy">Buy on Amazon</a>' % url)
        else:
            buy = ('<span class="pending" data-i18n="btn.soon"><i></i> '
                   "Coming to Amazon</span>")
        pdf = SAMPLERS.get(key)
        if pdf:
            dl = ('<a class="btn ghost" href="/samples/%s" data-i18n="btn.sample">'
                  "Free sample puzzles</a>" % pdf)
        else:
            dl = '<span class="pending" data-i18n="btn.coming"><i></i> Coming</span>'
        body = once(body, '<div class="actions" data-book="%s"></div>' % key,
                    '<div class="actions" data-book="%s">%s %s</div>' % (key, buy, dl),
                    "actions " + key)

    # the sampler cards lower down: a button that JS upgraded becomes a link
    def to_link(m):
        key, pdf = m.group("key"), SAMPLERS.get(m.group("key"))
        if not pdf:
            return ('<span class="pending" data-i18n="btn.coming"><i></i> Coming</span>')
        return ('<a class="btn ghost" href="/samples/%s" data-i18n="btn.dl">'
                "Download PDF</a>" % pdf)

    body, n = re.subn(
        r'<button class="btn ghost dl"[^>]*data-key="(?P<key>\w+)"[^>]*>.*?</button>',
        to_link, body)
    if n != 5:
        raise SystemExit("sampler cards: rewrote %d, expected 5" % n)
    return body


def head(lang, title, desc, url, og_image, og_alt, alternates=True):
    ln = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>%s</title>" % title,
        '<meta name="description" content="%s">' % desc,
        '<link rel="canonical" href="%s">' % url,
    ]
    if alternates:
        for code in LANGS:
            ln.append('<link rel="alternate" hreflang="%s" href="%s%s">'
                      % (code, ORIGIN, PATH[code]))
        ln.append('<link rel="alternate" hreflang="x-default" href="%s/">' % ORIGIN)
    ln += [
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="Kanjidoku">',
        '<meta property="og:locale" content="%s">' % OG_LOCALE.get(lang, "en_US"),
        '<meta property="og:title" content="%s">' % title,
        '<meta property="og:description" content="%s">' % desc,
        '<meta property="og:url" content="%s">' % url,
        '<meta property="og:image" content="%s%s">' % (ORIGIN, og_image),
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta property="og:image:alt" content="%s">' % og_alt,
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="theme-color" content="#fcfbf8" media="(prefers-color-scheme: light)">',
        '<meta name="theme-color" content="#141519" media="(prefers-color-scheme: dark)">',
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        'family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400'
        '&family=Zen+Kaku+Gothic+New:wght@400;500;700;900&display=swap">',
    ]
    return "\n".join(ln)


def document(lang, head_html, css, body, script):
    return (
        "<!doctype html>\n"
        '<html lang="%s" data-lang="%s">\n<head>\n%s\n<style>\n%s\n</style>\n</head>\n'
        "<body>\n%s\n<script>\n%s\n</script>\n</body>\n</html>\n"
        % (lang, lang, head_html, css.strip(), body.strip(), script.strip())
    )


# ---------------------------------------------------------------- the main page
def build_main():
    src = read("template.html")
    css = src.split("<style>", 1)[1].split("</style>", 1)[0]
    body = src.split("</style>", 1)[1].split("<script>", 1)[0]
    script = src.split("<script>", 1)[1].rsplit("</script>", 1)[0]

    en = extract(body)
    print("  english keys lifted out of the markup:", len(en))

    # ---- the switcher stops being three buttons built by JS and becomes
    # ---- four links, so a crawler and a no-JS visitor both follow them
    nav = ['<nav class="langs" id="langs" aria-label="Language">']
    for code in LANGS:
        nav.append('  <a href="%s" data-lang="%s" hreflang="%s" title="%s">%s</a>'
                   % (PATH[code], code, code, NAME[code], LABEL[code]))
    nav.append("</nav>")
    body = once(body,
                '<nav class="langs" id="langs" aria-label="Language"></nav>',
                "\n".join(nav), "language nav")

    css = once(css, ".langs button{", ".langs a,\n.langs button{", "switcher css")
    css = once(css, ".langs button:hover{color:var(--ink)}",
               ".langs a{text-decoration:none}\n.langs a:hover,\n.langs button:hover{color:var(--ink)}",
               "switcher hover")
    css = once(css, '.langs button[aria-pressed="true"]',
               '.langs a[aria-pressed="true"],\n.langs button[aria-pressed="true"]',
               "switcher pressed")
    css = once(css, ".langs button:focus-visible{",
               ".langs a:focus-visible,\n.langs button:focus-visible{",
               "switcher focus")

    body = images(body)
    body = buttons(body, script)

    # ---- the download plumbing all goes: the PDFs are files on this domain,
    # ---- so the buttons are plain links written into the markup above
    script = cut(script, "function sampleUrl(key)",
                 "/* ---- language ---- */", "download plumbing")
    script = cut(script, "/* ---- downloads ------", None, "downloads block")
    for dead in ("  if (typeof refreshDownloadLabels === \"function\") refreshDownloadLabels();\n",):
        script = once(script, dead, "", "dead call")
    body = once(body, '    <p class="dlnote" id="dlnote"></p>\n', "", "dlnote")

    script = re.sub(r'const STROKES = "[^"]*";',
                    'const STROKES = "/strokes/";', script, count=1)

    # ---- the English table, and a fallback that no longer depends on which
    # ---- language the document happened to ship in
    script = once(script, "const STRINGS = {", "const EN_MARKUP = %s;\n\nconst STRINGS = {"
                  % json.dumps(en, ensure_ascii=False, indent=2), "EN_MARKUP")
    # the merge has to come after STRINGS is declared, not before
    script = once(script, "function t(key) {",
                  "Object.assign(STRINGS.en, EN_MARKUP);\n\nfunction t(key) {", "merge en")
    script = once(script, "let lang = \"en\";",
                  'let lang = document.documentElement.getAttribute("data-lang") || "en";',
                  "initial lang")
    script = once(script,
                  "    el.innerHTML = value != null ? value : original.get(el);",
                  "    el.innerHTML = value != null ? value\n"
                  "      : (STRINGS.en[key] != null ? STRINGS.en[key] : original.get(el));",
                  "fallback")

    # ---- switching stays instant, but the address bar keeps up with it
    script = once(script,
                  '  document.querySelectorAll("#langs button").forEach(function (b) {\n'
                  '    b.setAttribute("aria-pressed", String(b.dataset.lang === lang));\n'
                  '  });',
                  '  document.querySelectorAll("#langs [data-lang]").forEach(function (b) {\n'
                  '    b.setAttribute("aria-pressed", String(b.dataset.lang === lang));\n'
                  '  });',
                  "aria-pressed")

    old_nav_js = script[script.index("const langNav = document.getElementById(\"langs\");"):
                        script.index("})();", script.index("const langNav")) + 5]
    new_nav_js = '''const PATHS = %s;

/* The links are real: without JS they navigate, and a crawler follows them.
   With JS they swap the text in place and push the sibling URL, so the
   address bar and the language on screen never disagree. */
document.querySelectorAll("#langs a[data-lang]").forEach(function (a) {
  a.addEventListener("click", function (e) {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
    e.preventDefault();
    const code = a.dataset.lang;
    applyLang(code);
    try { history.pushState({ lang: code }, "", PATHS[code]); } catch (err) {}
  });
});

window.addEventListener("popstate", function () {
  const here = location.pathname.replace(/\\/+$/, "/") || "/";
  let code = "en";
  Object.keys(PATHS).forEach(function (k) { if (PATHS[k] === here) code = k; });
  applyLang(code);
});

applyLang(document.documentElement.getAttribute("data-lang") || "en");''' % json.dumps(PATH, indent=2)
    script = once(script, old_nav_js, new_nav_js, "switcher js")

    for lang in LANGS:
        m = META[lang]
        url = ORIGIN + PATH[lang]
        doc = document(
            lang,
            head(lang, m["title"], m["desc"], url, "/og/card-%s.png" % lang, m["og_alt"]),
            css, localise(body, lang, en, src), script)
        rel = "index.html" if lang == "en" else lang + "/index.html"
        write(rel, doc)
        print("  %-16s %6.1f KB" % (rel, len(doc.encode()) / 1024))


def localise(body, lang, en, src):
    """Swap the markup into one language, so the document ships ready."""
    if lang == "en":
        return body
    table = json.loads(table_json(src, lang))
    out = body
    for key, value in table.items():
        if key not in en:
            continue
        pat = re.compile(r'(<([a-z0-9]+)[^>]*\bdata-i18n="%s"[^>]*>)(.*?)(</\2>)'
                         % re.escape(key), re.S)
        out, n = pat.subn(lambda m: m.group(1) + value + m.group(4), out, count=1)
    return out


def table_json(src, lang):
    """The es / it / ja tables are JS object literals that are already valid JSON."""
    start = src.index('\n  %s: {' % lang)
    end = src.index("\n  }", start) + 4
    block = src[start:end].split("{", 1)[1].rsplit("}", 1)[0]
    return "{" + block.rstrip().rstrip(",") + "}"


def page_count(path, declared):
    """How many pages the PDF really has.

    Preferred over the number typed into strokes-body.html, so the page
    cannot claim a count the file does not have. Both readers are optional,
    though: without either the build still runs and falls back to the
    declared value, loudly, rather than failing.
    """
    try:
        import pymupdf
        return len(pymupdf.open(path)), True
    except ImportError:
        pass
    try:
        from pypdf import PdfReader
        return len(PdfReader(path).pages), True
    except ImportError:
        pass
    return declared, False


def supplement_rows(script):
    """Write the download list into the markup, with pages and size taken
    from the PDFs themselves."""
    block = script[script.index("const SUPPLEMENTS = ["):script.index("\n];")]
    rows = []
    warned = False
    for obj in re.finditer(r"\{(.*?)\}", block, re.S):
        f = dict(re.findall(r'(\w+):\s*"((?:[^"\\]|\\.)*)"', obj.group(1)))
        name = f.get("file", "")
        if not name:
            continue
        path = os.path.join(HERE, "pdf", name)
        declared = int(re.search(r"pages:\s*(\d+)", obj.group(1)).group(1))
        pages, measured = page_count(path, declared)
        if not measured:
            if not warned:
                print("  ! page counts not verified (install pymupdf or pypdf); "
                      "using the numbers written in strokes-body.html")
                warned = True
        elif pages != declared:
            print("  ! %s: strokes-body.html says %d pages, the file has %d "
                  "— using %d" % (name, declared, pages, pages))
        mb = os.path.getsize(path) / 1048576
        rows.append(
            '  <div class="file">\n'
            '    <div class="who">\n'
            '      <span class="lv"><i style="background:%s"></i> %s · %s</span>\n'
            "      <h3>%s characters</h3>\n"
            '      <p class="meta">%d pages · 8.5 × 11</p>\n'
            '      <p class="note">%s</p>\n'
            "    </div>\n"
            '    <div class="size">%.1f MB</div>\n'
            '    <a class="btn" href="/strokes/%s" data-file="%s">Download PDF</a>\n'
            "  </div>"
            % (f["colour"], f["volume"], f["level"],
               re.search(r"chars:\s*(\d+)", obj.group(1)).group(1),
               pages, f["note"], mb, name, name))
    if len(rows) != 5:
        raise SystemExit("supplements: built %d rows, expected 5" % len(rows))
    return '<div class="files" id="files">\n' + "\n".join(rows) + "\n</div>"


# ---------------------------------------------------------------- the stroke page
def build_strokes():
    src = read("template.html")
    css = src.split("<style>", 1)[1].split("</style>", 1)[0]
    body = read("strokes-body.html")

    # the stroke page lifts the core of the main stylesheet rather than
    # copying it, so the two cannot drift apart
    cut = css.index("/* ---------- hero ---------- */")
    core = css[:cut]
    marks = [m.start() for m in re.finditer(r"^/\* -{6,}", css, re.M)] + [len(css)]

    def section(name):
        s = css.index(name)
        return css[s:next(m for m in marks if m > s + 10)]

    for marker in ("/* ---------- books ---------- */",
                   "/* ---------- proof ---------- */",
                   "/* ---------- language ---------- */"):
        core += section(marker)

    page_css = body.split("<style>", 1)[1].split("</style>", 1)[0]
    page_css = page_css.replace("__CORE_CSS__", core.rstrip())
    markup = body.split("</style>", 1)[1].split("<script>", 1)[0]
    script = body.split("<script>", 1)[1].rsplit("</script>", 1)[0]

    markup = images(markup)
    markup = once(markup, '<div class="files" id="files"></div>',
                  supplement_rows(script), "supplement rows")
    # the rows are markup now, so the script is just the back link
    script = ('/* Where the main site lives. */\nconst HOME = "/";\n\n'
              'const home = document.getElementById("home");\n'
              'if (HOME) home.href = HOME; else home.remove();')

    doc = document("en",
                   head("en", STROKES_META["title"], STROKES_META["desc"],
                        ORIGIN + "/strokes/", "/og/card-strokes.png",
                        STROKES_META["og_alt"], alternates=False),
                   page_css, markup, script)
    write("strokes/index.html", doc)
    print("  %-16s %6.1f KB" % ("strokes/", len(doc.encode()) / 1024))


# ---------------------------------------------------------------- the rest
def build_extras():
    write("CNAME", DOMAIN + "\n")
    # Pages runs Jekyll unless told not to, which would swallow any path
    # beginning with an underscore. Nothing here starts with one, but the
    # flag costs a byte and removes a whole class of surprise.
    write(".nojekyll", "")
    write("robots.txt", "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % ORIGIN)

    urls = []
    for lang in LANGS:
        alts = "".join(
            '\n    <xhtml:link rel="alternate" hreflang="%s" href="%s%s"/>'
            % (c, ORIGIN, PATH[c]) for c in LANGS)
        alts += ('\n    <xhtml:link rel="alternate" hreflang="x-default" href="%s/"/>'
                 % ORIGIN)
        urls.append("  <url>\n    <loc>%s%s</loc>%s\n  </url>" % (ORIGIN, PATH[lang], alts))
    urls.append("  <url>\n    <loc>%s/strokes/</loc>\n  </url>" % ORIGIN)
    write("sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
          '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
          + "\n".join(urls) + "\n</urlset>\n")

    css = read("template.html").split("<style>", 1)[1].split("</style>", 1)[0]
    core = css[:css.index("/* ---------- hero ---------- */")]
    write("404.html", document(
        "en",
        head("en", "Not here — Kanjidoku",
             "That page does not exist on kanjidoku.net.",
             ORIGIN + "/404.html", "/og/card-en.png",
             META["en"]["og_alt"], alternates=False),
        core,
        '<div class="wrap">\n  <header class="masthead">\n'
        '    <div class="topbar"><div class="imprint"><span class="dot"></span> Mind Quests</div></div>\n'
        '    <div><h1>Not here</h1>\n'
        '    <p class="strap">That page does not exist.</p></div>\n'
        "  </header>\n"
        '  <section><p class="measure">Try <a class="inline" href="/">the books</a>, '
        'or <a class="inline" href="/strokes/">the stroke-order downloads</a>.</p></section>\n'
        "</div>", "/* nothing to run */"))

    for folder, names in (("samples", SAMPLERS.values()), ("strokes", SUPPLEMENTS)):
        os.makedirs(os.path.join(OUT, folder), exist_ok=True)
        for name in names:
            shutil.copy2(os.path.join(HERE, "pdf", name),
                         os.path.join(OUT, folder, name))

    shutil.copytree(os.path.join(HERE, "img"), os.path.join(OUT, "img"),
                    dirs_exist_ok=True)

    cards = os.path.join(HERE, "og")
    if os.path.isdir(cards):
        shutil.copytree(cards, os.path.join(OUT, "og"), dirs_exist_ok=True)
    else:
        print("  ! no src/og: run build_og.py, or link previews will 404")


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    print("main page:")
    build_main()
    print("stroke page:")
    build_strokes()
    build_extras()
    total = sum(os.path.getsize(os.path.join(r, f))
                for r, _, fs in os.walk(OUT) for f in fs)
    print("site: %.1f MB over %d files"
          % (total / 1048576, sum(len(fs) for _, _, fs in os.walk(OUT))))


if __name__ == "__main__":
    main()
