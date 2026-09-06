#!/usr/bin/env python3
"""Saekir domaskjol af island.is (heradsdomur + Landsrettur + Haestirettur, um
sameiginlegt GraphQL leitarvidmot) sem tengjast tilteknum efnisordum, og vistar
hvern dom i domar/<id>.json.

Notkun:
    python3 fetch_domar.py
"""
import base64
import io
import json
import re
import time
import urllib.request
from pathlib import Path

from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "domar"
API = "https://island.is/api/graphql"
SLEEP = 0.35

# (merkimidi, {keywords: [...], searchTerm: "..."})
# Efnisordin eru af opinberum lykilordalista dómstólanna (webVerdictKeywords).
QUERY_SPECS = [
    ("Lúganósamningurinn", {"keywords": ["Lúganósamningurinn"]}),
    ("Erlendur dómur", {"keywords": ["Erlendur dómur"]}),
    ("Erlend réttarregla", {"keywords": ["Erlend réttarregla"]}),
    ("Námslán", {"keywords": ["Námslán"]}),
    ("Fyrningarslit", {"keywords": ["Fyrningarslit"]}),
    ("Slit fyrningar", {"keywords": ["Slit fyrningar"]}),
    ("Innheimta opinberra gjalda", {"keywords": ["Innheimta opinberra gjalda"]}),
    ("Aðför + Fjárnám", {"keywords": ["Aðför", "Fjárnám"]}),
    ("Gjaldþrotaskipti + Fjárnám", {"keywords": ["Gjaldþrotaskipti", "Fjárnám"]}),
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
query($input: WebVerdictsInput!) {
  webVerdicts(input: $input) {
    total
    items { id title court caseNumber verdictDate keywords presentings }
  }
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


def flatten_richtext(node):
    """Contentful rich-text document -> plain text."""
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
            for child in n.get("content", []) or []:
                walk(child)
            if n.get("nodeType") in ("paragraph", "heading-1", "heading-2", "heading-3"):
                parts.append("\n")

    walk(doc)
    text = "".join(parts)
    return re.sub(r"[ \t]+", " ", text).strip()


def flatten_pdf(pdf_b64):
    if not pdf_b64:
        return ""
    try:
        raw = base64.b64decode(pdf_b64)
        reader = PdfReader(io.BytesIO(raw))
        pages = [p.extract_text() or "" for p in reader.pages]
        text = "\n".join(pages)
        return re.sub(r"[ \t]+", " ", text).strip()
    except Exception as e:
        print(f"    (pdf villa: {e})")
        return ""


def search_all(spec_input):
    d = gql(SEARCH_Q, {"input": {**spec_input, "page": 1, "pageSize": 100}})
    r = d["webVerdicts"]
    items = list(r["items"])
    if r["total"] > len(items):
        page = 2
        while len(items) < r["total"]:
            d = gql(SEARCH_Q, {"input": {**spec_input, "page": page, "pageSize": 100}})
            more = d["webVerdicts"]["items"]
            if not more:
                break
            items.extend(more)
            page += 1
            time.sleep(SLEEP)
    return r["total"], items


def main():
    OUTDIR.mkdir(exist_ok=True)
    all_items = {}
    for label, spec_input in QUERY_SPECS:
        total, items = search_all(spec_input)
        print(f"{label}: total={total}, sótt={len(items)}")
        for it in items:
            all_items[it["id"]] = it
        time.sleep(SLEEP)

    print(f"\nSamtals {len(all_items)} einstakir dómar að sækja fullan texta fyrir.")

    n = 0
    for vid, meta in sorted(all_items.items()):
        outpath = OUTDIR / f"{vid}.json"
        if outpath.exists():
            existing = json.loads(outpath.read_text(encoding="utf-8"))
            if existing.get("full_text"):
                continue  # already have text, skip
        try:
            d = gql(BYID_Q, {"input": {"id": vid}})
            item = d["webVerdictById"]["item"] if d["webVerdictById"] else None
        except Exception as e:
            print(f"  villa við {vid}: {e}")
            continue
        if item is None:
            continue
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
        n += 1
        if n % 20 == 0:
            print(f"  ... {n} sóttir")
        time.sleep(SLEEP)

    print(f"Lokið. {n} nýir dómar vistaðir í {OUTDIR}")


if __name__ == "__main__":
    main()
