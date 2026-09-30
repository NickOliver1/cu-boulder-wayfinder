"""Embed the data into template.html.

Writes two files next to the build folder:
  build/artifact-body.html              page body only, for hosts that supply their own document shell
  index.html                            complete web page (served by GitHub Pages, or open it in any browser)
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")

def embed(name):
    return open(os.path.join(HERE, name), encoding="utf-8").read().replace("</", "<\\/")

data = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))
payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
page = tpl.replace("/*DATA*/", payload).replace("/*PATHS*/", embed("paths.json")).replace("/*DOORS*/", embed("entrances.json"))

out = os.path.join(HERE, "artifact-body.html")
open(out, "w", encoding="utf-8").write(page)
print("wrote", os.path.abspath(out), os.path.getsize(out), "bytes")

# Standalone: the template's <title>, font links and <style> go in <head>; everything after them is the body.
split = page.index("</style>") + len("</style>")
head, body = page[:split], page[split:]
standalone = (
    "<!doctype html>\n<html lang=\"en\">\n<head>\n"
    "<meta charset=\"utf-8\">\n"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
    "<meta name=\"description\" content=\"Unofficial, screen-reader-first guide to the CU Boulder campus maps with walking directions.\">\n"
    "<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}"
    "body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n"
    + head + "\n</head>\n<body>\n" + body + "\n</body>\n</html>\n"
)
out2 = os.path.join(ROOT, "index.html")
open(out2, "w", encoding="utf-8").write(standalone)
print("wrote", os.path.abspath(out2), os.path.getsize(out2), "bytes")

