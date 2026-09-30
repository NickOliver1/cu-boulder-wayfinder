"""Match CU Boulder map buildings to OpenStreetMap footprints and their mapped entrances.

Writes entrances.json: { "<concept3d building id>": [[lat, lng, kind, flags, label], ...] }
  kind: 0 main, 1 regular, 2 service / back
  flags: bit 1 = wheelchair accessible, bit 2 = not wheelchair accessible
"""
import json, math, os, sys, time, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
BBOX = (39.9930, -105.2840, 40.0215, -105.2330)
data = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))
BUILDING_ROOT = next(c["id"] for c in data["cats"] if c["name"] == "Buildings" and c["parent"] == 0)
sub = {BUILDING_ROOT}
changed = True
while changed:
    changed = False
    for c in data["cats"]:
        if c["parent"] in sub and c["id"] not in sub:
            sub.add(c["id"]); changed = True
bldgs = [l for l in data["locs"] if l["c"] in sub and BBOX[0] < l["la"] < BBOX[2] and BBOX[1] < l["ln"] < BBOX[3]]

SERVERS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
           "https://overpass.private.coffee/api/interpreter"]

def overpass(q):
    last = None
    for attempt in range(6):
        url = SERVERS[attempt % len(SERVERS)]
        try:
            req = urllib.request.Request(url, data=urllib.parse.urlencode({"data": q}).encode(),
                                         headers={"User-Agent": "cu-boulder-wayfinder/1.0 (accessibility project)"})
            return json.load(urllib.request.urlopen(req, timeout=240))
        except Exception as e:
            last = e
            print(f"{url}: {e}; retrying", file=sys.stderr)
            time.sleep(5)
    raise last

fp = overpass(f"[out:json][timeout:180];(way[building]{BBOX};relation[building]{BBOX};);out geom;")
ent = overpass(f'[out:json][timeout:180];node[entrance]{BBOX};out;')

KX = math.cos(math.radians(40.007)) * 111320; KY = 110540
xy = lambda la, ln: ((ln - BBOX[1]) * KX, (la - BBOX[0]) * KY)

rings = []  # (osm name, [ (x,y), ... ])
for e in fp["elements"]:
    name = e.get("tags", {}).get("name", "")
    if e["type"] == "way" and "geometry" in e:
        rings.append((name, [xy(p["lat"], p["lon"]) for p in e["geometry"]]))
    elif e["type"] == "relation":
        for m in e.get("members", []):
            if m.get("role") == "outer" and "geometry" in m:
                rings.append((name, [xy(p["lat"], p["lon"]) for p in m["geometry"]]))

def inside(pt, ring):
    x, y = pt; c = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1:
            c = not c
    return c

def seg_dist(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy + 1e-12)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)

def ring_dist(p, ring):
    return min(seg_dist(p, a, b) for a, b in zip(ring, ring[1:] + ring[:1]))

entrances = []
for n in ent["elements"]:
    t = n.get("tags", {})
    kind_tag = t.get("entrance", "")
    if kind_tag in ("emergency", "no", "garage"):
        continue
    kind = 0 if kind_tag == "main" else 2 if kind_tag in ("service", "exit", "staircase") and kind_tag != "staircase" else 1
    flags = (1 if t.get("wheelchair") in ("yes", "designated") else 0) | (2 if t.get("wheelchair") == "no" else 0)
    label = t.get("name") or t.get("ref") or t.get("description") or ""
    entrances.append((xy(n["lat"], n["lon"]), [round(n["lat"], 6), round(n["lon"], 6), kind, flags, label]))

out, matched_fp, with_ent = {}, 0, 0
for b in bldgs:
    c = xy(b["la"], b["ln"])
    cand = [r for r in rings if inside(c, r[1])]
    if not cand:
        near = sorted(rings, key=lambda r: ring_dist(c, r[1]))[:1]
        cand = [r for r in near if ring_dist(c, r[1]) < 25]
    if not cand:
        continue
    matched_fp += 1
    ring = min(cand, key=lambda r: abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(r[1], r[1][1:] + r[1][:1]))))[1]
    doors = [rec for p, rec in entrances if ring_dist(p, ring) < 2.5 or inside(p, ring)]
    if doors:
        with_ent += 1
        out[str(b["id"])] = doors

json.dump(out, open(os.path.join(HERE, "entrances.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"{len(bldgs)} campus building records, {matched_fp} matched to footprints, {with_ent} with mapped entrances, "
      f"{sum(len(v) for v in out.values())} entrances", file=sys.stderr)
