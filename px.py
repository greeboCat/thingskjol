#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
px - flettir og sækir töflur úr talnagrunni Hagstofu Íslands.
Engir aðfluttir pakkar, aðeins grunnsafn Python 3.

  ./px.py tre                          efsta stig
  ./px.py tre Samfelag/launogtekjur    flettir niður
  ./px.py breytur <slod>               sýnir breytur og gildi töflu
  ./px.py sekja <slod> [-o skra.csv]   sækir alla töfluna sem CSV
"""

import argparse
import io
import json
import sys
import urllib.error
import urllib.request

STOFN = "https://px.hagstofa.is/pxis/api/v1/is"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def kalla(slod, gogn=None):
    url = "%s/%s" % (STOFN, slod.strip("/")) if slod else STOFN
    haus = {"User-Agent": UA, "Accept": "application/json"}
    baeti = None
    if gogn is not None:
        baeti = json.dumps(gogn).encode("utf-8")
        haus["Content-Type"] = "application/json"
    beidni = urllib.request.Request(url, data=baeti, headers=haus)
    try:
        with urllib.request.urlopen(beidni, timeout=60) as svar:
            hrar = svar.read()
    except urllib.error.HTTPError as e:
        print("HTTP %s: %s" % (e.code, url), file=sys.stderr)
        print(e.read().decode("utf-8", "replace")[:600], file=sys.stderr)
        sys.exit(1)
    for enc in ("utf-8", "utf-8-sig", "iso-8859-1"):
        try:
            return json.loads(hrar.decode(enc))
        except (UnicodeDecodeError, ValueError):
            continue
    print("Gat ekki lesið svarið sem JSON.", file=sys.stderr)
    sys.exit(1)


def skip_tre(args):
    svar = kalla(args.slod)
    if isinstance(svar, dict):
        print(json.dumps(svar, ensure_ascii=False, indent=2)[:2000])
        return
    for lidur in svar:
        tegund = lidur.get("type", "?")
        merki = "mappa" if tegund == "l" else "tafla"
        print("%-6s %-28s %s" % (merki, lidur.get("id", ""),
                                 lidur.get("text", "")[:70]))


def skip_breytur(args):
    svar = kalla(args.slod)
    print("Tafla: %s" % svar.get("title", ""))
    print()
    for breyta in svar.get("variables", []):
        kodar = breyta.get("values", [])
        heiti = breyta.get("valueTexts", kodar)
        print("%s  (kóði: %s, %d gildi)%s" % (
            breyta.get("text", ""), breyta.get("code", ""), len(kodar),
            "  ELIMINATION" if breyta.get("elimination") else ""))
        for k, h in list(zip(kodar, heiti))[:25]:
            print("    %-14s %s" % (k, h))
        if len(kodar) > 25:
            print("    ... og %d til viðbótar" % (len(kodar) - 25))
        print()


def saekja_csv(slod, ut):
    lysing = kalla(slod)
    fyrirspurn = [{"code": b["code"],
                   "selection": {"filter": "all", "values": ["*"]}}
                  for b in lysing.get("variables", [])]
    gogn = json.dumps({"query": fyrirspurn,
                       "response": {"format": "csv"}}).encode("utf-8")
    url = "%s/%s" % (STOFN, slod.strip("/"))
    beidni = urllib.request.Request(url, data=gogn, headers={
        "User-Agent": UA, "Content-Type": "application/json",
        "Accept": "text/csv"})
    with urllib.request.urlopen(beidni, timeout=120) as svar:
        hrar = svar.read()
    for enc in ("utf-8-sig", "utf-8", "iso-8859-1"):
        try:
            texti = hrar.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        texti = hrar.decode("iso-8859-1", "replace")
    if ut:
        io.open(ut, "w", encoding="utf-8").write(texti)
        print("Vistað: %s (%d bæti)" % (ut, len(texti.encode("utf-8"))))
    else:
        sys.stdout.write(texti)


def main():
    p = argparse.ArgumentParser(prog="px")
    u = p.add_subparsers(dest="skipun", required=True)

    a = u.add_parser("tre", help="flettir gagnatrénu")
    a.add_argument("slod", nargs="?", default="")
    a.set_defaults(func=skip_tre)

    b = u.add_parser("breytur", help="sýnir breytur og gildi töflu")
    b.add_argument("slod")
    b.set_defaults(func=skip_breytur)

    c = u.add_parser("saekja", help="sækir alla töfluna sem CSV")
    c.add_argument("slod")
    c.add_argument("-o", dest="ut", default="")
    c.set_defaults(func=lambda args: saekja_csv(args.slod, args.ut))

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

