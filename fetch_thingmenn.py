#!/usr/bin/env python3
"""Saekir thingmannaskra Althingis (nafn, aevi, thingseta, nefndaseta) af
XML-vefthjonustu althingi.is og vistar hvern thingmann i thingmenn/<id>.json.

Notkun:
    python3 fetch_thingmenn.py
"""
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "thingmenn"
LIST_URL = "https://www.althingi.is/altext/xml/thingmenn/"
DETAIL_TMPL = "https://www.althingi.is/altext/xml/thingmenn/thingmadur/{kind}?nr={id}"
WORKERS = 6


def fetch_url(url, retries=5):
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except Exception as e:
            last_err = e
            time.sleep(min(2 ** attempt, 20))
    raise last_err


def text_of(el):
    return (el.text or "").strip() if el is not None else None


def list_mps():
    raw = fetch_url(LIST_URL)
    root = ET.fromstring(raw)
    mps = []
    for tm in root.findall("þingmaður"):
        mps.append({"id": tm.get("id"), "nafn": text_of(tm.find("nafn")), "faedingardagur": text_of(tm.find("fæðingardagur"))})
    return mps


def fetch_lifshlaup(mp_id):
    raw = fetch_url(DETAIL_TMPL.format(kind="lifshlaup/", id=mp_id))
    root = ET.fromstring(raw)
    lh = root.find("lífshlaup")
    if lh is None:
        return {}
    out = {}
    for child in lh:
        tag = child.tag
        val = (child.text or "").strip()
        if val:
            out[tag] = val
    return out


def fetch_thingseta(mp_id):
    raw = fetch_url(DETAIL_TMPL.format(kind="thingseta/", id=mp_id))
    root = ET.fromstring(raw)
    out = []
    for ts in root.findall(".//þingsetur/þingseta"):
        tímabil = ts.find("tímabil")
        out.append({
            "thing": text_of(ts.find("þing")),
            "skammstofun": text_of(ts.find("skammstöfun")),
            "tegund": text_of(ts.find("tegund")),
            "thingflokkur": text_of(ts.find("þingflokkur")),
            "kjordaemi": text_of(ts.find("kjördæmi")),
            "inn": text_of(tímabil.find("inn")) if tímabil is not None else None,
            "ut": text_of(tímabil.find("út")) if tímabil is not None else None,
        })
    return out


def fetch_nefndaseta(mp_id):
    raw = fetch_url(DETAIL_TMPL.format(kind="nefndaseta/", id=mp_id))
    root = ET.fromstring(raw)
    out = []
    for ns in root.findall(".//nefndasetur/nefndaseta"):
        out.append({
            "nefnd": text_of(ns.find("nefnd")),
            "hlutverk": text_of(ns.find("hlutverk")),
            "thing": text_of(ns.find("þing")),
        })
    return out


def fetch_one(mp):
    mp_id = mp["id"]
    outpath = OUTDIR / f"{mp_id}.json"
    if outpath.exists():
        return None
    try:
        rec = dict(mp)
        rec["lifshlaup"] = fetch_lifshlaup(mp_id)
        rec["thingseta"] = fetch_thingseta(mp_id)
        rec["nefndaseta"] = fetch_nefndaseta(mp_id)
    except Exception as e:
        return f"villa við {mp_id} ({mp.get('nafn')}): {e}"
    outpath.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return None


def main():
    OUTDIR.mkdir(exist_ok=True)
    print("Sæki þingmannalista...")
    mps = list_mps()
    print(f"Samtals {len(mps)} þingmenn. Sæki æviatriði/þingsetu/nefndasetu með {WORKERS} þráðum...")

    n = 0
    errors = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(fetch_one, mp): mp for mp in mps}
        for fut in as_completed(futures):
            res = fut.result()
            n += 1
            if res:
                errors += 1
                print(" ", res)
            if n % 200 == 0:
                print(f"  ... {n}/{len(mps)} unnir ({errors} villur)")

    print(f"Lokið. {n} þingmenn yfirfarnir, {errors} villur.")


if __name__ == "__main__":
    main()
