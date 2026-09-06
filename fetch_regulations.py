#!/usr/bin/env python3
"""Saekir reglugerdir af island.is sem tengjast tilteknum efnisordum og vistar
hverja regluger i reglugerdir/<nafn>.json.

Notar innri GraphQL-vef island.is (sama og vefsidan sjalf notar):
    getRegulationsSearch(input: {q, page, ch, iA, iR, rn})
    getRegulation(input: {name, viewType})

Notkun:
    python3 fetch_regulations.py
"""
import json
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "reglugerdir"
API = "https://island.is/api/graphql"
SLEEP = 0.35

# Efnisord sem tengjast malinu: adfor/fjarnam, innheimta, gjaldthrot,
# fyrning krofurettinda, Menntasjodur/namslan.
QUERIES = [
    "aðför",
    "fjárnám",
    "gjaldþrotaskipti",
    "fyrning kröfuréttinda",
    "Menntasjóð",
    "námslán",
]


def gql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        API, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


SEARCH_Q = """
query($input: GetRegulationsSearchInput!) { getRegulationsSearch(input: $input) }
"""
REG_Q = """
query($input: GetRegulationInput!) { getRegulation(input: $input) }
"""


def search_all(q):
    page = 1
    seen = []
    while True:
        d = gql(SEARCH_Q, {"input": {"ch": "", "iA": False, "iR": False, "page": page, "q": q, "rn": ""}})
        r = d["getRegulationsSearch"]
        seen.extend(r["data"])
        if page >= r["totalPages"]:
            break
        page += 1
        time.sleep(SLEEP)
    return seen


def main():
    OUTDIR.mkdir(exist_ok=True)
    all_items = {}
    for q in QUERIES:
        items = search_all(q)
        print(f"'{q}': {len(items)} reglugerðir")
        for it in items:
            all_items[it["name"]] = it
        time.sleep(SLEEP)

    print(f"\nSamtals {len(all_items)} einstakar reglugerðir að sækja.")

    n = 0
    for name, meta in sorted(all_items.items()):
        fname = name.replace("/", "-") + ".json"
        outpath = OUTDIR / fname
        if outpath.exists():
            continue
        try:
            d = gql(REG_Q, {"input": {"name": name.replace("/", "-"), "viewType": "current"}})
            reg = d["getRegulation"]
        except Exception as e:
            print(f"  villa við {name}: {e}")
            continue
        reg["_search_meta"] = meta
        outpath.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
        n += 1
        if n % 20 == 0:
            print(f"  ... {n} sóttar")
        time.sleep(SLEEP)

    print(f"Lokið. {n} nýjar reglugerðir vistaðar í {OUTDIR}")


if __name__ == "__main__":
    main()
