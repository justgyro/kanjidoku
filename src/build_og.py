"""Render the link-preview cards.

Pasting kanjidoku.net into a chat is the whole point of the site, so the
card is the first thing most people will see of it. Five 1200x630 PNGs,
one per language and one for the stroke page, drawn with the site's own
type and colours rather than mocked up.
"""
import asyncio
import io
import os
import sys

from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "docs", "og")

STRAP = {
    "en": "Sudoku that leaves you with a word",
    "es": "Sudoku que te deja una palabra",
    "it": "Sudoku che ti lascia una parola",
    "ja": "解いたあとに、言葉が残る数独",
}
FOOT = {
    "en": "Five books · JLPT N5 to N1 · free sample puzzles",
    "es": "Cinco libros · JLPT N5 a N1 · puzles de muestra gratis",
    "it": "Cinque libri · JLPT N5 a N1 · schemi di prova gratis",
    "ja": "全五冊 · JLPT N5〜N1 · 無料の見本",
}

CARD = """<!doctype html><html><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;1,8..60,400&family=Zen+Kaku+Gothic+New:wght@500;700;900&display=swap">
<style>
*{box-sizing:border-box;margin:0}
body{width:1200px;height:630px;background:#fcfbf8;color:#111;
  font-family:"Zen Kaku Gothic New",system-ui,sans-serif;
  display:grid;grid-template-columns:1fr 430px;align-items:center;gap:56px;padding:64px 72px;overflow:hidden}
.imprint{font-size:17px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:#77746b;
  display:flex;align-items:baseline;gap:12px}
.imprint i{width:9px;height:9px;border-radius:50%;background:#fa9716;display:inline-block;font-style:normal;transform:translateY(-2px)}
h1{font-size:104px;font-weight:900;letter-spacing:-.025em;line-height:1;margin:26px 0 0}
p.strap{font-family:"Source Serif 4",Georgia,serif;font-size:35px;font-style:italic;color:#4a4842;margin:22px 0 0;line-height:1.25}
.ladder{display:flex;gap:7px;margin-top:38px}
.ladder span{height:9px;width:76px;border-radius:3px}
p.foot{font-size:20px;font-weight:500;letter-spacing:.04em;color:#77746b;margin:30px 0 0}
.art{position:relative}
.art img{display:block;width:100%;height:auto;border:1px solid #dedbd3;box-shadow:0 1px 2px rgba(17,17,17,.05),0 18px 44px -20px rgba(17,17,17,.42)}
body.ja h1{letter-spacing:0}
body.ja p.strap{font-family:"Zen Kaku Gothic New",sans-serif;font-style:normal;font-size:32px}
body.wide{grid-template-columns:1fr 470px}
</style></head><body class="__CLS__">
<div>
  <div class="imprint"><i></i> Mind Quests</div>
  <h1>__TITLE__</h1>
  <p class="strap">__STRAP__</p>
  <div class="ladder">
    <span style="background:#3573bc"></span><span style="background:#45a099"></span>
    <span style="background:#88c029"></span><span style="background:#fa9716"></span>
    <span style="background:#eb2b92"></span><span style="background:#9d4bd7"></span>
  </div>
  <p class="foot">__FOOT__</p>
</div>
<div class="art"><img src="__ART__"></div>
</body></html>"""


def card(cls, title, strap, foot, art):
    return (CARD.replace("__CLS__", cls).replace("__TITLE__", title)
            .replace("__STRAP__", strap).replace("__FOOT__", foot)
            .replace("__ART__", art))


async def main():
    os.makedirs(OUT, exist_ok=True)
    jobs = []
    for lang, strap in STRAP.items():
        jobs.append(("card-%s.png" % lang,
                     card("ja" if lang == "ja" else "", "Kanjidoku", strap,
                          FOOT[lang], "file://" + os.path.join(HERE, "img", "cover-v1.webp"))))
    jobs.append(("card-strokes.png",
                 card("wide", "Stroke order",
                      "Every character in the book, big enough to read",
                      "Free · one PDF per volume · 8.5 × 11",
                      "file://" + os.path.join(HERE, "img", "row-three.webp"))))

    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        page = await b.new_page(viewport={"width": 1200, "height": 630},
                                device_scale_factor=1)
        for name, html in jobs:
            path = os.path.join(HERE, "_card.html")
            io.open(path, "w", encoding="utf-8").write(html)
            await page.goto("file://" + path)
            await page.wait_for_timeout(700)
            await page.screenshot(path=os.path.join(OUT, name))
            print("  og/%-18s %5.1f KB" % (name, os.path.getsize(os.path.join(OUT, name)) / 1024))
        os.remove(os.path.join(HERE, "_card.html"))
        await b.close()


if __name__ == "__main__":
    asyncio.run(main())
