#!/usr/bin/env python3
"""Saekir samthykktar thingsalyktanir Althingis (ekki tillogur sem daudu i
nefnd) fyrir thing 130-157, af XML-vefthjonustu althingi.is.

Fyrir hvert thing:
  1. Saekir thingmalalisti (?lthing=N) og sigtar mal med malstegund='a'
     (tillaga til thingsalyktunar).
  2. Saekir mal-nanar (thingmalalisti/thingmal/?lthing=N&malnr=M) og athugar
     hvort stadamals segir samthykkt sem alyktun.
  3. Ef samthykkt: finnur lokaskjalid (skjalategund byrjar a "thal") og
     saekir HTML-textann.

Vistar hverja alyktun i alyktanir/<thing>-<malnr>.json.

Notkun:
    python3 fetch_alyktanir.py
"""
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "alyktanir"
WORKERS = 6
THING_RANGE = range(130, 158)


def fetch_url(url, retries=5, timeout=30):
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:
            last_err = e
            time.sleep(min(2 ** attempt, 20))
    raise last_err


def text_of(el):
    return (el.text or "").strip() if el is not None else None


def list_thal_mal(lthing):
    raw = fetch_url(f"https://www.althingi.is/altext/xml/thingmalalisti/?lthing={lthing}")
    root = ET.fromstring(raw)
    out = []
    for mal in root.findall("mál"):
        mt = mal.find("málstegund")
        if mt is not None and mt.get("málstegund") == "a":
            out.append(mal.get("málsnúmer"))
    return out


def html_to_text(html_bytes):
    html = html_bytes.decode("utf-8", errors="replace")
    body = re.search(r'<div class="article\s+box news">(.*?)</div>\s*</div>', html, re.S)
    chunk = body.group(1) if body else html
    chunk = re.sub(r"<script.*?</script>", " ", chunk, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", chunk)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_one(lthing, malnr):
    outpath = OUTDIR / f"{lthing}-{malnr}.json"
    if outpath.exists():
        return None
    try:
        raw = fetch_url(f"https://www.althingi.is/altext/xml/thingmalalisti/thingmal/?lthing={lthing}&malnr={malnr}")
        root = ET.fromstring(raw)
    except Exception as e:
        return f"villa við {lthing}/{malnr}: {e}"

    mal = root.find("mál")
    stada = text_of(root.find("mál/staðamáls")) or ""
    if "samþykkt" not in stada.lower() or "ályktun" not in stada.lower():
        return None  # ekki samþykkt sem ályktun - sleppa

    heiti = text_of(mal.find("málsheiti"))

    efnisflokkar = []
    for ef in root.findall(".//efnisflokkar/yfirflokkur/efnisflokkur"):
        efnisflokkar.append(text_of(ef.find("heiti")))

    thal_skjal = None
    for sk in root.findall(".//þingskjöl/þingskjal"):
        tegund = text_of(sk.find("skjalategund")) or ""
        if tegund.startswith("þál"):
            thal_skjal = sk  # síðasta (samþykkta) skjalið yfirskrifar fyrri "þál." útgáfur

    if thal_skjal is None:
        return None

    skjalnr = thal_skjal.get("skjalsnúmer")
    html_url = text_of(thal_skjal.find("slóð/html"))
    try:
        html_raw = fetch_url(html_url)
    except Exception as e:
        return f"villa við sókn skjals {lthing}/{skjalnr}: {e}"

    full_text = html_to_text(html_raw)

    rec = {
        "thing": lthing,
        "malnr": malnr,
        "heiti": heiti,
        "stada": stada,
        "efnisflokkar": [e for e in efnisflokkar if e],
        "skjalnr": skjalnr,
        "url": html_url,
        "full_text": full_text,
    }
    outpath.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return None


def main():
    OUTDIR.mkdir(exist_ok=True)
    all_pairs = []
    for lthing in THING_RANGE:
        try:
            malnrs = list_thal_mal(lthing)
        except Exception as e:
            print(f"  villa við þing {lthing} (listun): {e}")
            continue
        print(f"  þing {lthing}: {len(malnrs)} þingsályktunartillögur")
        all_pairs.extend((lthing, m) for m in malnrs)
        time.sleep(0.2)

    print(f"Samtals {len(all_pairs)} tillögur til að athuga (aðeins samþykktar verða vistaðar).")

    n = 0
    saved = 0
    errors = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(fetch_one, lthing, malnr): (lthing, malnr) for lthing, malnr in all_pairs}
        for fut in as_completed(futures):
            res = fut.result()
            n += 1
            if res:
                errors += 1
                print(" ", res)
            if n % 200 == 0:
                print(f"  ... {n}/{len(all_pairs)} skoðaðar")

    saved = len(list(OUTDIR.glob("*.json")))
    print(f"Lokið. {n} tillögur skoðaðar, {saved} samþykktar ályktanir vistaðar, {errors} villur.")


if __name__ == "__main__":
    main()
