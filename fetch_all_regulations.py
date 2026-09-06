#!/usr/bin/env python3
"""Saekir ALLAR reglugerdir af island.is (ekki bara thaer sem tengjast einu mali).

Notkun:
    python3 fetch_all_regulations.py
"""
import json
import time
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "reglugerdir"
API = "https://island.is/api/graphql"
WORKERS = 8

SEARCH_Q = """
query($input: GetRegulationsInput!) { getRegulations(input: $input) }
"""
REG_Q = """
query($input: GetRegulationInput!) { getRegulation(input: $input) }
"""


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
            time.sleep(min(2 ** attempt, 30))
    raise last_err


def list_all():
    all_items = {}
    page = 1
    while True:
        d = gql(SEARCH_Q, {"input": {"page": page, "type": "newest"}})
        r = d["getRegulations"]
        for it in r["data"]:
            all_items[it["name"]] = it
        print(f"  síða {page}/{r['totalPages']}: {len(all_items)} / {r['totalItems']}")
        if page >= r["totalPages"]:
            break
        page += 1
        time.sleep(0.15)
    return all_items


def fetch_one(name, meta):
    fname = name.replace("/", "-") + ".json"
    outpath = OUTDIR / fname
    if outpath.exists():
        return None
    try:
        d = gql(REG_Q, {"input": {"name": name.replace("/", "-"), "viewType": "current"}})
        reg = d["getRegulation"]
    except Exception as e:
        return f"villa við {name}: {e}"
    reg["_search_meta"] = meta
    outpath.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    return None


def main():
    OUTDIR.mkdir(exist_ok=True)
    print("Sæki lista yfir allar reglugerðir...")
    all_items = list_all()
    print(f"Samtals {len(all_items)} reglugerðir. Sæki fullan texta með {WORKERS} samhliða þráðum...")

    n = 0
    errors = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(fetch_one, name, meta): name for name, meta in all_items.items()}
        for fut in as_completed(futures):
            res = fut.result()
            n += 1
            if res:
                errors += 1
                print(" ", res)
            if n % 500 == 0:
                print(f"  ... {n}/{len(all_items)} unnar ({errors} villur)")

    print(f"Lokið. {n} reglugerðir yfirfarnar, {errors} villur.")


if __name__ == "__main__":
    main()
