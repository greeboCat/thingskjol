#!/usr/bin/env python3
"""Sameiginlegt leitartol fyrir gagnasafn.db (log + reglugerdir + domar).

Daemi:
    python3 search.py leit "árangurslaust fjárnám"
    python3 search.py leit "Lúganó*" --type domur
    python3 search.py log 1989090.html
    python3 search.py breytingar 1989090.html
    python3 search.py reglugerd 0017-1992
    python3 search.py domur s-4E51D2F3-492C-4C7C-A92B-560898515446
    python3 search.py thingmadur 1347
    python3 search.py alyktun 141-567

Vefslóðir laga: https://www.althingi.is/lagas/nuna/<skrá> (nýjasta útgáfa).
Beint í grein: bæta við #G<greinarnúmer>, t.d. #G10. Í málsgrein: #G10AM4 (4. mgr. 10. gr.).
"""
import argparse
import sqlite3
import sys
import textwrap
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "gagnasafn.db"


def connect():
    if not DB_PATH.exists():
        sys.exit(f"Finn ekki {DB_PATH} - keyrdu fyrst: python3 build_db.py")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def cmd_leit(args):
    conn = connect()
    query = args.query
    results = []

    if args.type in ("allt", "log"):
        rows = conn.execute(
            """SELECT l.filename AS key, l.heiti AS title,
                      ('nr. ' || COALESCE(l.law_nr,'?') || '/' || COALESCE(l.year,0)) AS sub,
                      snippet(laws_fts, 2, '[', ']', ' ... ', 12) AS snip, bm25(laws_fts) AS rank
               FROM laws_fts JOIN laws l ON l.filename = laws_fts.filename
               WHERE laws_fts MATCH ? ORDER BY rank LIMIT ?""",
            (query, args.limit),
        ).fetchall()
        results += [("log", r) for r in rows]

    if args.type in ("allt", "reglugerd"):
        rows = conn.execute(
            """SELECT r.name AS key, r.title AS title,
                      (COALESCE(r.ministry,'') || '  ' || COALESCE(r.published_date,'')) AS sub,
                      snippet(regulations_fts, 2, '[', ']', ' ... ', 12) AS snip, bm25(regulations_fts) AS rank
               FROM regulations_fts JOIN regulations r ON r.name = regulations_fts.name
               WHERE regulations_fts MATCH ? ORDER BY rank LIMIT ?""",
            (query, args.limit),
        ).fetchall()
        results += [("reglugerð", r) for r in rows]

    if args.type in ("allt", "domur"):
        rows = conn.execute(
            """SELECT c.id AS key, c.title AS title,
                      (COALESCE(c.court,'') || '  ' || COALESCE(c.case_number,'') || '  ' || COALESCE(c.verdict_date,'')) AS sub,
                      snippet(court_cases_fts, 3, '[', ']', ' ... ', 12) AS snip, bm25(court_cases_fts) AS rank
               FROM court_cases_fts JOIN court_cases c ON c.id = court_cases_fts.id
               WHERE court_cases_fts MATCH ? ORDER BY rank LIMIT ?""",
            (query, args.limit),
        ).fetchall()
        results += [("dómur", r) for r in rows]

    if args.type in ("allt", "thingmadur"):
        rows = conn.execute(
            """SELECT t.id AS key, t.nafn AS title, COALESCE(t.faedingardagur,'') AS sub,
                      snippet(thingmenn_fts, 2, '[', ']', ' ... ', 12) AS snip, bm25(thingmenn_fts) AS rank
               FROM thingmenn_fts JOIN thingmenn t ON t.id = thingmenn_fts.id
               WHERE thingmenn_fts MATCH ? ORDER BY rank LIMIT ?""",
            (query, args.limit),
        ).fetchall()
        results += [("þingmaður", r) for r in rows]

    if args.type in ("allt", "alyktun"):
        rows = conn.execute(
            """SELECT a.id AS key, a.heiti AS title,
                      ('þing ' || COALESCE(a.thing,'?') || '  ' || COALESCE(a.efnisflokkar,'')) AS sub,
                      snippet(alyktanir_fts, 3, '[', ']', ' ... ', 12) AS snip, bm25(alyktanir_fts) AS rank
               FROM alyktanir_fts JOIN alyktanir a ON a.id = alyktanir_fts.id
               WHERE alyktanir_fts MATCH ? ORDER BY rank LIMIT ?""",
            (query, args.limit),
        ).fetchall()
        results += [("ályktun", r) for r in rows]

    if not results:
        print("Ekkert fannst.")
        return

    for kind, r in results:
        title = r["title"] or "(heiti vantar)"
        print(f"\n[{kind}] {title}")
        print(f"  {r['sub']}   ({r['key']})")
        snip = (r["snip"] or "").strip()
        if snip:
            print("  " + textwrap.shorten(snip, width=220, placeholder=" ..."))
    print(f"\n({len(results)} niðurstöður)")


def cmd_log(args):
    conn = connect()
    row = conn.execute("SELECT * FROM laws WHERE filename = ?", (args.filename,)).fetchone()
    if not row:
        sys.exit(f"Lög '{args.filename}' fundust ekki.")
    print(f"Heiti:      {row['heiti']}")
    print(f"Lög nr.:    {row['law_nr']} / {row['year']}  ({row['nr_date']})")
    print(f"Gildi tók:  {row['effective']}")
    print(f"Vefslóð:    https://www.althingi.is/lagas/nuna/{row['filename']}")
    print(f"PDF:        {row['pdf_url']}")
    print(f"Skrá:       {row['filename']}")

    chs = conn.execute(
        "SELECT chapter_no, sub_code, sub_name FROM law_chapters WHERE filename = ?",
        (args.filename,),
    ).fetchall()
    if chs:
        print("Kaflar:")
        for c in chs:
            print(f"  - {c['chapter_no']}  {c['sub_code'] or ''}  {c['sub_name'] or ''}")

    n_am = conn.execute(
        "SELECT COUNT(*) FROM law_amendments WHERE filename = ?", (args.filename,)
    ).fetchone()[0]
    print(f"Breytingar: {n_am}  (sjá: python3 search.py breytingar {args.filename})")

    if args.full:
        print("\n--- Fullur texti ---\n")
        print(row["body_text"])


def cmd_breytingar(args):
    conn = connect()
    row = conn.execute("SELECT heiti, law_nr, year FROM laws WHERE filename = ?", (args.filename,)).fetchone()
    if not row:
        sys.exit(f"Lög '{args.filename}' fundust ekki.")
    print(f"{row['heiti']}  (nr. {row['law_nr']}/{row['year']})")

    rows = conn.execute(
        """SELECT amend_ref, amend_law_nr, amend_year, amend_note, amend_url
           FROM law_amendments WHERE filename = ? ORDER BY amend_year, amend_law_nr""",
        (args.filename,),
    ).fetchall()

    if not rows:
        print("Engar skráðar breytingar fundust.")
        return

    print(f"\n{len(rows)} breyting(ar):")
    for r in rows:
        print(f"  - {r['amend_ref']}  ({r['amend_note']})")
        if r["amend_url"]:
            print(f"      {r['amend_url']}")


def cmd_reglugerd(args):
    conn = connect()
    row = conn.execute("SELECT * FROM regulations WHERE name = ?", (args.name,)).fetchone()
    if not row:
        sys.exit(f"Reglugerð '{args.name}' fannst ekki.")
    print(f"Heiti:      {row['title']}")
    print(f"Nr.:        {row['name']}")
    print(f"Útgefin:    {row['published_date']}")
    print(f"Ráðuneyti:  {row['ministry']}")
    print(f"Vefslóð:    {row['url']}")
    if args.full:
        print("\n--- Fullur texti ---\n")
        print(row["body_text"])


def cmd_domur(args):
    conn = connect()
    row = conn.execute("SELECT * FROM court_cases WHERE id = ?", (args.id,)).fetchone()
    if not row:
        sys.exit(f"Dómur '{args.id}' fannst ekki.")
    print(f"Heiti:       {row['title']}")
    print(f"Dómstóll:    {row['court']}")
    print(f"Málsnúmer:   {row['case_number']}")
    print(f"Dagsetning:  {row['verdict_date']}")
    print(f"Lykilorð:    {row['keywords']}")
    print(f"Vefslóð:     {row['url']}")
    if row["presentings"]:
        print(f"\nÁgrip:\n{row['presentings']}")
    if args.full:
        print("\n--- Fullur texti ---\n")
        print(row["full_text"])


def cmd_thingmadur(args):
    conn = connect()
    row = conn.execute("SELECT * FROM thingmenn WHERE id = ?", (args.id,)).fetchone()
    if not row:
        sys.exit(f"Þingmaður '{args.id}' fannst ekki.")
    print(f"Nafn:            {row['nafn']}")
    print(f"Fæðingardagur:   {row['faedingardagur']}")

    thingseta = conn.execute(
        """SELECT thing, tegund, thingflokkur, kjordaemi, inn, ut
           FROM thingmenn_thingseta WHERE thingmadur_id = ? ORDER BY thing""",
        (args.id,),
    ).fetchall()
    if thingseta:
        print(f"Þingseta ({len(thingseta)}):")
        for t in thingseta:
            print(f"  - þing {t['thing']}  {t['tegund'] or ''}  {t['thingflokkur'] or ''}  {t['kjordaemi'] or ''}  ({t['inn'] or '?'} - {t['ut'] or '?'})")

    nefndaseta = conn.execute(
        "SELECT nefnd, hlutverk, thing FROM thingmenn_nefndaseta WHERE thingmadur_id = ? ORDER BY thing",
        (args.id,),
    ).fetchall()
    if nefndaseta:
        print(f"Nefndaseta ({len(nefndaseta)}):")
        for n in nefndaseta:
            print(f"  - þing {n['thing']}  {n['nefnd']}  {n['hlutverk'] or ''}")

    if args.full and row["lifshlaup_text"]:
        print("\n--- Æviágrip ---\n")
        print(row["lifshlaup_text"])


def cmd_alyktun(args):
    conn = connect()
    row = conn.execute("SELECT * FROM alyktanir WHERE id = ?", (args.id,)).fetchone()
    if not row:
        sys.exit(f"Ályktun '{args.id}' fannst ekki.")
    print(f"Heiti:         {row['heiti']}")
    print(f"Þing/mál:      {row['thing']} / {row['malnr']}")
    print(f"Staða:         {row['stada']}")
    print(f"Efnisflokkar:  {row['efnisflokkar']}")
    print(f"Vefslóð:       {row['url']}")
    if args.full:
        print("\n--- Fullur texti ---\n")
        print(row["full_text"])


def main():
    p = argparse.ArgumentParser(description="Leit í gagnasafn.db (lög + reglugerðir + dómar)")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_leit = sub.add_parser("leit", help="Fulltextaleit (FTS5 setningafræði, t.d. 'innheimt* skuld*')")
    p_leit.add_argument("query")
    p_leit.add_argument("--type", choices=["allt", "log", "reglugerd", "domur", "thingmadur", "alyktun"], default="allt")
    p_leit.add_argument("--limit", type=int, default=10)
    p_leit.set_defaults(func=cmd_leit)

    p_log = sub.add_parser("log", help="Sýna metadata fyrir eitt lög")
    p_log.add_argument("filename")
    p_log.add_argument("--full", action="store_true")
    p_log.set_defaults(func=cmd_log)

    p_br = sub.add_parser("breytingar", help="Sýna breytingasögu fyrir eitt lög")
    p_br.add_argument("filename")
    p_br.set_defaults(func=cmd_breytingar)

    p_reg = sub.add_parser("reglugerd", help="Sýna eina reglugerð")
    p_reg.add_argument("name")
    p_reg.add_argument("--full", action="store_true")
    p_reg.set_defaults(func=cmd_reglugerd)

    p_dom = sub.add_parser("domur", help="Sýna einn dóm")
    p_dom.add_argument("id")
    p_dom.add_argument("--full", action="store_true")
    p_dom.set_defaults(func=cmd_domur)

    p_tm = sub.add_parser("thingmadur", help="Sýna einn þingmann")
    p_tm.add_argument("id")
    p_tm.add_argument("--full", action="store_true")
    p_tm.set_defaults(func=cmd_thingmadur)

    p_aly = sub.add_parser("alyktun", help="Sýna eina þingsályktun")
    p_aly.add_argument("id")
    p_aly.add_argument("--full", action="store_true")
    p_aly.set_defaults(func=cmd_alyktun)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
