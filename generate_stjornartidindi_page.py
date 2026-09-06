#!/usr/bin/env python3
"""Saekir nyjustu ROI-fraedslu (RSS) fra Stjornartidindum (A/B/C-deild) og
byggir sjalfstaeda HTML-sidu ur henni.

Notkun:
    python3 generate_stjornartidindi_page.py
"""
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_JSON = HERE / "artifacts" / "stjornartidindi_data.json"
OUT_HTML = HERE / "artifacts" / "stjornartidindi.html"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def load_data():
    all_items = []
    for deild in ["a-deild", "b-deild", "c-deild"]:
        raw = fetch(f"https://api.stjornartidindi.is/api/v1/rss/{deild}")
        root = ET.fromstring(raw)
        for item in root.findall(".//item"):
            title = item.findtext("title") or ""
            m = re.search(r"(\d+)/(\d+)", title)
            nr = m.group(1) if m else None
            ar = m.group(2) if m else None
            all_items.append({
                "deild": deild[0].upper(),
                "nr": nr,
                "ar": ar,
                "titill": (item.findtext("description") or "").strip(),
                "dagsetning": item.findtext("pubDate"),
                "slod": item.findtext("link"),
            })
    all_items.sort(key=lambda x: x["dagsetning"], reverse=True)
    OUT_JSON.write_text(json.dumps(all_items, ensure_ascii=False, indent=1), encoding="utf-8")
    return all_items


TEMPLATE = """<title>Stjórnartíðindavaktin</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=Public+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root {{
  --paper: #eef0f3;
  --paper-raised: #ffffff;
  --ink: #171a21;
  --ink-soft: #383d49;
  --muted: #5b6270;
  --rule: #d3d6dc;
  --rule-strong: #b7bbc4;
  --a-accent: #2851a3;
  --a-tint: #e3eaf7;
  --b-accent: #a3660a;
  --b-tint: #f6ecda;
  --c-accent: #167468;
  --c-tint: #dcf0ec;
  --focus: #2851a3;
  --shadow: 0 1px 2px rgba(23,26,33,0.06), 0 8px 24px -12px rgba(23,26,33,0.18);
}}

@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --paper: #14161c;
    --paper-raised: #1c1f28;
    --ink: #e9eaee;
    --ink-soft: #c7cad3;
    --muted: #9297a4;
    --rule: #2b2f3a;
    --rule-strong: #3a3f4d;
    --a-accent: #7fa4e8;
    --a-tint: #1e2a42;
    --b-accent: #e0a84f;
    --b-tint: #3a2e18;
    --c-accent: #5cc2b0;
    --c-tint: #163531;
    --focus: #7fa4e8;
    --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 8px 24px -12px rgba(0,0,0,0.5);
  }}
}}

:root[data-theme="dark"] {{
  --paper: #14161c;
  --paper-raised: #1c1f28;
  --ink: #e9eaee;
  --ink-soft: #c7cad3;
  --muted: #9297a4;
  --rule: #2b2f3a;
  --rule-strong: #3a3f4d;
  --a-accent: #7fa4e8;
  --a-tint: #1e2a42;
  --b-accent: #e0a84f;
  --b-tint: #3a2e18;
  --c-accent: #5cc2b0;
  --c-tint: #163531;
  --focus: #7fa4e8;
  --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 8px 24px -12px rgba(0,0,0,0.5);
}}

* {{ box-sizing: border-box; }}

body {{
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: "Public Sans", system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
}}

.masthead {{
  border-bottom: 1px solid var(--rule-strong);
  padding: 2rem 1.5rem 1.25rem;
  background: var(--paper-raised);
}}

.masthead-inner {{
  max-width: 76rem;
  margin: 0 auto;
}}

.eyebrow {{
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
  margin: 0 0 0.4rem;
}}

h1 {{
  font-family: "Newsreader", Georgia, serif;
  font-weight: 600;
  font-size: clamp(1.9rem, 3.4vw, 2.6rem);
  margin: 0 0 0.35rem;
  text-wrap: balance;
  letter-spacing: -0.01em;
}}

.subhead {{
  color: var(--muted);
  font-size: 0.98rem;
  margin: 0 0 1.4rem;
  max-width: 42rem;
  line-height: 1.5;
}}

.controls {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  align-items: center;
}}

.search-wrap {{
  position: relative;
  flex: 1 1 18rem;
  min-width: 14rem;
}}

.search-wrap svg {{
  position: absolute;
  left: 0.85rem;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  stroke: var(--muted);
  pointer-events: none;
}}

#search {{
  width: 100%;
  font: inherit;
  font-size: 0.95rem;
  padding: 0.65rem 0.9rem 0.65rem 2.5rem;
  border-radius: 8px;
  border: 1px solid var(--rule-strong);
  background: var(--paper);
  color: var(--ink);
}}

#search:focus-visible {{
  outline: 2px solid var(--focus);
  outline-offset: 1px;
}}

.filters {{
  display: flex;
  gap: 0.4rem;
}}

.filter-chip {{
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.78rem;
  letter-spacing: 0.04em;
  padding: 0.55rem 0.85rem;
  border-radius: 999px;
  border: 1px solid var(--rule-strong);
  background: var(--paper);
  color: var(--ink-soft);
  cursor: pointer;
  transition: background 0.12s ease, color 0.12s ease, border-color 0.12s ease;
}}

.filter-chip:focus-visible {{ outline: 2px solid var(--focus); outline-offset: 1px; }}

.filter-chip[data-active="true"][data-deild="A"] {{ background: var(--a-tint); border-color: var(--a-accent); color: var(--a-accent); }}
.filter-chip[data-active="true"][data-deild="B"] {{ background: var(--b-tint); border-color: var(--b-accent); color: var(--b-accent); }}
.filter-chip[data-active="true"][data-deild="C"] {{ background: var(--c-tint); border-color: var(--c-accent); color: var(--c-accent); }}
.filter-chip[data-active="true"][data-deild="ALL"] {{ background: var(--ink); border-color: var(--ink); color: var(--paper); }}

main {{
  max-width: 76rem;
  margin: 0 auto;
  padding: 1.75rem 1.5rem 4rem;
}}

.day-group {{ margin-bottom: 2.1rem; }}

.day-heading {{
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  margin: 0 0 0.7rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid var(--rule);
}}

.day-heading .date {{
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.85rem;
  color: var(--muted);
  letter-spacing: 0.02em;
}}

.day-heading .count {{
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.72rem;
  color: var(--muted);
}}

.entries {{
  display: grid;
  gap: 0.55rem;
}}

.entry {{
  display: grid;
  grid-template-columns: 6.2rem 1fr;
  gap: 0.9rem;
  align-items: start;
  padding: 0.75rem 0.9rem;
  border-radius: 10px;
  background: var(--paper-raised);
  border: 1px solid var(--rule);
  text-decoration: none;
  color: inherit;
  transition: box-shadow 0.12s ease, border-color 0.12s ease, transform 0.12s ease;
}}

.entry:hover {{
  box-shadow: var(--shadow);
  border-color: var(--rule-strong);
  transform: translateY(-1px);
}}

.entry:focus-visible {{
  outline: 2px solid var(--focus);
  outline-offset: 2px;
}}

.tag {{
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.74rem;
  font-weight: 500;
  padding: 0.2rem 0.5rem;
  border-radius: 5px;
  white-space: nowrap;
  justify-self: start;
  line-height: 1.5;
}}

.tag[data-deild="A"] {{ background: var(--a-tint); color: var(--a-accent); }}
.tag[data-deild="B"] {{ background: var(--b-tint); color: var(--b-accent); }}
.tag[data-deild="C"] {{ background: var(--c-tint); color: var(--c-accent); }}

.entry-title {{
  font-family: "Newsreader", Georgia, serif;
  font-size: 1.02rem;
  line-height: 1.42;
  color: var(--ink);
}}

.entry-time {{
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.7rem;
  color: var(--muted);
  margin-top: 0.3rem;
  font-variant-numeric: tabular-nums;
}}

.empty {{
  text-align: center;
  color: var(--muted);
  padding: 3rem 1rem;
  font-size: 0.95rem;
}}

.legend {{
  display: flex;
  gap: 1.1rem;
  margin-top: 1rem;
  font-size: 0.78rem;
  color: var(--muted);
  flex-wrap: wrap;
}}

.legend span {{ display: inline-flex; align-items: center; gap: 0.35rem; }}

.legend i {{
  width: 8px; height: 8px; border-radius: 2px; display: inline-block;
}}

.legend i.a {{ background: var(--a-accent); }}
.legend i.b {{ background: var(--b-accent); }}
.legend i.c {{ background: var(--c-accent); }}

@media (max-width: 40rem) {{
  .entry {{ grid-template-columns: 1fr; gap: 0.4rem; }}
  .tag {{ justify-self: start; }}
}}
</style>

<header class="masthead">
  <div class="masthead-inner">
    <p class="eyebrow">Stjórnartíðindi &middot; A &middot; B &middot; C-deild</p>
    <h1>Stjórnartíðindavaktin</h1>
    <p class="subhead">Nýjustu lög, reglugerðir og þjóðréttarsamningar sem birt hafa verið í Stjórnartíðindum, teknar beint af opinberu RSS-veitunum. Leitaðu eða síaðu eftir deild til að finna það sem skiptir máli hverju sinni.</p>
    <div class="controls">
      <div class="search-wrap">
        <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input id="search" type="text" placeholder="Leita — t.d. „reglugerð“, „fjárlög“, „samningur“…" autocomplete="off">
      </div>
      <div class="filters" role="group" aria-label="Sía eftir deild">
        <button class="filter-chip" data-deild="ALL" data-active="true">Allt</button>
        <button class="filter-chip" data-deild="A" data-active="false">A · lög</button>
        <button class="filter-chip" data-deild="B" data-active="false">B · reglugerðir</button>
        <button class="filter-chip" data-deild="C" data-active="false">C · samningar</button>
      </div>
    </div>
    <div class="legend">
      <span><i class="a"></i>A-deild: lög, forsetabréf, auglýsingar Alþingis</span>
      <span><i class="b"></i>B-deild: reglugerðir, samþykktir sveitarfélaga</span>
      <span><i class="c"></i>C-deild: þjóðréttarsamningar</span>
    </div>
  </div>
</header>

<main id="main"></main>

<script>
const DATA = {data_json};

const ICELANDIC_MONTHS = ["janúar","febrúar","mars","apríl","maí","júní","júlí","ágúst","september","október","nóvember","desember"];
const ICELANDIC_DAYS = ["sunnudagur","mánudagur","þriðjudagur","miðvikudagur","fimmtudagur","föstudagur","laugardagur"];

function fmtDay(d) {{
  return `${{ICELANDIC_DAYS[d.getDay()]}} ${{d.getDate()}}. ${{ICELANDIC_MONTHS[d.getMonth()]}} ${{d.getFullYear()}}`;
}}
function fmtTime(d) {{
  return d.toLocaleTimeString("is-IS", {{hour: "2-digit", minute: "2-digit"}});
}}
function dayKey(d) {{
  return `${{d.getFullYear()}}-${{d.getMonth()}}-${{d.getDate()}}`;
}}

const DEILD_LABEL = {{A: "A-deild", B: "B-deild", C: "C-deild"}};

let activeDeild = "ALL";
let query = "";

function render() {{
  const main = document.getElementById("main");
  const q = query.trim().toLowerCase();
  const filtered = DATA.filter(item => {{
    if (activeDeild !== "ALL" && item.deild !== activeDeild) return false;
    if (!q) return true;
    return item.titill.toLowerCase().includes(q) || (item.nr || "").includes(q) || (item.ar || "").includes(q);
  }});

  if (filtered.length === 0) {{
    main.innerHTML = '<p class="empty">Ekkert fannst. Prófaðu annað leitarorð eða aðra deild.</p>';
    return;
  }}

  const groups = new Map();
  for (const item of filtered) {{
    const d = new Date(item.dagsetning);
    const key = dayKey(d);
    if (!groups.has(key)) groups.set(key, {{ date: d, items: [] }});
    groups.get(key).items.push({{ ...item, _date: d }});
  }}

  let html = "";
  for (const {{ date, items }} of groups.values()) {{
    html += `<section class="day-group">`;
    html += `<div class="day-heading"><span class="date">${{fmtDay(date)}}</span><span class="count">${{items.length}} atriði</span></div>`;
    html += `<div class="entries">`;
    for (const item of items) {{
      html += `<a class="entry" href="${{item.slod}}" target="_blank" rel="noopener">`;
      html += `<span class="tag" data-deild="${{item.deild}}">${{DEILD_LABEL[item.deild]}} ${{item.nr || ""}}/${{item.ar || ""}}</span>`;
      html += `<span><span class="entry-title">${{item.titill}}</span><div class="entry-time">${{fmtTime(item._date)}}</div></span>`;
      html += `</a>`;
    }}
    html += `</div></section>`;
  }}
  main.innerHTML = html;
}}

document.getElementById("search").addEventListener("input", e => {{ query = e.target.value; render(); }});
document.querySelectorAll(".filter-chip").forEach(btn => {{
  btn.addEventListener("click", () => {{
    activeDeild = btn.dataset.deild;
    document.querySelectorAll(".filter-chip").forEach(b => b.dataset.active = (b === btn) ? "true" : "false");
    render();
  }});
}});

render();
</script>
"""


def main():
    items = load_data()
    html = TEMPLATE.format(data_json=json.dumps(items, ensure_ascii=False))
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"{len(items)} atriði skrifuð í {OUT_HTML}")


if __name__ == "__main__":
    main()
