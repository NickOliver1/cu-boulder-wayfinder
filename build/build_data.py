"""Pull CU Boulder campus map data (Concept3D map 336) and write a compact data.json."""
import json, re, html, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = "0001085cc708b9cef47080f064612ca5"
API = "https://api.concept3d.com"
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "data.json")

# Download the raw map data on first run (about 9 MB; not kept in the repository).
for name in ("categories", "locations"):
    path = os.path.join(HERE, name + ".json")
    if not os.path.exists(path):
        print("downloading", name, file=sys.stderr)
        urllib.request.urlretrieve(f"{API}/{name}?map=336&key={KEY}", path)

cats = json.load(open(os.path.join(HERE, "categories.json"), encoding="utf-8"))
locs = json.load(open(os.path.join(HERE, "locations.json"), encoding="utf-8"))

SKIP_ROOTS = {"Room Details"}
SKIP_NAMES = {"Building Labels"}
FLATTEN = {"All Gender Bathrooms"}  # merge per-building subcategories into one list

by_id = {c["catId"]: c for c in cats}
children = {}
for c in cats:
    children.setdefault(c["parent"], []).append(c)

keep = {}      # catId -> output category id
out_cats = []  # {id, name, parent, weight}

def walk(parent, out_parent, flatten_to=None):
    for c in sorted(children.get(parent, []), key=lambda c: c["weight"]):
        if c["hidden"] or c["private"] or c["restricted"]:
            continue
        if c["name"] in SKIP_NAMES or (parent == 0 and c["name"] in SKIP_ROOTS):
            continue
        if flatten_to is not None:
            keep[c["catId"]] = flatten_to
            walk(c["catId"], None, flatten_to)
            continue
        keep[c["catId"]] = c["catId"]
        out_cats.append({"id": c["catId"], "name": c["name"].strip(), "parent": out_parent})
        walk(c["catId"], c["catId"], c["catId"] if c["name"] in FLATTEN else None)

walk(0, 0)

wanted = [l for l in locs if l["catId"] in keep]
print("locations to fetch:", len(wanted), file=sys.stderr)

def fetch(l):
    url = f"{API}/locations/{l['id']}?map=336&key={KEY}"
    for _ in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            pass
    return l

with ThreadPoolExecutor(12) as ex:
    details = list(ex.map(fetch, wanted))

ALLOWED = {"p", "ul", "ol", "li", "a", "strong", "b", "em", "i", "br", "h3", "h4"}

class Clean(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED:
            return
        tag = {"b": "strong", "i": "em", "h3": "strong", "h4": "strong"}.get(tag, tag)
        if tag == "a":
            href = dict(attrs).get("href", "") or ""
            if href.startswith("//"):
                href = "https:" + href
            if not re.match(r"^https?://", href):
                self.out.append("<span>"); self._a = "span"; return
            self._a = "a"
            self.out.append(f'<a href="{html.escape(href, quote=True)}" target="_blank" rel="noopener">')
        elif tag == "br":
            self.out.append("<br>")
        else:
            self.out.append(f"<{tag}>")
    def handle_endtag(self, tag):
        if tag not in ALLOWED or tag == "br":
            return
        if tag == "a":
            self.out.append(f"</{getattr(self, '_a', 'a')}>"); return
        tag = {"b": "strong", "i": "em", "h3": "strong", "h4": "strong"}.get(tag, tag)
        self.out.append(f"</{tag}>")
    def handle_data(self, data):
        self.out.append(html.escape(data.replace("\xa0", " "), quote=False))

def clean_html(s):
    if not s:
        return ""
    p = Clean(); p.feed(s); p.close()
    h = "".join(p.out)
    h = re.sub(r"<strong>\s*</strong>", "", h)
    h = re.sub(r"<p>\s*(<br>\s*)*</p>", "", h)
    h = re.sub(r"(<br>\s*){2,}", "<br>", h)
    h = re.sub(r"<p>\s*<br>", "<p>", h)
    return h.strip()

def text_of(s):
    t = re.sub(r"<br\s*/?>|</p>|</li>", "\n", s or "")
    t = html.unescape(re.sub(r"<[^>]+>", "", t)).replace("\xa0", " ")
    return re.sub(r"[ \t]+", " ", t)

def field(t, label):
    m = re.search(label + r"\s*:\s*([^\n]+)", t, re.I)
    return m.group(1).strip() if m else ""

def strip_fields(h):
    # Remove the label/value lines we show separately (address, code, number).
    for label in ("Address", "Building code", "Building number", "Description"):
        pat = r"<strong>\s*" + label + r"\s*:?\s*</strong>\s*:?\s*"
        if label == "Description":
            h = re.sub(pat, "", h, flags=re.I)
        else:
            h = re.sub(pat + r"[^<]*(<br>)?", "", h, flags=re.I)
    h = re.sub(r"<p>\s*(<br>\s*)*</p>", "", h)
    h = re.sub(r"<br>\s*</p>", "</p>", h)
    return h.strip()

out_locs = []
for d in details:
    t = text_of(d.get("description", ""))
    code = field(t, "Building code")
    m = re.search(r"\(([A-Z0-9]{2,6})\)\s*$", d["name"].strip())
    if not code and m:
        code = m.group(1)
    alt = [a for a in (d.get("mediaAltDescriptions") or []) if a and a.strip()]
    rec = {
        "id": d["id"],
        "n": html.unescape(d["name"]).strip(),
        "c": keep[d["catId"]],
        "la": round(d["lat"], 6),
        "ln": round(d["lng"], 6),
        "a": field(t, "Address"),
        "code": code,
        "num": field(t, "Building number"),
        "d": strip_fields(clean_html(d.get("description", ""))),
        "img": alt[0].strip() if alt else "",
        "k": (d.get("keywords") or "").strip(" ,"),
    }
    out_locs.append({k: v for k, v in rec.items() if v not in ("", None)})

# Drop categories that ended up with no locations anywhere beneath them.
has = {l["c"] for l in out_locs}
def nonempty(cid):
    return cid in has or any(nonempty(c["id"]) for c in out_cats if c["parent"] == cid)
out_cats = [c for c in out_cats if nonempty(c["id"])]

json.dump({"cats": out_cats, "locs": out_locs}, open(OUT, "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
print("wrote", OUT, len(out_cats), "categories,", len(out_locs), "locations", file=sys.stderr)

