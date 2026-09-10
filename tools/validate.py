"""Fetch every transitively referenced PBIR schema, then validate generated JSON against it."""
import json, os, re, urllib.parse, urllib.request, glob, sys

CACHE = os.path.join(os.path.dirname(__file__), "..", "schema_cache")
os.makedirs(CACHE, exist_ok=True)
RAW = "https://raw.githubusercontent.com/microsoft/json-schemas/main/fabric/"
DEV = "https://developer.microsoft.com/json-schemas/fabric/"


def _path_for(url):
    return os.path.join(CACHE, urllib.parse.quote(url, safe="") + ".json")


def fetch(url, seen=None):
    """Download `url` (mapping developer.microsoft.com -> raw.githubusercontent) and all its $refs."""
    seen = seen if seen is not None else set()
    if url in seen:
        return
    seen.add(url)
    p = _path_for(url)
    if not os.path.exists(p):
        src = url.replace(DEV, RAW) if url.startswith(DEV) else url
        with urllib.request.urlopen(src, timeout=60) as r:
            data = r.read()
        open(p, "wb").write(data)
    doc = json.load(open(p, encoding="utf-8"))
    for ref in set(re.findall(r'"\$ref"\s*:\s*"([^"]+)"', json.dumps(doc))):
        if ref.startswith("#"):
            continue
        child = urllib.parse.urljoin(url, ref.split("#")[0])
        fetch(child, seen)
    return seen


def registry():
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT7
    res = []
    for f in glob.glob(os.path.join(CACHE, "*.json")):
        url = urllib.parse.unquote(os.path.basename(f)[:-5])
        doc = json.load(open(f, encoding="utf-8"))
        res.append((url, Resource.from_contents(doc, default_specification=DRAFT7)))
        # also register under the document's own $id so internal refs resolve
        if isinstance(doc, dict) and doc.get("$id") and doc["$id"] != url:
            res.append((doc["$id"], Resource.from_contents(doc, default_specification=DRAFT7)))
    return Registry().with_resources(res)


def validate_tree(report_dir):
    from jsonschema import Draft7Validator
    reg = registry()
    files = sorted(glob.glob(os.path.join(report_dir, "**", "*.json"), recursive=True))
    files += sorted(glob.glob(os.path.join(report_dir, "definition.pbir")))
    roots = set()
    problems, checked = [], 0
    for f in files:
        doc = json.load(open(f, encoding="utf-8"))
        s = doc.get("$schema") if isinstance(doc, dict) else None
        if not s:
            continue
        roots.add(s)
        fetch(s)
        schema = json.load(open(_path_for(s), encoding="utf-8"))
        v = Draft7Validator(schema, registry=registry())
        errs = sorted(v.iter_errors(doc), key=lambda e: list(e.path))
        checked += 1
        for e in errs[:6]:
            problems.append(f"{os.path.relpath(f, report_dir)}: /{'/'.join(map(str, e.path))}: {e.message[:220]}")
    return checked, roots, problems


if __name__ == "__main__":
    target = sys.argv[1]
    # seed the cache from the schemas we know we emit
    for s in [
        DEV + "item/report/definition/visualContainer/2.8.0/schema.json",
        DEV + "item/report/definition/page/2.1.0/schema.json",
        DEV + "item/report/definition/pagesMetadata/1.0.0/schema.json",
        DEV + "item/report/definition/report/3.2.0/schema.json",
        DEV + "item/report/definition/versionMetadata/1.0.0/schema.json",
        DEV + "item/report/definitionProperties/2.0.0/schema.json",
        DEV + "gitIntegration/platformProperties/2.0.0/schema.json",
        DEV + "item/semanticModel/definitionProperties/1.0.0/schema.json",
        DEV + "pbip/pbipProperties/1.0.0/schema.json",
    ]:
        fetch(s)
    n, roots, probs = validate_tree(target)
    print(f"validated {n} json files against {len(roots)} root schemas")
    for r in sorted(roots):
        print("   ", r.rsplit("/definition/", 1)[-1] if "/definition/" in r else r.rsplit("fabric/", 1)[-1])
    if probs:
        print(f"\n!! {len(probs)} SCHEMA PROBLEM(S):")
        for p in probs:
            print("  -", p)
        sys.exit(1)
    print("\nOK - no schema violations")
