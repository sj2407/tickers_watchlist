#!/usr/bin/env python3
"""
Build the visual /primer document by lifting VERBATIM text from the approved
content markdown and decorating it. No sentence is ever retyped or reworded:
the parser copies literal substrings out of the .md, and the renderer only
WRAPS those substrings in markup (bold/colour/charts). Run with --audit to
prove, against the produced HTML, that every approved sentence is present
verbatim and that no prose was paraphrased.

Usage:
    python3 build_primer.py            # build primer-tech.html
    python3 build_primer.py --audit    # build, then audit fidelity vs the .md
"""
import json
import re
import sys
import html as htmllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC_TECH = ROOT / "primer-content-tech.md"
OUT_TECH = ROOT / "primer-tech.html"

# ---- theme taxonomy -> accent colour (vivid, AA on near-black; neighbours in the
#      reading sequence differ in hue family so adjacent sections never clash) ----
THEME_COLOR = {
    "semicap equipment":    "#e879c9",  # magenta (litho / equipment)
    "foundry":              "#2dd4bf",  # teal (manufacturing)
    "memory":               "#a78bfa",  # violet
    "AI silicon":           "#5ea8ff",  # blue (the brains)
    "semiconductor IP":     "#4ade80",  # green (design ingredients)
    "optical/connectivity": "#fb7185",  # rose (the wiring)
    "AI infrastructure":    "#fbbf63",  # amber (the cloud)
    "software":             "#7dd3fc",  # sky
}
# Roman numerals for the eight phases, in reading order.
PHASE_ROMAN = ["1", "2", "3", "4", "5", "6", "7", "8"]

# ---- supply-chain edges (real supplier relationships among the holdings) ----
# "supplies" = sells to / feeds. Supplied-by is derived. Edges represent the
# AI build-out chain described verbatim in L1 (equipment -> foundry -> designers
# -> cloud; memory/interconnect/IP feed the machine).
SUPPLIES = {
    "ASML": ["TSM"],
    "AMAT": ["TSM", "MU", "SNDK"],
    "LRCX": ["TSM", "MU", "SNDK"],
    "KLAC": ["TSM", "MU", "SNDK"],
    "TSM":  ["NVDA", "AVGO", "MRVL"],
    "MU":   ["NVDA"],
    "SNDK": [],
    "NVDA": ["CRWV"],
    "AVGO": [],
    "MRVL": [],
    "CEVA": ["NVDA"],
    "COHR": ["NVDA"],
    "LITE": ["NVDA"],
    "CRDO": ["NVDA"],
    "CRWV": [],
    "NOW":  [],
    "CRWD": [],
}

# inline SVG icons per theme (self-contained, no external assets)
ICONS = {
    "semicap equipment": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/></svg>',
    "foundry": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"><path d="M3 21V11l5 3V11l5 3V8l5 3v10z"/><path d="M3 21h18"/></svg>',
    "memory": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"><rect x="4" y="6" width="16" height="4" rx="1"/><rect x="4" y="13" width="16" height="4" rx="1"/><path d="M8 6V4M16 6V4M8 20v-3M16 20v-3"/></svg>',
    "AI silicon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"><rect x="7" y="7" width="10" height="10" rx="1.5"/><rect x="10" y="10" width="4" height="4"/><path d="M10 7V4M14 7V4M10 20v-3M14 20v-3M7 10H4M7 14H4M20 10h-3M20 14h-3"/></svg>',
    "semiconductor IP": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"><path d="M4 7h16M4 12h10M4 17h16"/></svg>',
    "optical/connectivity": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><circle cx="6" cy="12" r="2"/><path d="M9 12h11"/><path d="M14 9l3 3-3 3"/></svg>',
    "AI infrastructure": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"><path d="M7 18a4 4 0 0 1-.5-7.97A5.5 5.5 0 0 1 17 9.5a3.5 3.5 0 0 1 0 8.5z"/></svg>',
    "software": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18"/><path d="M9 14l-2 2 2 2M14 14l2 2-2 2"/></svg>',
}

# Charts built ONLY from figures stated verbatim in the text. Share-of-a-whole
# data (sums to ~100%) -> donut; a revenue ranking ($B, not a share) -> bars.
# rows: [label, value, is_owned].
CHARTS = {
    "semicap equipment": [
        {"type": "bars", "title": "Equipment revenue", "unit": "$",
         "cap": "approx revenue, $B, fiscal 2025 · the five control ~70% of all chip-equipment spending",
         "rows": [["ASML", 28, 1], ["Applied Materials", 26.5, 1], ["Tokyo Electron", 19.2, 0], ["Lam Research", 16.8, 1], ["KLA", 10.8, 1]]},
    ],
    "foundry": [
        {"type": "donut", "title": "Foundry", "cap": "% of contract-manufacturing market · TSMC also >90% of the leading edge",
         "rows": [["TSMC", 70, 1], ["Samsung", 5, 0], ["Intel + others", 25, 0]]},
    ],
    "memory": [
        {"type": "donut", "title": "DRAM", "cap": "% of DRAM", "rows": [["SK Hynix", 34, 0], ["Samsung", 33, 0], ["Micron", 26, 1], ["others", 7, 0]]},
        {"type": "donut", "title": "HBM", "cap": "% of HBM, the AI memory", "rows": [["SK Hynix", 60, 0], ["Micron", 20, 1], ["Samsung", 17, 0], ["others", 3, 0]]},
        {"type": "donut", "title": "NAND", "cap": "% of NAND storage", "rows": [["Samsung", 32, 0], ["SK Hynix", 19, 0], ["Kioxia", 15, 0], ["SanDisk", 12, 1], ["Micron", 10, 1], ["others", 12, 0]]},
    ],
    "AI silicon": [
        {"type": "donut", "title": "Merchant GPUs", "cap": "% of AI accelerators", "rows": [["Nvidia", 89, 1], ["AMD", 6, 0], ["others", 5, 0]]},
        {"type": "donut", "title": "Custom silicon", "cap": "% of custom AI silicon", "rows": [["Broadcom", 62, 1], ["Marvell", 25, 1], ["others", 13, 0]]},
    ],
    "optical/connectivity": [
        {"type": "donut", "title": "Transceivers", "cap": "% of optical transceivers · top five make ~half", "rows": [["Coherent", 16, 1], ["Lumentum", 11, 1], ["Other top five", 23, 0], ["Rest of market", 50, 0]]},
        {"type": "donut", "title": "Active e-cables", "cap": "% of active electrical cables, a separate niche", "rows": [["Credo", 88, 1], ["Astera, Marvell, others", 12, 0]]},
    ],
    "AI infrastructure": [
        {"type": "donut", "title": "AI cloud ~2030", "cap": "AI-cloud market, ~2030 estimate", "rows": [["Hyperscalers", 80, 0], ["Neoclouds", 20, 1]]},
    ],
    "software": [
        {"type": "donut", "title": "ITSM", "cap": "% of IT-service management", "rows": [["ServiceNow", 44, 1], ["Others", 56, 0]]},
        {"type": "donut", "title": "Endpoint security", "cap": "% of endpoint security", "rows": [["Microsoft", 40, 0], ["CrowdStrike", 14, 1], ["Others", 46, 0]]},
    ],
}

# ----------------------------------------------------------------------------
# PARSING: lift verbatim strings from the markdown.
# ----------------------------------------------------------------------------
MARK_RE = re.compile(r"\*\*\[(?:VISUAL|ACCENT):.*?\]\*\*", re.DOTALL)


def strip_markers(text):
    """Remove **[VISUAL: ...]** / **[ACCENT: ...]** build directives."""
    return MARK_RE.sub("", text).strip()


def debold(text):
    """Remove markdown bold and inline-code markers; the prose chars are unchanged."""
    return text.replace("**", "").replace("`", "")


def split_blocks(lines):
    """List-aware block splitter. A line starting with '- ' or 'N. ' begins a new
    block even without a preceding blank line; blank lines and '---' end a block;
    other lines are continuation. Returns [{'marker': None|'-'|int, 'raw': str}]
    with the literal markdown (bold/code markers preserved) joined by spaces."""
    blocks, cur = [], None

    def flush():
        nonlocal cur
        if cur is not None:
            cur["raw"] = " ".join(p.strip() for p in cur["parts"]).strip()
            del cur["parts"]
            blocks.append(cur)
            cur = None

    for ln in lines:
        s = ln.strip()
        if s == "" or s == "---":
            flush()
            continue
        mul = re.match(r"^[-*]\s+(.*)$", s)
        mol = re.match(r"^(\d+)\.\s+(.*)$", s)
        if mul:
            flush()
            cur = {"marker": "-", "parts": [mul.group(1)]}
        elif mol:
            flush()
            cur = {"marker": int(mol.group(1)), "parts": [mol.group(2)]}
        else:
            if cur is None:
                cur = {"marker": None, "parts": [s]}
            else:
                cur["parts"].append(s)
    flush()
    return blocks


def split_lead(raw):
    """Pull a leading **bold** label off a block. ('Compute.', 'An AI model...').
    Fires only when the block literally starts with '**...**'; returns ('', body)
    otherwise, so plain paragraphs keep no label."""
    raw = strip_markers(raw)
    m = re.match(r"^\*\*(.+?)\*\*\s*(.*)$", raw, re.DOTALL)
    if m:
        return debold(m.group(1)).strip(), debold(m.group(2)).strip()
    return "", debold(raw).strip()


def parse_tech(md_text):
    lines = md_text.split("\n")
    model = {
        "title": "",
        "l0": "",
        "l1_intro": "",
        "l1_items": [],     # list of {lead, body} (lead may be "")
        "forces_intro": "",
        "forces": [],       # list of {num, lead, body}
        "cycle": "",
        "l2_intro": "",
        "phases": [],       # list of phase dicts
        "onemin": [],
        "sources": [],
    }

    # locate section heading indices
    def find(idx_pred):
        for i, ln in enumerate(lines):
            if idx_pred(ln):
                return i
        return -1

    model["title"] = debold(lines[0].lstrip("# ").strip())

    i_l0 = find(lambda l: l.startswith("## L0"))
    i_l1 = find(lambda l: l.startswith("## L1"))
    i_forces = find(lambda l: l.startswith("### The four forces"))
    i_cycle = find(lambda l: l.startswith("### Reading the cycle"))
    i_l2 = find(lambda l: l.startswith("## L2"))
    i_onemin = find(lambda l: l.startswith("## Reading your tech"))
    i_sources = find(lambda l: l.startswith("## Sources"))

    def blocks(a, b):
        out = []
        for blk in split_blocks(lines[a:b]):
            if not strip_markers(blk["raw"]):
                continue
            out.append(blk)
        return out

    # L0
    for blk in blocks(i_l0 + 1, i_l1):
        model["l0"] = split_lead(blk["raw"])[1]
        break

    # L1: intro paragraph, then bold-lead paragraphs and bullets
    for blk in blocks(i_l1 + 1, i_forces):
        lead, body = split_lead(blk["raw"])
        if not model["l1_intro"] and not lead and blk["marker"] is None:
            model["l1_intro"] = body
            continue
        model["l1_items"].append({"lead": lead, "body": body, "bullet": blk["marker"] == "-"})

    # four forces
    for blk in blocks(i_forces + 1, i_cycle):
        lead, body = split_lead(blk["raw"])
        if isinstance(blk["marker"], int):
            model["forces"].append({"num": blk["marker"], "lead": lead, "body": body})
        elif not model["forces_intro"]:
            model["forces_intro"] = body

    # reading the cycle
    for blk in blocks(i_cycle + 1, i_l2):
        model["cycle"] = split_lead(blk["raw"])[1]
        break

    # L2 intro
    end_l2_intro = next(k for k, ln in enumerate(lines) if k > i_l2 and ln.startswith("### Phase"))
    for blk in blocks(i_l2 + 1, end_l2_intro):
        model["l2_intro"] = split_lead(blk["raw"])[1]
        break

    # phases + companies
    phase_starts = [k for k, ln in enumerate(lines) if ln.startswith("### Phase")]
    bounds = phase_starts + [i_onemin]
    for pi in range(len(phase_starts)):
        ph_lines = lines[bounds[pi]:bounds[pi + 1]]
        hm = re.match(r"^### Phase ·\s*(.*?)\s*`theme:\s*(.*?)`", ph_lines[0])
        phase = {"title": debold(hm.group(1).strip()), "theme": hm.group(2).strip(),
                 "fields": [], "companies": []}

        comp_idx = [k for k, ln in enumerate(ph_lines) if ln.startswith("#### ")]
        head_end = comp_idx[0] if comp_idx else len(ph_lines)
        for blk in split_blocks(ph_lines[1:head_end]):
            if not strip_markers(blk["raw"]):
                continue
            lead, body = split_lead(blk["raw"])
            phase["fields"].append({"lead": lead, "body": body})

        comp_bounds = comp_idx + [len(ph_lines)]
        for ci in range(len(comp_idx)):
            c_lines = ph_lines[comp_bounds[ci]:comp_bounds[ci + 1]]
            chm = re.match(r"^####\s+(.*?)\s*\(([A-Z]+)\)\s*$", c_lines[0])
            comp = {"name": debold(chm.group(1).strip()), "ticker": chm.group(2).strip(), "fields": []}
            for blk in split_blocks(c_lines[1:]):
                if not strip_markers(blk["raw"]):
                    continue
                lead, body = split_lead(blk["raw"])
                comp["fields"].append({"lead": lead, "body": body})
            phase["companies"].append(comp)
        model["phases"].append(phase)

    # one minute
    for blk in blocks(i_onemin + 1, i_sources):
        if blk["marker"] == "-":
            model["onemin"].append(split_lead(blk["raw"])[1])

    # sources
    for ln in lines[i_sources + 1:]:
        s = ln.strip()
        if not s.startswith("- "):
            continue
        s = s[2:]
        label = s.split(":", 1)[0].strip()
        links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", s)
        model["sources"].append({"label": label, "links": [{"text": t, "url": u} for t, u in links]})

    return model


# ----------------------------------------------------------------------------
# DECORATION: wrap existing substrings only (never change characters).
# ----------------------------------------------------------------------------
NUM_PATTERN = (
    r"\$\d[\d.,]*\s*(?:billion|million)?|"
    r"\b\d[\d.,]*\s*(?:to\s*\d[\d.,]*\s*)?(?:billion|million)\s*dollars|"
    r"\b\d[\d.,]*(?:\s*to\s*\d[\d.,]*)?\s*%|"
    r"\bover\s*9[07]%|"
    r"\b\d[\d.,]*\s*nm\b"
)

# Competitor / company names to surface, so the reader can see the players at a
# glance. Wrapped in <span class=ent> (no characters changed).
ENTITIES = [
    "Applied Materials", "Tokyo Electron", "Lam Research", "SK Hynix", "Palo Alto Networks",
    "Astera Labs", "Carl Zeiss", "Western Digital", "Oxford Ionics", "Trend Micro", "Google DeepMind",
    "Nvidia", "Broadcom", "Marvell", "ASML", "TSMC", "Samsung", "Micron", "SanDisk", "Intel",
    "Canon", "Nikon", "Kioxia", "Coherent", "Lumentum", "Credo", "InnoLight", "Accelink",
    "CoreWeave", "Nebius", "Lambda", "Crusoe", "Microsoft", "Amazon", "Google", "Meta",
    "OpenAI", "Anthropic", "ServiceNow", "CrowdStrike", "Ceva", "SentinelOne", "Atlassian",
    "Salesforce", "Zeiss", "Quantinuum", "Rigetti", "DeepMind", "VMware", "Apple", "Defender",
    "CUDA", "Arm", "AMD", "BMC", "Jira", "CXMT", "IBM", "AWS", "Azure", "xAI",
]
# Key concept terms that carry the "what kind of business is this" idea. Italic.
TERMS = [
    "monopoly", "monopolies", "commodity", "commodities", "oligopoly", "duopoly",
    "lock-in", "leading edge", "leading-edge", "price maker", "price makers",
    "vertical integration", "vertically integrated", "switching cost", "switching costs",
    "network effects", "first-mover", "pure-play", "scarcity", "bottleneck", "neutral",
]
_ent_alt = "|".join(re.escape(e) for e in sorted(set(ENTITIES), key=len, reverse=True))
_term_alt = "|".join(re.escape(t) for t in sorted(set(TERMS), key=len, reverse=True))
EMPH_RE = re.compile(
    rf"(?P<fig>{NUM_PATTERN})"
    rf"|(?P<ent>\b(?:{_ent_alt})\b)"
    rf"|(?P<key>(?i:\b(?:{_term_alt})\b))"
)


def deco(text):
    """HTML-escape, then draw the eye to key information by wrapping (only): figures
    in colour, competitor names, and key concept terms. Characters are unchanged."""
    esc = htmllib.escape(text)

    def rep(m):
        cls = m.lastgroup
        return f'<span class="{cls}">{m.group()}</span>'

    return EMPH_RE.sub(rep, esc)


def esc_block(text, tag="p", cls=""):
    """A verbatim element whose content is plain-escaped (no emphasis) — for
    headers/titles where entity wrapping would be noise."""
    return block(text, htmllib.escape(text), tag=tag, cls=cls)


def src_attr(text):
    return htmllib.escape(text, quote=True)


def slug(theme):
    return re.sub(r"[^a-z0-9]+", "-", theme.lower()).strip("-")


def block(full, inner, tag="p", cls=""):
    """A verbatim prose element. `full` is the literal source string (stored in
    data-src for the audit); `inner` is the decorated HTML of the same text."""
    c = f' class="{cls}"' if cls else ""
    return f'<{tag}{c} data-src="{src_attr(full)}">{inner}</{tag}>'


def lead_para(lead, body, cls=""):
    full = (lead + " " + body).strip() if lead else body
    inner = (f'<strong class="lead-in">{deco(lead)}</strong> ' if lead else "") + deco(body)
    return block(full, inner, cls=cls)


def field_html(f, label_text=None):
    """A labelled field (mono micro-label + prose). A label-less block (the
    phase-level rivalry paragraph) becomes a takeaway callout."""
    if not f["lead"]:
        return f'<div class="takeaway">{block(f["body"], deco(f["body"]))}</div>'
    lab = htmllib.escape(label_text if label_text is not None else f["lead"].rstrip("."))
    return f'<div class="fld"><span class="lab">{lab}</span>{block(f["body"], deco(f["body"]), cls="fld-p")}</div>'


# ---- charts: generated server-side as self-contained SVG / markup ----
GREYS = ["#7b8190", "#565c6b", "#9aa0ad", "#454b59", "#6b7280"]


def _row_colors(rows, accent):
    cols, gi = [], 0
    for _, _, owned in rows:
        if owned:
            cols.append(accent)
        else:
            cols.append(GREYS[gi % len(GREYS)])
            gi += 1
    return cols


def donut_svg(chart, accent):
    import math
    rows = chart["rows"]
    cols = _row_colors(rows, accent)
    total = sum(v for _, v, _ in rows) or 1
    r, sw, cx = 64, 24, 80
    C = 2 * math.pi * r
    owned_sum = sum(v for _, v, o in rows if o)
    seg, off = [], 0.0
    for i, (label, val, owned) in enumerate(rows):
        frac = val / total
        arc = max(frac * C - 2.5, 0.5)
        seg.append(f'<circle cx="{cx}" cy="{cx}" r="{r}" fill="none" stroke="{cols[i]}" '
                   f'stroke-width="{sw + (4 if owned else 0)}" stroke-linecap="butt" '
                   f'stroke-dasharray="{arc:.1f} {C - arc:.1f}" stroke-dashoffset="{-off:.1f}" '
                   f'transform="rotate(-90 {cx} {cx})"/>')
        off += frac * C
    big = (f"{owned_sum:g}%" if owned_sum else htmllib.escape(chart["title"]))
    small = htmllib.escape(chart["title"]) if owned_sum else ""
    svg = (f'<svg viewBox="0 0 160 160" class="donut" role="img" aria-label="{htmllib.escape(chart["cap"])}">'
           f'<circle cx="{cx}" cy="{cx}" r="{r}" fill="none" stroke="#1a1b22" stroke-width="{sw}"/>'
           + "".join(seg)
           + f'<text x="{cx}" y="{cx + (0 if small else 6)}" text-anchor="middle" class="d-big">{big}</text>'
           + (f'<text x="{cx}" y="{cx + 18}" text-anchor="middle" class="d-small">{small}</text>' if small else "")
           + "</svg>")
    legend = '<ul class="legend">' + "".join(
        f'<li class="{"me" if o else ""}"><span class="sw" style="background:{cols[i]}"></span>'
        f'<span class="ln">{htmllib.escape(lab)}</span><span class="fig">{v:g}%</span></li>'
        for i, (lab, v, o) in enumerate(rows)) + "</ul>"
    return (f'<figure class="chart" style="--cat:{accent}"><div class="chart-body">{svg}{legend}</div>'
            f'<figcaption>{htmllib.escape(chart["cap"])}</figcaption></figure>')


def bars_html(chart, accent):
    rows = chart["rows"]
    mx = max(v for _, v, _ in rows) or 1
    unit = chart.get("unit", "")
    body = "".join(
        f'<div class="bar-row{" me" if o else ""}">'
        f'<span class="bar-label">{htmllib.escape(lab)}</span>'
        f'<span class="bar-track"><span class="bar-fill" style="width:{v / mx * 100:.0f}%{"" if o else ";opacity:.5"}"></span></span>'
        f'<span class="fig">{unit}{v:g}</span></div>'
        for lab, v, o in rows)
    return (f'<figure class="chart bars" style="--cat:{accent}"><div class="barset">{body}</div>'
            f'<figcaption>{htmllib.escape(chart["cap"])}</figcaption></figure>')


def charts_for(theme, accent):
    cs = CHARTS.get(theme, [])
    if not cs:
        return ""
    items = "".join(donut_svg(c, accent) if c["type"] == "donut" else bars_html(c, accent) for c in cs)
    return f'<div class="charts">{items}</div>'


def supply_html(ticker, names):
    sup = SUPPLIES.get(ticker, [])
    supby = [k for k, v in SUPPLIES.items() if ticker in v]

    def tk(t):
        return f'<a class="tk" href="#co-{t}">{t}</a> ({htmllib.escape(names.get(t, t))})'

    a = f'Supplies {", ".join(tk(t) for t in sup)}.' if sup else ""
    b = f'Supplied by {", ".join(tk(t) for t in supby)}.' if supby else ""
    line = (a + " " + b).strip() if (a or b) else "No supply links to other holdings (standalone in your book)."
    return f'<div class="fld supply"><span class="lab">Supply links</span><p>{line}</p></div>'


def company_html(c, accent, names):
    fields = {f["lead"].rstrip("."): f for f in c["fields"] if f["lead"]}
    body = "".join(field_html(fields[k]) for k in
                   ("Role", "Revenue source", "Competitive landscape", "Moat", "Indicators to watch", "Catalysts")
                   if k in fields)
    wbb = fields.get("Worst / Base / Best")
    scen = ""
    if wbb:
        parts = [p.strip() for p in wbb["body"].split(" / ")]
        if len(parts) == 3:
            nm, kd = ["Worst", "Base", "Best"], ["worst", "base", "best"]
            rows = "".join(f'<div class="scn {kd[i]}"><span class="scn-k">{nm[i]}</span>'
                           f'{block(parts[i], deco(parts[i]), cls="scn-p")}</div>' for i in range(3))
            scen = f'<div class="scn-wrap"><span class="lab">Worst / Base / Best</span><div class="scn-rows">{rows}</div></div>'
        else:
            scen = field_html(wbb)
    chev = ('<svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg>')
    summary = (f'<summary class="co-h"><span class="co-tk">{c["ticker"]}</span>'
               f'<h4 class="co-n">{esc_block(c["name"], tag="span")}</h4>{chev}</summary>')
    return (f'<details class="co" id="co-{c["ticker"]}" style="--cat:{accent}">{summary}'
            f'<div class="co-body">{body}{scen}{supply_html(c["ticker"], names)}</div></details>')


GLANCE_LABELS = {"The role", "Where the profit concentrates", "Why this phase behaves differently",
                 "Why this phase is risky", "Why this phase is steadier"}


def phase_html(phase, idx, names):
    theme = phase["theme"]
    accent = THEME_COLOR[theme]
    roman = PHASE_ROMAN[idx]
    glance, detail = "", ""
    for f in phase["fields"]:
        lbl = f["lead"].rstrip(".") if f["lead"] else ""
        if lbl in GLANCE_LABELS:
            glance += field_html(f)
        else:
            detail += field_html(f)
    companies = "".join(company_html(c, accent, names) for c in phase["companies"])
    return (f'<section class="phase" id="phase-{slug(theme)}" style="--cat:{accent}">'
            f'<div class="phase-band"><span class="phase-no">{roman}</span>'
            f'<span class="phase-ic">{ICONS.get(theme, "")}</span>'
            f'<div class="phase-tt"><span class="eyebrow">Phase {roman} · {htmllib.escape(theme)}</span>'
            f'<h3 class="phase-h">{esc_block(phase["title"], tag="span")}</h3></div></div>'
            f'<div class="glance">{glance}</div>{charts_for(theme, accent)}'
            f'<div class="phase-detail">{detail}</div>'
            f'<div class="co-list"><div class="co-list-head">'
            f'<span class="co-list-lab">Companies in this phase <span class="co-count">{len(phase["companies"])}</span></span>'
            f'<button class="expand-all" type="button">Expand all</button></div>{companies}</div></section>')


# ----------------------------------------------------------------------------
# RENDER
# ----------------------------------------------------------------------------

def render(model):
    names = {c["ticker"]: c["name"] for ph in model["phases"] for c in ph["companies"]}
    data = {"phases": [{"theme": p["theme"], "title": p["title"], "slug": slug(p["theme"]),
                        "tickers": [c["ticker"] for c in p["companies"]]} for p in model["phases"]],
            "supplies": SUPPLIES, "themeColor": THEME_COLOR, "icons": ICONS}

    # --- L1: concept blocks (bold lead-ins become scannable sub-labels) ---
    l1 = [block(model["l1_intro"], deco(model["l1_intro"]), cls="lead")]
    for it in model["l1_items"]:
        if it["lead"].startswith("The chain"):
            l1.append(f'<div class="takeaway">{lead_para(it["lead"], it["body"])}</div>')
        else:
            cls = "concept bullet" if it.get("bullet") else "concept"
            l1.append(f'<div class="{cls}">{lead_para(it["lead"], it["body"])}</div>')

    # --- four forces: distinctly-coloured cards ---
    force_accents = ["#fbbf63", "#a78bfa", "#fb7185", "#5ea8ff"]
    forces = []
    for f in model["forces"]:
        ac = force_accents[(f["num"] - 1) % len(force_accents)]
        forces.append(f'<div class="force" style="--cat:{ac}"><div class="fn">{f["num"]}</div>'
                      f'<div class="ft">{lead_para(f["lead"], f["body"])}</div></div>')

    # --- phases ---
    phases = "".join(phase_html(p, i, names) for i, p in enumerate(model["phases"]))

    # --- one minute ---
    onemin = "".join(f'<li>{block(t, deco(t), tag="span")}</li>' for t in model["onemin"])

    # --- sources ---
    src = []
    for s in model["sources"]:
        links = " ".join(
            f'<a href="{htmllib.escape(l["url"])}" target="_blank" rel="noreferrer">{htmllib.escape(l["text"])}</a>'
            for l in s["links"])
        src.append(f'<div class="srcrow"><span class="sl">{htmllib.escape(s["label"])}</span><span class="slk">{links}</span></div>')

    # --- sticky contents nav ---
    nav = ['<a class="nav-top" href="#sec-1"><span class="nr">I</span>How the ecosystem works</a>',
           '<a class="nav-top" href="#sec-2"><span class="nr">II</span>The four forces</a>',
           '<a class="nav-top" href="#sec-3"><span class="nr">III</span>Reading the cycle</a>',
           '<a class="nav-top" href="#sec-4"><span class="nr">IV</span>The landscape</a>']
    for i, p in enumerate(model["phases"]):
        nav.append(f'<a class="nav-sub" href="#phase-{slug(p["theme"])}">'
                   f'<span class="dot" style="background:{THEME_COLOR[p["theme"]]}"></span>'
                   f'{PHASE_ROMAN[i]} · {htmllib.escape(p["title"])}</a>')

    html = TEMPLATE
    repl = {
        "__TITLE__": htmllib.escape(model["title"]),
        "__DECK__": block(model["l0"], deco(model["l0"]), tag="p", cls="deck"),
        "__NAV__": "\n".join(nav),
        "__L1__": "\n".join(l1),
        "__FORCES_INTRO__": block(model["forces_intro"], deco(model["forces_intro"]), cls="lead"),
        "__FORCES__": "\n".join(forces),
        "__CYCLE__": block(model["cycle"], deco(model["cycle"]), cls="lead"),
        "__L2INTRO__": block(model["l2_intro"], deco(model["l2_intro"]), cls="lead"),
        "__PHASES__": phases,
        "__ONEMIN__": onemin,
        "__SOURCES__": "\n".join(src),
        "__DATA__": json.dumps(data, ensure_ascii=False),
    }
    for k, v in repl.items():
        html = html.replace(k, v)
    return html


# ----------------------------------------------------------------------------
# AUDIT: prove fidelity against the .md, reading the produced HTML.
# ----------------------------------------------------------------------------

def norm(t):
    t = htmllib.unescape(t)
    t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("–", "-")
    return re.sub(r"\s+", " ", t).strip()


def md_haystack(md_text):
    """All reader-facing text of the .md as one normalised string, for substring
    'is this verbatim?' checks. Drops the build-note blockquote and the
    [VISUAL]/[ACCENT] directives; keeps headings; strips only bold/backtick/list
    markers and turns [text](url) links into their text."""
    lines = [l for l in md_text.split("\n") if not l.strip().startswith(">")]
    body = "\n".join(lines)
    body = MARK_RE.sub("", body)
    body = body.replace("`", "")
    body = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", body)
    body = body.replace("**", "")
    body = re.sub(r"^\s{0,3}#{1,6}\s*", "", body, flags=re.M)
    body = re.sub(r"^\s*[-*]\s+", "", body, flags=re.M)
    body = re.sub(r"^\s*\d+\.\s+", "", body, flags=re.M)
    return norm(body)


def md_prose_corpus(md_text):
    """Reader PROSE sentences the build must reproduce verbatim. Headings, the
    blockquote build-note, and the Sources citations are excluded; the **bold
    field labels** (Role./Revenue source./...) are dropped so only body prose is
    compared (the labels are rendered as styled micro-labels, not prose)."""
    kept, in_sources = [], False
    for ln in md_text.split("\n"):
        s = ln.strip()
        if s.startswith("#"):
            in_sources = s.startswith("## Sources")
            continue
        if in_sources or s.startswith(">"):
            continue
        kept.append(ln)
    sents = []
    for blk in split_blocks(kept):
        raw = strip_markers(blk["raw"])
        if not raw:
            continue
        body = norm(split_lead(raw)[1])  # drop any leading bold label
        for piece in re.split(r"(?<=[.:])\s+|\s+/\s+", body):
            piece = piece.strip().lstrip("/").strip()
            if len(piece) >= 12:
                sents.append(piece)
    return sents


def build_prose_chunks(html_text):
    """Every verbatim prose string the build presents lives in a data-src
    attribute (all prose is rendered inline; the DATA blob holds no prose)."""
    return [htmllib.unescape(m.group(1)) for m in re.finditer(r'data-src="([^"]*)"', html_text)
            if htmllib.unescape(m.group(1)).strip()]


def audit(html_text, md_text):
    hay = md_haystack(md_text)
    chunks = build_prose_chunks(html_text)
    build_join = norm(" ".join(chunks))
    problems = []

    # A) no paraphrase / no addition: every prose chunk the build shows must be
    #    a verbatim substring of the source markdown.
    for ch in chunks:
        if norm(ch) not in hay:
            problems.append(("NOT-IN-SOURCE", ch[:140]))

    # B) nothing dropped: every prose sentence of the source must appear in the
    #    build's verbatim text.
    for sent in md_prose_corpus(md_text):
        if sent not in build_join:
            problems.append(("MISSING-FROM-BUILD", sent[:140]))

    return problems


# ----------------------------------------------------------------------------
TEMPLATE = (ROOT / "primer_template.html").read_text(encoding="utf-8")


def main():
    md = SRC_TECH.read_text(encoding="utf-8")
    model = parse_tech(md)
    out = render(model)
    OUT_TECH.write_text(out, encoding="utf-8")
    print(f"wrote {OUT_TECH} ({len(out)} bytes), {sum(len(p['companies']) for p in model['phases'])} companies")
    if "--audit" in sys.argv:
        problems = audit(out, md)
        if not problems:
            print("AUDIT PASS: every approved sentence is present verbatim; no paraphrase detected.")
        else:
            print(f"AUDIT FAIL: {len(problems)} issue(s):")
            for kind, txt in problems[:40]:
                print(f"  [{kind}] {txt}")
            sys.exit(1)


if __name__ == "__main__":
    main()
