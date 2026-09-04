#!/usr/bin/env bash
# skjalasokn - stutt utgafa
set -uo pipefail
[ "$#" -lt 2 ] && { echo "Notkun: $0 <thing> <skjal...>"; exit 2; }
T="$1"; shift; mkdir -p skjol
for N in "$@"; do
  P=$(printf "%04d" "$N")
  U="https://www.althingi.is/altext/$T/s/$P.html"
  echo "-> $N"
  curl -sSL --compressed -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36" \
       --max-time 45 "$U" -o /tmp/_s.html || { echo "   ! nadi ekki"; continue; }
  python3 - "$T" "$P" "$U" <<'PYEOF'
import io,re,sys
from html import unescape
t,p,u=sys.argv[1],sys.argv[2],sys.argv[3]
h=io.open("/tmp/_s.html",encoding="utf-8",errors="replace").read()
m=re.split(r'<div[^>]*(?:class|id)="[^"]*pgmain[^"]*"[^>]*>',h,maxsplit=1)
h=m[1] if len(m)>1 else h
for tag in ("script","style","head","nav","footer","form","select"):
    h=re.sub(r"<%s\b[^>]*>.*?</%s>"%(tag,tag),u" ",h,flags=re.S|re.I)
h=re.sub(r"</?(?:p|div|br|tr|li|h[1-6]|table|section|article|blockquote)\b[^>]*>",u"\n",h,flags=re.I)
h=re.sub(r"</?(?:td|th|span|a|b|i|em|strong)\b[^>]*>",u" ",h,flags=re.I)
h=unescape(re.sub(r"<[^>]+>",u" ",h))
h=re.sub(r"[^\S\r\n]+",u" ",h)
ls=[x.strip() for x in h.split(u"\n")]
out=[];z=0
for x in ls:
    if not x:
        z+=1
        if z>1: continue
    else: z=0
    out.append(x)
txt=u"\n".join(out).strip()
for s in (u"\u00de\u00fa ert h\u00e9r:",u"Skrifstofa Al\u00feingis",u"Deila"):
    i=txt.find(s)
    if i>60: txt=txt[:i].rstrip()
io.open("skjol/%s-%s.md"%(t,p),"w",encoding="utf-8").write(
    u"# \u00deingskjal %s, %s. l\u00f6ggjafar\u00feing\n\nHeimild: %s\n\n---\n\n%s\n"%(int(p),t,u,txt))
print("   . skjol/%s-%s.md"%(t,p))
PYEOF
  sleep 2
done
git add skjol && git commit -q -m "thingskjol $T: $*" && git push -q && echo "Ytt i origin."

