"""Generate lbj/index.html from the song timing (lbj/assets/song_data.js)."""
import json
import re
import html
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))  # paths below are relative to this script

src = open("lbj/assets/song_data.js").read()
SONG = json.loads(re.search(r"window\.SONG=(.*);", src).group(1))
BAR = SONG["bar"]
SEC = SONG["sections"]
END = round(SONG["end"], 2)
tag_lines = [l for l in SONG["lines"] if l["sec"] == "tag"]
TAG_A, TAG_B = tag_lines[0]["t"], tag_lines[1]["t"]
HIT = SONG["hit"]


def r(x):
    return round(x, 3)


# ------------------------------------------------------------- captions
caps = []
for li, line in enumerate(SONG["lines"]):
    sec = line["sec"]
    if sec in ("ch1", "ch2"):
        words = [w for w in SONG["words"] if w["sec"] == sec and w["line"] == line["i"]]
        spans = " ".join(
            f'<span class="w" data-t="{r(w["t"])}">{html.escape(w["w"])}</span>' for w in words
        )
        caps.append(
            f'<div class="clip cap sung" id="cap{li}" data-start="{r(line["t"])}" data-duration="{r(BAR)}" data-track-index="9"><div class="cap-in">{spans}</div></div>'
        )
    else:
        dur = BAR if sec in ("v1", "v2") else line["d"] + 0.3
        if sec == "tag" and line["i"] == 0:
            dur = TAG_B - line["t"]
        text = line["text"]
        if sec == "tag" and line["i"] == 0:
            text = "Fun fact! His wife and both daughters? All L.B.J."
        caps.append(
            f'<div class="clip cap" id="cap{li}" data-start="{r(line["t"])}" data-duration="{r(dur)}" data-track-index="9"><div class="cap-in">{html.escape(text)}</div></div>'
        )
CAPTIONS = "\n      ".join(caps)


def L(sec, i):
    return r(SEC[sec] + i * BAR)


def scene(sid, sec, i, inner, bars=1, extra=""):
    return f'<section class="clip scene" id="{sid}" data-start="{L(sec, i)}" data-duration="{r(BAR * bars)}" data-track-index="2"{extra}><div class="in">{inner}</div></section>'


LBJ_FIG = """<svg class="lbj-fig" viewBox="0 0 200 420">
  <rect x="45" y="170" width="110" height="230" rx="30" fill="#23304a"/>
  <polygon points="100,175 88,190 100,300 112,190" fill="#b8322a"/>
  <polygon points="80,170 100,200 120,170" fill="#f4ede4"/>
  <rect x="85" y="140" width="30" height="35" fill="#e2b48f"/>
  <ellipse cx="46" cy="100" rx="16" ry="26" fill="#d9a47e"/>
  <ellipse cx="154" cy="100" rx="16" ry="26" fill="#d9a47e"/>
  <ellipse cx="100" cy="95" rx="52" ry="62" fill="#e8bf99"/>
  <path d="M50 70 Q100 10 150 70 Q140 45 100 40 Q60 45 50 70Z" fill="#555"/>
  <ellipse cx="100" cy="112" rx="14" ry="20" fill="#d9a47e"/>
  <rect x="72" y="85" width="12" height="6" rx="3" fill="#222"/>
  <rect x="116" y="85" width="12" height="6" rx="3" fill="#222"/>
  <path d="M80 138 Q100 146 120 138" stroke="#7a4a32" stroke-width="4" fill="none" stroke-linecap="round"/>
  <text x="100" y="260" text-anchor="middle" font-family="Luckiest Guy" font-size="34" fill="#f4ede4">LBJ</text>
</svg>"""

S = []  # scenes
# ---- verse 1
S.append(scene("s-v1-0", "v1", 0, """
  <div class="cal"><div class="cal-top">NOVEMBER</div><div class="cal-day">22</div><div class="cal-yr">1963</div></div>
  <div class="kicker k-left">Dallas, Texas</div>"""))
S.append(scene("s-v1-1", "v1", 1, """
  <div class="plane"><svg viewBox="0 0 520 160"><path d="M20 80 Q40 55 120 55 L430 55 Q505 60 510 80 Q505 100 430 105 L120 105 Q40 105 20 80Z" fill="#f4f6fb"/>
  <rect x="120" y="72" width="330" height="10" fill="#2d5aa8"/><path d="M200 60 L300 60 L240 5 L210 5Z" fill="#dfe4ee"/><path d="M220 100 L320 100 L250 155 L225 155Z" fill="#dfe4ee"/>
  <path d="M40 60 L20 10 L60 10 L90 58Z" fill="#2d5aa8"/><g fill="#9fb6dd">""" + "".join(f'<circle cx="{150+i*28}" cy="66" r="5"/>' for i in range(10)) + """</g>
  <text x="300" y="98" font-family="Fredoka" font-weight="700" font-size="16" fill="#2d5aa8" text-anchor="middle">UNITED STATES OF AMERICA</text></svg></div>
  <div class="big-title t-mid">Sworn in aboard<br/><span class="hl">Air Force One</span></div>""".replace("<br/>", " ")))
S.append(scene("s-v1-2", "v1", 2, """
  <div class="ruler">""" + "".join(f'<div class="tick"><span>{7-i}\'</span></div>' for i in range(7)) + """</div>
  <div class="fig-wrap tall">""" + LBJ_FIG + """</div>
  <div class="height-tag">6′4″</div>"""))
S.append(scene("s-v1-3", "v1", 3, """
  <div class="fig-wrap lean">""" + LBJ_FIG + """</div>
  <div class="senator"><div class="sen-head"></div><div class="sen-body">CONGRESS</div><div class="sweat s1"></div><div class="sweat s2"></div></div>
  <div class="stamp st-treat">THE JOHNSON<br/>TREATMENT™</div>""".replace("<br/>", " ")))
S.append(scene("s-v1-4", "v1", 4, """
  <div class="doc"><div class="doc-h">CIVIL RIGHTS ACT</div><div class="doc-sub">of 1964</div>
  <div class="doc-lines">""" + "<i></i>" * 6 + """</div>
  <svg class="sig" viewBox="0 0 300 80"><path id="sigpath" d="M10 55 Q30 10 45 50 T80 40 Q95 20 110 55 Q130 70 150 30 Q160 15 175 50 Q190 70 210 35 T260 45 Q275 40 290 30" stroke="#1d2a57" stroke-width="5" fill="none" stroke-linecap="round"/></svg></div>
  <div class="stamp st-law">LAW ✓</div>"""))
S.append(scene("s-v1-5", "v1", 5, """
  <div class="chart"><div class="bar-row"><div class="bar-lbl">JOHNSON</div><div class="bar b-lbj"><span class="cnt" id="cnt-lbj">0</span></div></div>
  <div class="bar-row"><div class="bar-lbl">GOLDWATER</div><div class="bar b-gw"><span class="cnt" id="cnt-gw">0</span></div></div>
  <div class="chart-note">Electoral votes, 1964 · LBJ won 44 states + D.C.</div></div>
  <div class="stamp st-land">LANDSLIDE!</div>"""))
S.append(scene("s-v1-6", "v1", 6, """
  <div class="ballots">""" + "".join(f'<div class="ballot bl{i}">✓</div>' for i in range(4)) + """</div>
  <div class="bbox"><div class="bbox-slot"></div><div class="bbox-lbl">VOTE</div></div>
  <div class="big-title t-top">Voting Rights Act <span class="hl">1965</span></div>"""))
S.append(scene("s-v1-7", "v1", 7, """
  <div class="confetti" id="conf1"></div>
  <div class="mega">BIG DEAL!</div>"""))

# ---- verse 2
S.append(scene("s-v2-0", "v2", 0, """
  <div class="card c1"><div class="card-ic">1964</div><div>WAR ON<br/>POVERTY</div></div>
  <div class="card c2"><div class="card-ic">1965</div><div>HEAD<br/>START</div></div>
  <div class="bus"><div class="bus-win">""" + "<i></i>" * 4 + """</div><div class="bus-lbl">SCHOOL BUS</div><div class="wheel w1"></div><div class="wheel w2"></div></div>""".replace("<br/>", " ")))
S.append(scene("s-v2-1", "v2", 1, """
  <div class="med m1"><div class="cross"></div><div class="med-t">MEDICARE</div></div>
  <div class="med m2"><div class="cross"></div><div class="med-t">MEDICAID</div></div>
  <div class="big-title t-top">Signed in <span class="hl">1965</span></div>"""))
S.append(scene("s-v2-2", "v2", 2, """
  <div class="passport"><div class="pp-h">PASSPORT</div><div class="pp-stamp">IMMIGRATION<br/>ACT 1965</div></div>
  <div class="school"><div class="roof"></div><div class="sch-body"><div class="door"></div></div><div class="sch-lbl">ELEMENTARY &amp; SECONDARY<br/>EDUCATION ACT 1965</div></div>""".replace("<br/>", " ")))
S.append(scene("s-v2-3", "v2", 3, """
  <div class="court"><div class="pedi"></div><div class="cols">""" + "<i></i>" * 5 + """</div><div class="steps"></div></div>
  <div class="gavel"><div class="g-head"></div><div class="g-handle"></div></div>
  <div class="tm-card"><div class="tm-name">Thurgood Marshall</div><div class="tm-sub">First Black Supreme Court justice · 1967</div></div>"""))
S.append(scene("s-v2-4", "v2", 4, """
  <div class="stencil">VIETNAM</div>
  <svg class="troops" viewBox="0 0 700 320"><path d="M40 280 L700 280" stroke="#d8d2b8" stroke-width="3"/>
  <path id="troopline" d="M60 272 L220 240 L380 90 L540 45 L680 20" stroke="#e24a3b" stroke-width="10" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
  <g font-family="Fredoka" font-weight="700" font-size="26" fill="#d8d2b8" text-anchor="middle"><text x="60" y="314">'64</text><text x="220" y="314">'65</text><text x="380" y="314">'66</text><text x="540" y="314">'67</text><text x="680" y="314">'68</text></g></svg>
  <div class="kicker k-right">U.S. troops in Vietnam</div>"""))
S.append(scene("s-v2-5", "v2", 5, """
  <div class="counter"><span id="cnt-troops">0</span>,000</div>
  <div class="counter-sub">U.S. troops by 1968</div>
  <div class="signs">""" + "".join(f'<div class="sign sg{i}"><div class="sign-b">{t}</div><div class="stick"></div></div>' for i, t in enumerate(["PEACE ☮", "BRING THEM HOME", "PEACE NOW", "END THE WAR"])) + """</div>"""))
S.append(scene("s-v2-6", "v2", 6, """
  <div class="tv"><div class="tv-screen"><div class="tv-date">MARCH 31, 1968</div><div class="tv-q">“I shall not seek, and I will not accept, the nomination of my party for another term as your President.”</div><div class="scan"></div></div><div class="tv-knobs"><i></i><i></i></div></div>"""))
S.append(scene("s-v2-7", "v2", 7, """
  <div class="sun"></div>
  <div class="hills"></div>
  <div class="fence">""" + "<i></i>" * 9 + """</div>
  <div class="ranch-sign">LBJ RANCH<small>Stonewall, Texas</small></div>"""))

# ---- choruses
def chorus(sec, variant):
    t0 = SEC[sec]
    out = []
    out.append(f'<section class="clip scene chorus" id="s-{sec}-a" data-start="{r(t0)}" data-duration="{r(BAR)}" data-track-index="2"><div class="in"><div class="lbj-letters"><span class="lt lt1">L</span><span class="lt lt2">B</span><span class="lt lt3">J</span></div></div></section>')
    if variant == "A":
        out.append(f'<section class="clip scene chorus" id="s-{sec}-b" data-start="{r(t0 + BAR)}" data-duration="{r(BAR)}" data-track-index="2"><div class="in"><div class="banner"><span>THE GREAT SOCIETY</span></div><div class="confetti" id="conf-{sec}"></div></div></section>')
    else:
        out.append(f'<section class="clip scene chorus" id="s-{sec}-b" data-start="{r(t0 + BAR)}" data-duration="{r(BAR)}" data-track-index="2"><div class="in"><div class="split"><div class="half win"><h3>BIG WINS</h3><p>✓ Civil Rights Act</p><p>✓ Voting Rights Act</p><p>✓ Medicare &amp; Medicaid</p></div><div class="half war"><h3>BIG WAR</h3><p>✗ Vietnam</p></div></div></div></section>')
    out.append(f'<section class="clip scene chorus" id="s-{sec}-c" data-start="{r(t0 + 2 * BAR)}" data-duration="{r(BAR)}" data-track-index="2"><div class="in"><div class="lbj-letters"><span class="lt lt1">L</span><span class="lt lt2">B</span><span class="lt lt3">J</span></div></div></section>')
    if variant == "A":
        out.append(f'<section class="clip scene chorus" id="s-{sec}-d" data-start="{r(t0 + 3 * BAR)}" data-duration="{r(BAR)}" data-track-index="2"><div class="in"><div class="lone-star">★</div><div class="big-title t-top">The Lone Star State</div></div></section>')
    else:
        out.append(f'<section class="clip scene chorus" id="s-{sec}-d" data-start="{r(t0 + 3 * BAR)}" data-duration="{r(BAR)}" data-track-index="2"><div class="in"><div class="scale"><div class="beam"><div class="pan pl">WINS</div><div class="pan pr">WAR</div></div><div class="post"></div></div><div class="big-title t-top">History’s complicated.</div></div></section>')
    return out


S += chorus("ch1", "A") + chorus("ch2", "B")

# ---- intro + tag
S.insert(0, f"""<section class="clip scene" id="s-intro" data-start="0" data-duration="{r(SEC['v1'])}" data-track-index="2"><div class="in">
  <div class="intro-star">★</div>
  <div class="intro-title"><span class="it it1">L</span><span class="dot">·</span><span class="it it2">B</span><span class="dot">·</span><span class="it it3">J</span></div>
  <div class="intro-sub">Lyndon Baines Johnson · 36th U.S. President · 1963–1969</div>
  <div class="intro-credit">a Clawd-pop history lesson</div></div></section>""")

fam = [("Lyndon Baines Johnson", "the president"), ("Lady Bird Johnson", "his wife"), ("Lynda Bird Johnson", "daughter"), ("Luci Baines Johnson", "daughter")]


def lbjify(name):
    parts = name.split()
    return " ".join(f"<b>{p[0]}</b>{p[1:]}" for p in parts)


S.append(f"""<section class="clip scene" id="s-tag" data-start="{r(SEC['tag'])}" data-duration="{r(HIT - SEC['tag'])}" data-track-index="2"><div class="in">
  <div class="funfact">FUN FACT</div>
  <div class="family">""" + "".join(f'<div class="nametag nt{i}"><div class="nt-h">HELLO my name is</div><div class="nt-n">{lbjify(n)}</div><div class="nt-r">{rr}</div></div>' for i, (n, rr) in enumerate(fam)) + f"""</div>
  <div class="dog"><svg viewBox="0 0 260 200"><ellipse cx="140" cy="130" rx="85" ry="45" fill="#f4ede4"/><path d="M80 115 Q120 95 170 110 Q200 120 215 105 L220 150 Q150 160 90 150Z" fill="#8a5a2b"/>
  <rect x="80" y="160" width="16" height="32" rx="7" fill="#f4ede4"/><rect x="110" y="162" width="16" height="30" rx="7" fill="#f4ede4"/><rect x="165" y="162" width="16" height="30" rx="7" fill="#f4ede4"/><rect x="195" y="160" width="16" height="32" rx="7" fill="#f4ede4"/>
  <path d="M220 110 Q250 80 245 60" stroke="#8a5a2b" stroke-width="10" fill="none" stroke-linecap="round"/><path d="M243 62 Q246 50 240 44" stroke="#fff" stroke-width="10" fill="none" stroke-linecap="round"/>
  <ellipse cx="55" cy="85" rx="42" ry="36" fill="#8a5a2b"/><ellipse cx="30" cy="100" rx="22" ry="22" fill="#f4ede4"/><ellipse cx="14" cy="96" rx="9" ry="7" fill="#222"/>
  <path d="M70 60 Q95 70 88 125 Q72 128 66 95Z" fill="#5b3a1a"/><circle cx="45" cy="75" r="6" fill="#222"/><circle cx="47" cy="73" r="2" fill="#fff"/>
  <rect x="68" y="112" width="40" height="10" rx="5" fill="#d23c3c"/><circle cx="88" cy="126" r="7" fill="#f2c14e"/></svg>
  <div class="dog-tag">{lbjify("Little Beagle Johnson")}</div></div>
</div></section>""")
S.append(f"""<section class="clip scene" id="s-end" data-start="{r(HIT)}" data-duration="{r(END - HIT)}" data-track-index="2"><div class="in">
  <div class="end-title">L·B·J</div><div class="end-sub">1963 – 1969 · all the way</div><div class="confetti" id="conf-end"></div></div></section>""")

SCENES = "\n      ".join(S)

tpl = open("lbj_template.html").read()
out = (
    tpl.replace("__SCENES__", SCENES)
    .replace("__CAPTIONS__", CAPTIONS)
    .replace("__END__", str(END))
    .replace("__TAG_A__", str(r(TAG_A)))
    .replace("__TAG_B__", str(r(TAG_B)))
    .replace("__HIT__", str(r(HIT)))
    .replace("__TAG_REST__", str(r(END - SEC["tag"])))
)
open("lbj/index.html", "w").write(out)
print("wrote index.html", END, TAG_A, TAG_B, HIT)
