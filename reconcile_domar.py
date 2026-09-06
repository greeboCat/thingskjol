#!/usr/bin/env python3
"""Ber saman fullan lista yfir doma-id fra island.is vid thad sem er thegar
vistad i domar/, og saekir eingongu thau sem vantar (villur af hvaða tagi
sem er - 500, DNS-blip, o.s.frv.). Keyra eftir ad fetch_all_domar.py hefur
lokid, til ad fylla i eyduraur.

Notkun:
    python3 reconcile_domar.py
"""
import json
from pathlib import Path

from fetch_all_domar import list_all_ids, fetch_one, OUTDIR
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = Path(__file__).resolve().parent
ERRORS_PATH = HERE / "domar_errors.json"


def main():
    print("Sæki fullan lista af doma-id frá island.is...")
    all_ids = list_all_ids()
    print(f"Samtals {len(all_ids)} id í heildarlistanum.")

    existing = {p.stem for p in OUTDIR.glob("*.json")}
    missing = sorted(all_ids - existing)
    print(f"{len(existing)} þegar vistaðir, {len(missing)} vantar.")

    if not missing:
        print("Ekkert vantar - allt í lagi.")
        if ERRORS_PATH.exists():
            ERRORS_PATH.unlink()
        return

    errors = []
    n = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(fetch_one, vid): vid for vid in missing}
        for fut in as_completed(futures):
            vid = futures[fut]
            res = fut.result()
            n += 1
            if res:
                errors.append({"id": vid, "error": res})
                print(" ", res)
            if n % 100 == 0:
                print(f"  ... {n}/{len(missing)}")

    ERRORS_PATH.write_text(json.dumps(errors, ensure_ascii=False, indent=1), encoding="utf-8")
    still_missing = len(missing) - (n - len(errors))
    print(f"Lokið. {n - len(errors)} ný sótt, {len(errors)} enn með villu (sjá {ERRORS_PATH}).")


if __name__ == "__main__":
    main()
