# kanjidoku.net

The buyer-facing site for the Kanjidoku books, plus the stroke-order
downloads at the URL printed inside them.

`src/` is the source. `docs/` is the built site, and is what GitHub Pages
serves. **Everything in `docs/` is generated** — edit the source and
rebuild, never the output.

## Building

    cd src
    python3 build_site.py      # the pages, the PDFs, CNAME, sitemap
    python3 build_og.py        # the link-preview cards (needs Playwright)

`build_og.py` only needs re-running if the cards change; the PNGs it makes
are committed.

Requirements: Python 3 with `pillow` and `pymupdf`, and for the cards,
`playwright` with Chromium.

## What comes out

| | |
|---|---|
| `index.html` | English |
| `es/` `it/` `ja/` | the same page, prerendered in each language |
| `strokes/` | the stroke-order page, **at the URL printed in the books** |
| `strokes/*.pdf` | the five supplements |
| `samples/*.pdf` | the five samplers |
| `img/` `og/` | shared images and the link-preview cards |
| `CNAME` `.nojekyll` `404.html` `robots.txt` `sitemap.xml` | |

## Turning it on

1. Push this repo to GitHub. The name does not matter: a custom domain
   serves from the root of the domain, so there is no `/repo-name/`
   prefix to worry about and no need for a `<username>.github.io` repo.
2. Settings, Pages: deploy from a branch, `main`, folder `/docs`.
3. Settings, Pages, custom domain: `kanjidoku.net`.
4. At the registrar, for the apex:

       A     185.199.108.153
       A     185.199.109.153
       A     185.199.110.153
       A     185.199.111.153
       AAAA  2606:50c0:8000::153
       AAAA  2606:50c0:8001::153
       AAAA  2606:50c0:8002::153
       AAAA  2606:50c0:8003::153

   and `CNAME www -> <username>.github.io`. An ALIAS or ANAME at the apex
   is tidier if the registrar supports one.
5. Wait for the certificate, then turn on **Enforce HTTPS**.

## Things that will bite

**`/strokes` can never move.** Every built stroke supplement prints
`KANJIDOKU.NET/STROKES` in its running header, and a book already sold
cannot be corrected. That is why the page is `strokes/index.html` rather
than `strokes.html`.

**`CNAME` is generated.** `build_site.py` writes it, because the build
clears `docs/` first and GitHub's own copy would be deleted on the next
rebuild, silently dropping the custom domain.

**Copy changes are four-way.** The English lives in the markup of
`src/template.html`; Spanish, Italian and Japanese live in the `STRINGS`
tables in the same file. A key edited in the markup and not in the
tables keeps showing the old sentence in the other three languages,
because the fallback only catches a *missing* key, never a stale one.

**Page counts and file sizes on the stroke page are read off the PDFs**
at build time rather than typed in, so they cannot drift. The character
counts still come from `strokes-body.html` and still can.

**Amazon links cannot be checked from a script**, since `amazon.com`
disallows robots. Read the five ASINs back before publishing: a wrong one
sends a buyer to a different volume and nothing here will catch it.

## Layout

    src/
      build_site.py      builds everything
      build_og.py        the 1200x630 link-preview cards
      i18n_extract.py    lifts the English out of the markup into a table
      template.html      the main page: markup, styles, the four STRINGS tables
      strokes-body.html  the stroke page
      img/  pdf/         sources for the assets
    docs/                generated; served by Pages
