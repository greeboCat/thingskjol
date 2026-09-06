#!/usr/bin/env python3
"""Saekir urskurdi/akvardanir/alit stjornsyslunefnda sem eru hyst a island.is
gegnum GenericList-kerfid. Byrjar med Personuvernd.

Vistar hvert atridi i urskurdir/<stofnun>/<id>.json.

Notkun:
    python3 fetch_urskurdir.py
"""
import json
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "urskurdir"
API = "https://island.is/api/graphql"

# (stofnun-slug, heiti, genericListId)
SOURCES = [
    ("personuvernd", "Persónuvernd", "18Qfx6UBAJmLrmaNZZA6lM"),
]


def gql(query, variables, retries=5):
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"})
    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if "errors" in data:
                raise RuntimeError(data["errors"])
            return data["data"]
        except Exception as e:
            last_err = e
            time.sleep(min(2 ** attempt, 20))
    raise last_err


ITEMS_Q = """
query($input: GetGenericListItemsInput!) {
  getGenericListItems(input: $input) {
    total
    items { id title date slug content { ... on Html { document } } }
  }
}
"""


def flatten_richtext(node):
    if node is None:
        return ""
    parts = []

    def walk(n):
        if isinstance(n, dict):
            if n.get("nodeType") == "text":
                parts.append(n.get("value", ""))
            for c in n.get("content", []) or []:
                walk(c)
            if n.get("nodeType") in ("paragraph", "heading-1", "heading-2", "heading-3"):
                parts.append("\n")

    walk(node)
    import re
    return re.sub(r"[ \t]+", " ", "".join(parts)).strip()


def fetch_source(slug, heiti, generic_list_id):
    outdir = OUTDIR / slug
    outdir.mkdir(parents=True, exist_ok=True)
    page = 1
    n_saved = 0
    n_seen = 0
    while True:
        d = gql(ITEMS_Q, {"input": {"lang": "is", "genericListId": generic_list_id, "page": page, "size": 50}})
        r = d["getGenericListItems"]
        if page == 1:
            print(f"  {heiti}: {r['total']} atriði samtals")
        if not r["items"]:
            break
        for it in r["items"]:
            n_seen += 1
            outpath = outdir / f"{it['id']}.json"
            if outpath.exists():
                continue
            content_blocks = it.get("content") or []
            full_text = "\n\n".join(flatten_richtext(c.get("document")) for c in content_blocks if c)
            rec = {
                "id": it["id"],
                "title": it["title"],
                "date": it.get("date"),
                "slug": it.get("slug"),
                "stofnun": heiti,
                "url": f"https://island.is/s/{slug}/{it.get('slug')}" if it.get("slug") else None,
                "full_text": full_text,
            }
            outpath.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            n_saved += 1
        if n_seen >= r["total"]:
            break
        page += 1
        time.sleep(0.2)
    print(f"  {heiti}: {n_saved} ný vistuð (af {n_seen} skoðuðum)")


def main():
    OUTDIR.mkdir(exist_ok=True)
    for slug, heiti, gl_id in SOURCES:
        fetch_source(slug, heiti, gl_id)


if __name__ == "__main__":
    main()
