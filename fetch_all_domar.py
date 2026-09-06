#!/usr/bin/env python3
"""Saekir ALLA doma af island.is (heradsdomur + Landsrettur + Haestirettur +
Endurupptokudomur), ekki bara thau sem tengjast einu mali.

Notkun:
    python3 fetch_all_domar.py
"""
import base64
import io
import json
import re
import time
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "domar"
API = "https://island.is/api/graphql"
WORKERS = 8

SEARCH_Q = """
query($input: WebVerdictsInput!) {
  webVerdicts(input: $input) { total items { id } }
}
"""
BYID_Q = """
query($input: WebVerdictByIdInput!) {
  webVerdictById(input: $input) {
    item {
      title court caseNumber verdictDate keywords presentings resolutionLink
      richText
      pdfString
    }
  }
}
"""


def gql(query, variables, retries=5):
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"})
    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if "errors" in data:
                raise RuntimeError(data["errors"])
            return data["data"]
        except Exception as e:
            last_err = e
            time.sleep(min(2 ** attempt, 30))
    raise last_err


def flatten_richtext(node):
    if node is None:
        return ""
    doc = node.get("document") if isinstance(node, dict) else None
    if doc is None:
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

    walk(doc)
    return re.sub(r"[ \t]+", " ", "".join(parts)).strip()


def flatten_pdf(b64):
    if not b64:
        return ""
    try:
        raw = base64.b64decode(b64)
        reader = PdfReader(io.BytesIO(raw))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
        return re.sub(r"[ \t]+", " ", text).strip()
    except Exception as e:
        print("    pdf villa:", e)
        return ""


def list_all_ids():
    ids = set()
    page = 1
    while True:
        try:
            d = gql(SEARCH_Q, {"input": {"page": page, "pageSize": 100}})
        except Exception as e:
            print(f"  villa á síðu {page}, hætti við listun: {e}")
            break
        r = d["webVerdicts"]
        got = [it["id"] for it in r["items"]]
        if not got:
            break
        ids.update(got)
        print(f"  síða {page}: {len(ids)} / {r['total']}")
        if len(ids) >= r["total"]:
            break
        page += 1
        time.sleep(0.15)
    return ids


def fetch_one(vid):
    outpath = OUTDIR / f"{vid}.json"
    if outpath.exists():
        try:
            existing = json.loads(outpath.read_text(encoding="utf-8"))
            if existing.get("full_text") or existing.get("full_text") == "":
                return None
        except Exception:
            pass
    try:
        d = gql(BYID_Q, {"input": {"id": vid}})
        item = d["webVerdictById"]["item"] if d["webVerdictById"] else None
    except Exception as e:
        return f"villa við {vid}: {e}"
    if item is None:
        return None
    text = flatten_richtext(item.pop("richText", None))
    pdf_b64 = item.pop("pdfString", None)
    source = "richText"
    if not text and pdf_b64:
        text = flatten_pdf(pdf_b64)
        source = "pdf"
    if not text:
        source = "none"
    item["id"] = vid
    item["full_text"] = text
    item["full_text_source"] = source
    outpath.write_text(json.dumps(item, ensure_ascii=False, indent=1), encoding="utf-8")
    return None


def main():
    OUTDIR.mkdir(exist_ok=True)
    print("Sæki lista yfir alla dóma (getur tekið nokkrar mínútur)...")
    ids = list_all_ids()
    print(f"Samtals {len(ids)} dómar. Sæki fullan texta með {WORKERS} samhliða þráðum...")

    n = 0
    error_records = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(fetch_one, vid): vid for vid in ids}
        for fut in as_completed(futures):
            vid = futures[fut]
            res = fut.result()
            n += 1
            if res:
                error_records.append({"id": vid, "error": res})
                print(" ", res)
            if n % 1000 == 0:
                print(f"  ... {n}/{len(ids)} unnir ({len(error_records)} villur)")

    if error_records:
        (HERE / "domar_errors.json").write_text(
            json.dumps(error_records, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    print(f"Lokið. {n} dómar yfirfarnir, {len(error_records)} villur (sjá domar_errors.json).")


if __name__ == "__main__":
    main()
