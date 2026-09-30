"""Pull the walkable path network around CU Boulder from OpenStreetMap and write paths.json.

Output format (compact, for embedding):
  nodes: flat list [lat1e6 offset, lng1e6 offset, ...] relative to origin
  ways:  [[nameIndex, kind, n0, n1, n2, ...], ...]   kind: 0 walkway, 1 street, 2 stairs, 3 crossing
  names: list of street/path names (index 0 is "")
"""
import json, os, sys, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
BBOX = (39.9930, -105.2840, 40.0215, -105.2330)  # south, west, north, east: Main, East, Williams Village
WALKABLE = "footway|path|pedestrian|steps|cycleway|living_street|residential|service|unclassified|tertiary|secondary|primary|track|corridor"

query = f"""
[out:json][timeout:120];
way["highway"~"^({WALKABLE})$"]["foot"!~"no|private"]["access"!~"^(no|private)$"]{BBOX};
(._;>;);
out body;
"""
req = urllib.request.Request(
    "https://overpass-api.de/api/interpreter",
    data=urllib.parse.urlencode({"data": query}).encode(),
    headers={"User-Agent": "cu-boulder-wayfinder/1.0 (accessibility project)"},
)
raw = json.load(urllib.request.urlopen(req, timeout=180))

osm_nodes = {e["id"]: e for e in raw["elements"] if e["type"] == "node"}
osm_ways = [e for e in raw["elements"] if e["type"] == "way"]

# Drop motorways-with-no-sidewalk style roads where OSM says sidewalks are absent.
def usable(w):
    t = w.get("tags", {})
    if t.get("highway") in ("primary", "secondary") and t.get("sidewalk") == "no" and t.get("foot") not in ("yes", "designated"):
        return False
    if t.get("highway") == "service" and t.get("service") in ("parking_aisle", "drive-through"):
        return True
    return True

LAT0, LNG0 = BBOX[0], BBOX[1]
index, nodes, names, name_idx, ways = {}, [], [""], {"": 0}, []

def nid(osm_id):
    if osm_id not in index:
        n = osm_nodes[osm_id]
        index[osm_id] = len(index)
        nodes.extend([round((n["lat"] - LAT0) * 1e6), round((n["lon"] - LNG0) * 1e6)])
    return index[osm_id]

for w in osm_ways:
    if not usable(w):
        continue
    t = w.get("tags", {})
    hw = t.get("highway")
    if hw == "steps":
        kind = 2
    elif t.get("footway") == "crossing" or t.get("path") == "crossing":
        kind = 3
    elif hw in ("footway", "path", "pedestrian", "cycleway", "track", "corridor"):
        kind = 0
    else:
        kind = 1
    name = t.get("name", "") if kind != 3 else ""
    if kind == 0 and not name and t.get("footway") == "sidewalk":
        name = ""
    if name not in name_idx:
        name_idx[name] = len(names)
        names.append(name)
    refs = [r for r in w["nodes"] if r in osm_nodes]
    if len(refs) < 2:
        continue
    ways.append([name_idx[name], kind] + [nid(r) for r in refs])

out = {"origin": [LAT0, LNG0], "nodes": nodes, "ways": ways, "names": names}
json.dump(out, open(os.path.join(HERE, "paths.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(len(index), "nodes,", len(ways), "ways,", len(names), "names", file=sys.stderr)
