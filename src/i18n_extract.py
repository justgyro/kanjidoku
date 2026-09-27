"""Pull the English out of the markup.

Until now the English lived in the page itself and the browser cached it on
load. That works while there is one document. Once Spanish, Italian and
Japanese are prerendered as documents of their own, the cache would hold
whichever language shipped, and a key missing from a translation would fall
back to Spanish rather than English.

So the English becomes a table like the other three. This walks the markup,
finds every element carrying data-i18n, and returns {key: inner HTML}.
"""
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"}


class _Collector(HTMLParser):
    """Records the inner HTML of every data-i18n element, nesting and all."""

    def __init__(self, src):
        super().__init__(convert_charrefs=False)
        self.src = src
        self.found = {}
        self.stack = []      # open tags, innermost last
        self.watching = []   # (key, tag_name, depth_at_open, start_offset)

    # -- offsets ----------------------------------------------------------
    def _offset(self):
        line, col = self.getpos()
        return self.line_starts[line - 1] + col

    def feed(self, data):
        self.line_starts = [0]
        for i, ch in enumerate(data):
            if ch == "\n":
                self.line_starts.append(i + 1)
        super().feed(data)

    # -- tags -------------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        self.stack.append(tag)
        key = dict(attrs).get("data-i18n")
        if key is not None:
            end = self.src.index(">", self._offset()) + 1
            self.watching.append((key, tag, len(self.stack), end))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in VOID or not self.stack:
            return
        depth = len(self.stack)
        self.stack.pop()
        while self.watching and self.watching[-1][2] == depth + 1:
            self.watching.pop()  # unbalanced; drop it rather than guess
        if self.watching and self.watching[-1][1] == tag and self.watching[-1][2] == depth:
            key, _, _, start = self.watching.pop()
            self.found[key] = self.src[start:self._offset()]


def extract(markup):
    c = _Collector(markup)
    c.feed(markup)
    c.close()
    return c.found


if __name__ == "__main__":
    import io, sys, json
    t = io.open(sys.argv[1], encoding="utf-8").read()
    body = t.split("</style>", 1)[1].split("<script>", 1)[0]
    got = extract(body)
    print(json.dumps(got, ensure_ascii=False, indent=1))
    print(len(got), "keys", file=sys.stderr)
