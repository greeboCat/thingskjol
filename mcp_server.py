#!/usr/bin/env python3
"""MCP-tjonn sem opnar gagnasafn.db (log, reglugerdir, domar) fyrir onnur
AI-tol (Claude Desktop, Claude Code, o.fl.) an thess ad fara i gegnum CLI.

Keyrsla (staedla stdio flutning):
    .venv/bin/python3 mcp_server.py

Uppsetning i Claude Code / Claude Desktop mcp stillingum, t.d.:
    {
      "mcpServers": {
        "gagnasafn": {
          "command": "/home/gunnar/thingskjol/.venv/bin/python3",
          "args": ["/home/gunnar/thingskjol/mcp_server.py"]
        }
      }
    }
"""
import sqlite3
import textwrap
from pathlib import Path

from mcp.server.fastmcp import FastMCP

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "gagnasafn.db"

mcp = FastMCP("gagnasafn")


def connect():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


@mcp.tool()
def leit(fyrirspurn: str, tegund: str = "allt", limit: int = 10) -> str:
    """Fulltextaleit í íslenska lagasafninu (lög, reglugerðir, dómar).

    Args:
        fyrirspurn: FTS5 leitarstrengur, t.d. "árangurslaust fjárnám" eða "innheimt* skuld*"
        tegund: "allt", "log", "reglugerd", "domur", "thingmadur", eða "alyktun"
        limit: hámarksfjöldi niðurstaðna per tegund
    """
    conn = connect()
    out = []

    if tegund in ("allt", "log"):
        rows = conn.execute(
            """SELECT l.filename AS key, l.heiti AS title,
                      ('nr. ' || COALESCE(l.law_nr,'?') || '/' || COALESCE(l.year,0)) AS sub,
                      snippet(laws_fts, 2, '[', ']', ' ... ', 12) AS snip, bm25(laws_fts) AS rank
               FROM laws_fts JOIN laws l ON l.filename = laws_fts.filename
               WHERE laws_fts MATCH ? ORDER BY rank LIMIT ?""",
            (fyrirspurn, limit),
        ).fetchall()
        for r in rows:
            out.append(f"[log] {r['title']}\n  {r['sub']}  ({r['key']})\n  {textwrap.shorten(r['snip'] or '', 220)}")

    if tegund in ("allt", "reglugerd"):
        rows = conn.execute(
            """SELECT r.name AS key, r.title AS title,
                      (COALESCE(r.ministry,'') || '  ' || COALESCE(r.published_date,'')) AS sub,
                      snippet(regulations_fts, 2, '[', ']', ' ... ', 12) AS snip, bm25(regulations_fts) AS rank
               FROM regulations_fts JOIN regulations r ON r.name = regulations_fts.name
               WHERE regulations_fts MATCH ? ORDER BY rank LIMIT ?""",
            (fyrirspurn, limit),
        ).fetchall()
        for r in rows:
            out.append(f"[reglugerð] {r['title']}\n  {r['sub']}  ({r['key']})\n  {textwrap.shorten(r['snip'] or '', 220)}")

    if tegund in ("allt", "domur"):
        rows = conn.execute(
            """SELECT c.id AS key, c.title AS title,
                      (COALESCE(c.court,'') || '  ' || COALESCE(c.case_number,'') || '  ' || COALESCE(c.verdict_date,'')) AS sub,
                      snippet(court_cases_fts, 3, '[', ']', ' ... ', 12) AS snip, bm25(court_cases_fts) AS rank
               FROM court_cases_fts JOIN court_cases c ON c.id = court_cases_fts.id
               WHERE court_cases_fts MATCH ? ORDER BY rank LIMIT ?""",
            (fyrirspurn, limit),
        ).fetchall()
        for r in rows:
            out.append(f"[dómur] {r['title']}\n  {r['sub']}  ({r['key']})\n  {textwrap.shorten(r['snip'] or '', 220)}")

    if tegund in ("allt", "thingmadur"):
        rows = conn.execute(
            """SELECT t.id AS key, t.nafn AS title, COALESCE(t.faedingardagur,'') AS sub,
                      snippet(thingmenn_fts, 2, '[', ']', ' ... ', 12) AS snip, bm25(thingmenn_fts) AS rank
               FROM thingmenn_fts JOIN thingmenn t ON t.id = thingmenn_fts.id
               WHERE thingmenn_fts MATCH ? ORDER BY rank LIMIT ?""",
            (fyrirspurn, limit),
        ).fetchall()
        for r in rows:
            out.append(f"[þingmaður] {r['title']}\n  {r['sub']}  ({r['key']})\n  {textwrap.shorten(r['snip'] or '', 220)}")

    if tegund in ("allt", "alyktun"):
        rows = conn.execute(
            """SELECT a.id AS key, a.heiti AS title,
                      ('þing ' || COALESCE(a.thing,'?') || '  ' || COALESCE(a.efnisflokkar,'')) AS sub,
                      snippet(alyktanir_fts, 3, '[', ']', ' ... ', 12) AS snip, bm25(alyktanir_fts) AS rank
               FROM alyktanir_fts JOIN alyktanir a ON a.id = alyktanir_fts.id
               WHERE alyktanir_fts MATCH ? ORDER BY rank LIMIT ?""",
            (fyrirspurn, limit),
        ).fetchall()
        for r in rows:
            out.append(f"[ályktun] {r['title']}\n  {r['sub']}  ({r['key']})\n  {textwrap.shorten(r['snip'] or '', 220)}")

    conn.close()
    return "\n\n".join(out) if out else "Ekkert fannst."


@mcp.tool()
def syna_log(skra: str, fullur_texti: bool = False) -> str:
    """Sýnir metadata (og valfrjálst fullan texta) fyrir eitt lög.

    Args:
        skra: skráarnafn lagans, t.d. "1989090.html"
        fullur_texti: ef satt, skilar einnig öllum texta laganna
    """
    conn = connect()
    row = conn.execute("SELECT * FROM laws WHERE filename = ?", (skra,)).fetchone()
    conn.close()
    if not row:
        return f"Lög '{skra}' fundust ekki."
    out = [
        f"Heiti: {row['heiti']}",
        f"Lög nr.: {row['law_nr']} / {row['year']} ({row['nr_date']})",
        f"Gildi tók: {row['effective']}",
        f"Vefslóð: https://www.althingi.is/lagas/nuna/{row['filename']}",
        f"PDF: {row['pdf_url']}",
    ]
    if fullur_texti:
        out.append("\n--- Fullur texti ---\n" + row["body_text"])
    return "\n".join(out)


@mcp.tool()
def breytingar_a_logum(skra: str) -> str:
    """Sýnir breytingasögu (hvaða lög breyttu þessum lögum, hvenær) fyrir eitt lög.

    Args:
        skra: skráarnafn lagans, t.d. "1989090.html"
    """
    conn = connect()
    row = conn.execute("SELECT heiti, law_nr, year FROM laws WHERE filename = ?", (skra,)).fetchone()
    if not row:
        conn.close()
        return f"Lög '{skra}' fundust ekki."
    rows = conn.execute(
        """SELECT amend_ref, amend_note, amend_url FROM law_amendments
           WHERE filename = ? ORDER BY amend_year, amend_law_nr""",
        (skra,),
    ).fetchall()
    conn.close()
    if not rows:
        return f"{row['heiti']} (nr. {row['law_nr']}/{row['year']}): engar skráðar breytingar."
    lines = [f"{row['heiti']} (nr. {row['law_nr']}/{row['year']}) — {len(rows)} breyting(ar):"]
    for r in rows:
        lines.append(f"  - {r['amend_ref']} ({r['amend_note']}) {r['amend_url'] or ''}")
    return "\n".join(lines)


@mcp.tool()
def syna_reglugerd(nafn: str, fullur_texti: bool = False) -> str:
    """Sýnir metadata (og valfrjálst fullan texta) fyrir eina reglugerð.

    Args:
        nafn: heiti reglugerðar í forminu "0017-1992"
        fullur_texti: ef satt, skilar einnig öllum texta reglugerðarinnar
    """
    conn = connect()
    row = conn.execute("SELECT * FROM regulations WHERE name = ?", (nafn,)).fetchone()
    conn.close()
    if not row:
        return f"Reglugerð '{nafn}' fannst ekki."
    out = [
        f"Heiti: {row['title']}",
        f"Nr.: {row['name']}",
        f"Útgefin: {row['published_date']}",
        f"Ráðuneyti: {row['ministry']}",
        f"Vefslóð: {row['url']}",
    ]
    if fullur_texti:
        out.append("\n--- Fullur texti ---\n" + row["body_text"])
    return "\n".join(out)


@mcp.tool()
def syna_dom(id: str, fullur_texti: bool = False) -> str:
    """Sýnir metadata (og valfrjálst fullan texta) fyrir einn dóm.

    Args:
        id: auðkenni dóms, t.d. "g-c1aeae01-303d-4da6-8795-0bacca267ed1"
        fullur_texti: ef satt, skilar einnig öllum texta dómsins
    """
    conn = connect()
    row = conn.execute("SELECT * FROM court_cases WHERE id = ?", (id,)).fetchone()
    conn.close()
    if not row:
        return f"Dómur '{id}' fannst ekki."
    out = [
        f"Heiti: {row['title']}",
        f"Dómstóll: {row['court']}",
        f"Málsnúmer: {row['case_number']}",
        f"Dagsetning: {row['verdict_date']}",
        f"Lykilorð: {row['keywords']}",
        f"Vefslóð: {row['url']}",
    ]
    if row["presentings"]:
        out.append(f"Ágrip: {row['presentings']}")
    if fullur_texti:
        out.append("\n--- Fullur texti ---\n" + row["full_text"])
    return "\n".join(out)


@mcp.tool()
def syna_thingmann(id: str, fullur_texti: bool = False) -> str:
    """Sýnir metadata (þingseta, nefndaseta, og valfrjálst æviágrip) fyrir einn þingmann.

    Args:
        id: auðkenni þingmanns, t.d. "1347"
        fullur_texti: ef satt, skilar einnig æviágripi
    """
    conn = connect()
    row = conn.execute("SELECT * FROM thingmenn WHERE id = ?", (id,)).fetchone()
    if not row:
        conn.close()
        return f"Þingmaður '{id}' fannst ekki."
    out = [f"Nafn: {row['nafn']}", f"Fæðingardagur: {row['faedingardagur']}"]

    thingseta = conn.execute(
        """SELECT thing, tegund, thingflokkur, kjordaemi, inn, ut
           FROM thingmenn_thingseta WHERE thingmadur_id = ? ORDER BY thing""",
        (id,),
    ).fetchall()
    if thingseta:
        out.append(f"Þingseta ({len(thingseta)}):")
        for t in thingseta:
            out.append(f"  - þing {t['thing']}  {t['tegund'] or ''}  {t['thingflokkur'] or ''}  {t['kjordaemi'] or ''}  ({t['inn'] or '?'} - {t['ut'] or '?'})")

    nefndaseta = conn.execute(
        "SELECT nefnd, hlutverk, thing FROM thingmenn_nefndaseta WHERE thingmadur_id = ? ORDER BY thing",
        (id,),
    ).fetchall()
    if nefndaseta:
        out.append(f"Nefndaseta ({len(nefndaseta)}):")
        for n in nefndaseta:
            out.append(f"  - þing {n['thing']}  {n['nefnd']}  {n['hlutverk'] or ''}")

    if fullur_texti and row["lifshlaup_text"]:
        out.append("\n--- Æviágrip ---\n" + row["lifshlaup_text"])
    conn.close()
    return "\n".join(out)


@mcp.tool()
def syna_alyktun(id: str, fullur_texti: bool = False) -> str:
    """Sýnir metadata (og valfrjálst fullan texta) fyrir eina samþykkta þingsályktun.

    Args:
        id: auðkenni ályktunar á forminu "<þing>-<málnúmer>", t.d. "141-567"
        fullur_texti: ef satt, skilar einnig öllum texta ályktunarinnar
    """
    conn = connect()
    row = conn.execute("SELECT * FROM alyktanir WHERE id = ?", (id,)).fetchone()
    conn.close()
    if not row:
        return f"Ályktun '{id}' fannst ekki."
    out = [
        f"Heiti: {row['heiti']}",
        f"Þing/mál: {row['thing']} / {row['malnr']}",
        f"Staða: {row['stada']}",
        f"Efnisflokkar: {row['efnisflokkar']}",
        f"Vefslóð: {row['url']}",
    ]
    if fullur_texti:
        out.append("\n--- Fullur texti ---\n" + row["full_text"])
    return "\n".join(out)


if __name__ == "__main__":
    mcp.run()
