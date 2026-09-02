#!/usr/bin/env bash
#
# skjalasokn.sh - sækir þingskjöl af althingi.is og ýtir þeim í GitHub-geymslu
#                 svo að Claude geti lesið þau af raw.githubusercontent.com
#
# Notkun:
#   ./skjalasokn.sh 156 315              # eitt skjal
#   ./skjalasokn.sh 156 315 316 317      # mörg skjöl af sama þingi
#   ./skjalasokn.sh 157 611 620 1426     # o.s.frv.
#
# Fyrsta viðfang er þingnúmer, þau sem á eftir koma eru skjalanúmer.
#
# Uppsetning í fyrsta skipti:
#   mkdir -p ~/thingskjol && cd ~/thingskjol
#   git init -b main
#   gh repo create thingskjol --public --source=. --remote=origin
#   cp /leid/ad/skjalasokn.sh . && chmod +x skjalasokn.sh
#
# Geymslan verður að vera opin (public), annars kemst Claude ekki í hana.

set -uo pipefail

UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
OUTDIR="skjol"
SLEEP_MILLI=1200

if [ "$#" -lt 2 ]; then
    echo "Notkun: $0 <thingnumer> <skjalanumer> [skjalanumer ...]" >&2
    echo "Daemi:  $0 156 315 316" >&2
    exit 2
fi

THING="$1"
shift

if ! [[ "$THING" =~ ^[0-9]+$ ]]; then
    echo "Villa: thingnumer '$THING' er ekki tala." >&2
    exit 2
fi

# ---------------------------------------------------------------- forsendur

VANTAR=""
for SKIPUN in curl python3; do
    command -v "$SKIPUN" >/dev/null 2>&1 || VANTAR="$VANTAR $SKIPUN"
done
if [ -n "$VANTAR" ]; then
    echo "Villa: vantar$VANTAR" >&2
    echo "Ubuntu: sudo apt install -y curl python3 git" >&2
    exit 3
fi

mkdir -p "$OUTDIR"

# ---------------------------------------------------------------- hjalparforrit

# Umbreytir HTML i einfaldan texta. Notar python3 ur grunnsafni, engar adfluttar
# skrar. Skilar tomum streng ef ekkert meginmal finnst.
html_i_texta() {
    python3 - "$1" <<'PYEOF'
import io
import re
import sys
from html.parser import HTMLParser
from html import unescape

SLEPPA = {"script", "style", "head", "nav", "footer", "form", "select", "option"}
BLOKK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6",
         "table", "section", "article", "blockquote"}
BIL = {"td", "th", "span", "a"}


class Sigti(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.bitar = []
        self.sleppa_dypt = 0
        self.i_meginmali = False
        self.meginmal_dypt = 0
        self.dypt = 0

    def handle_starttag(self, tag, attrs):
        self.dypt += 1
        if tag in SLEPPA:
            self.sleppa_dypt += 1
            return
        adict = dict(attrs)
        merki = " ".join([adict.get("class", ""), adict.get("id", "")])
        if "pgmain" in merki and not self.i_meginmali:
            self.i_meginmali = True
            self.meginmal_dypt = self.dypt
        if tag in BLOKK:
            self.bitar.append("\n")
        elif tag in BIL:
            self.bitar.append(" ")

    def handle_endtag(self, tag):
        if tag in SLEPPA and self.sleppa_dypt > 0:
            self.sleppa_dypt -= 1
        if tag in BLOKK:
            self.bitar.append("\n")
        if self.i_meginmali and self.dypt == self.meginmal_dypt:
            self.i_meginmali = False
            self.meginmal_dypt = 0
        self.dypt = max(0, self.dypt - 1)

    def handle_data(self, data):
        if self.sleppa_dypt > 0:
            return
        if data.strip():
            self.bitar.append(data)


def hreinsa(texti):
    texti = unescape(texti)
    texti = re.sub(r"[ \t\x0b\f\r]+", " ", texti)
    linur = [lina.strip() for lina in texti.split("\n")]
    ut = []
    tomar = 0
    for lina in linur:
        if not lina:
            tomar += 1
            if tomar > 1:
                continue
        else:
            tomar = 0
        ut.append(lina)
    return "\n".join(ut).strip()


with io.open(sys.argv[1], encoding="utf-8", errors="replace") as f:
    hrar = f.read()

# Fyrst er reynt ad taka adeins meginmalid, sem er innan div med class pgmain.
hlutar = re.split(r'<div[^>]*(?:class|id)="[^"]*pgmain[^"]*"[^>]*>', hrar, maxsplit=1)
ef_meginmal = hlutar[1] if len(hlutar) > 1 else hrar

sigti = Sigti()
sigti.feed(ef_meginmal)
nidurstada = hreinsa("".join(sigti.bitar))

# Klippum af eftirmalann sem er eins a ollum sidum Althingis.
for merki in ("Þú ert hér:", "Deila", "Skrifstofa Alþingis"):
    stadur = nidurstada.find(merki)
    if stadur > 120:
        nidurstada = nidurstada[:stadur].rstrip()

sys.stdout.write(nidurstada)
PYEOF
}

sofa() {
    python3 -c "import time; time.sleep($SLEEP_MILLI/1000.0)" 2>/dev/null || sleep 2
}

# ------------------------------------------------------------------- sokn

FENGIN=0
MISTOKST=0

for NR in "$@"; do
    if ! [[ "$NR" =~ ^[0-9]+$ ]]; then
        echo "  ! sleppi '$NR', ekki tala" >&2
        MISTOKST=$((MISTOKST + 1))
        continue
    fi

    PADDED=$(printf "%04d" "$NR")
    HTML_URL="https://www.althingi.is/altext/${THING}/s/${PADDED}.html"
    PDF_URL="https://www.althingi.is/altext/pdf/${THING}/s/${PADDED}.pdf"
    HRATT="$OUTDIR/.${THING}-${PADDED}.html"
    SKJAL="$OUTDIR/${THING}-${PADDED}.md"

    echo "-> þingskjal ${NR} af ${THING}. þingi"

    KODI=$(curl -sS -L --compressed \
                -A "$UA" \
                -H 'Accept: text/html,application/xhtml+xml' \
                -H 'Accept-Language: is,en;q=0.8' \
                --max-time 45 \
                -o "$HRATT" \
                -w '%{http_code}' \
                "$HTML_URL" 2>/dev/null)

    if [ "$KODI" != "200" ] || [ ! -s "$HRATT" ]; then
        echo "   ! HTML gaf $KODI, reyni PDF" >&2
        if curl -sS -L -A "$UA" --max-time 45 -o "$OUTDIR/${THING}-${PADDED}.pdf" "$PDF_URL" 2>/dev/null; then
            echo "   . PDF vistad sem $OUTDIR/${THING}-${PADDED}.pdf (tharf ad lesa handvirkt)"
            FENGIN=$((FENGIN + 1))
        else
            echo "   ! nadi hvorki HTML ne PDF" >&2
            MISTOKST=$((MISTOKST + 1))
        fi
        rm -f "$HRATT"
        sofa
        continue
    fi

    TEXTI=$(html_i_texta "$HRATT")

    if [ -z "$TEXTI" ] || [ "${#TEXTI}" -lt 200 ]; then
        echo "   ! meginmal fannst ekki eda er of stutt (${#TEXTI} stafir), vista hratt HTML" >&2
        mv "$HRATT" "$OUTDIR/${THING}-${PADDED}.html"
        MISTOKST=$((MISTOKST + 1))
        sofa
        continue
    fi

    {
        echo "# Þingskjal ${NR}, ${THING}. löggjafarþing"
        echo
        echo "Sótt: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
        echo "Heimild: ${HTML_URL}"
        echo
        echo "---"
        echo
        printf '%s\n' "$TEXTI"
    } > "$SKJAL"

    rm -f "$HRATT"
    echo "   . $SKJAL ($(wc -c < "$SKJAL" | tr -d ' ') bæti)"
    FENGIN=$((FENGIN + 1))
    sofa
done

echo
echo "Fengin: $FENGIN   Mistókst: $MISTOKST"

# ------------------------------------------------------------------- git

if [ "$FENGIN" -eq 0 ]; then
    echo "Ekkert nýtt, sleppi git."
    exit 1
fi

if [ ! -d .git ]; then
    echo "Engin git-geymsla hér. Sjá uppsetningu í haus skriptunnar." >&2
    exit 1
fi

git add "$OUTDIR"

if git diff --cached --quiet; then
    echo "Engar breytingar til að vista."
else
    git commit -q -m "þingskjöl af ${THING}. þingi: $*"
    if git push -q origin HEAD 2>/dev/null; then
        echo "Ýtt í origin."
    else
        echo "Push mistókst. Athugaðu remote og aðgang." >&2
        exit 1
    fi
fi

# ------------------------------------------------------------------- slodir

FJARSLOD=$(git config --get remote.origin.url 2>/dev/null || true)
GREIN=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)

if [ -n "$FJARSLOD" ]; then
    STOFN=$(printf '%s' "$FJARSLOD" \
        | sed -e 's#^git@github.com:#https://github.com/#' \
              -e 's#^https://github.com/##' \
              -e 's#\.git$##' \
              -e 's#^#https://raw.githubusercontent.com/#')
    echo
    echo "Slóðir fyrir Claude:"
    for NR in "$@"; do
        [[ "$NR" =~ ^[0-9]+$ ]] || continue
        PADDED=$(printf "%04d" "$NR")
        [ -f "$OUTDIR/${THING}-${PADDED}.md" ] || continue
        echo "  ${STOFN}/${GREIN}/${OUTDIR}/${THING}-${PADDED}.md"
    done
fi

