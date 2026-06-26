# Primer Brief: the "catch up on a sector" document

This is the spec for the `/primer` tab (and a candidate to become a reusable skill for
other sectors and domains). If you are a new session picking this up, read this first,
then read section 12 (the visual-build directive) and section 13 (next steps) before
touching anything.

The APPROVED, LOCKED content (the user reviewed every word) lives in three files:
`primer-content-tech.md`, `primer-content-healthcare.md`, `primer-content-frontier.md`.

> **PRIME DIRECTIVE for the visual build: the approved text is verbatim.** The build renders
> those three files word for word, same order, same flow. You ONLY add a visual layer on top
> (bold/highlight, color, diagrams, charts, the portfolio graph). You may NOT paraphrase,
> condense, reorder, substitute, or delete a single sentence in the first draft. See section 12.
> `primer.html` is a REJECTED prototype that broke this rule (it paraphrased); use it only for
> visual/interaction ideas, never for its words.

---

## 1. The goal, in one sentence

Take a smart person who knows nothing about a sector, have them read this, and leave them
with a genuinely good grasp of the ecosystem and the companies in it: the dynamics, the
landscape, how the pieces connect, what drives each player, and where each one fits in the
bigger picture.

## 2. The success test (use this to judge any draft)

A smart non-expert finishes the document and can, unprompted:
- explain how the sector works as a system (its main forces and how it booms or busts),
- place any company in that system and say what role it plays,
- name the few things that actually drive each company,
- and understand the key terms because the document made them self-evident, not because
  it defined them in a glossary.

The goal is understanding of dynamics, landscape, drivers, competitive position, catalysts,
and important KPIs. It is NOT granular financial metrics or price targets.

## 3. Audience and voice

- **Reader:** intelligent and capable, but not an expert in this field. Treat them as smart.
- **Tone:** clear and direct. Never condescending, never dumbed down. Do not over-simplify
  to the point of saying nothing.
- It should be a document someone returns to repeatedly, and could proudly share with a
  friend outside finance.

## 4. Hard content rules

0. **Every sentence must earn its place. This is the paramount rule.** Each sentence carries
   a specific fact, mechanism, number, or distinction the reader needs. No filler, no vague
   connective summaries, no restating the obvious. "The tools make the factories" is banned:
   it is imprecise (equipment makes chips, not factories) and it teaches nothing. Write the
   version with content in it ("equipment companies sell the machines a foundry uses to etch
   and pattern silicon into chips"). Prefer concrete nouns and precise verbs over hand-waving.
   If a sentence does not add something, cut it. Density and precision over volume.
1. **No em dashes (—), anywhere the reader sees text.** Use commas, semicolons, periods,
   colons, or parentheses. En dashes for numeric ranges (for example 5-8%) are fine.
2. **Do not force analogies.** Use one only when it genuinely makes something clearer.
   Never stretch a single metaphor across the whole document. The moment a metaphor
   starts to strain (the old "spine and parallel feeders" framing is the cautionary
   example), drop it and explain the real relationship in plain words. Clarity beats a
   tidy metaphor.
3. **Explain mechanisms, not jargon.** Say how something actually works (why a GPU beats a
   normal chip for AI; how a GLP-1 drug causes weight loss; why memory is a violent
   commodity cycle). A term is "defined" when the surrounding explanation makes it obvious.
4. **Size every competitive claim.** Whenever you say a company leads or competes, give the
   share of the pie (for example "roughly 70% of the foundry market", "the number two in
   HBM at about 20%"). "Big" and "dominant" without a number is not allowed.
5. **Research facts, do not recall them.** All market shares, mechanisms, and figures come
   from live web search and are sourced at the bottom. Never state a financial fact from
   memory. (This matches the project's standing "no training-data facts" rule.)
6. **Cut useless abstractions.** Do not include a generic "moat" line that says nothing.
   Explain the actual competitive dynamic instead (the real reason a customer can or cannot
   leave).
7. **Lead with the system, then the company.** Ecosystem dynamics come before any company.
   The reader should understand the board before meeting the players.
8. **No condescending scaffolding.** Do not tell the reader how to read ("read this first").
   Do not over-explain the obvious. The reader is smart; respect that.
9. **Define every technical term the first time it appears, in place.** If a full sentence
   would break the flow, put a short definition in parentheses. Terms that must be defined
   include at least: wafer, transistor, CPU, GPU, foundry, node and leading-edge, DRAM, NAND,
   HBM, inference, CUDA, ASIC (custom chip), transceiver, VMware. Never use a technical word
   in passing without explaining it.
10. **Name the players.** Never write "the top makers", "several rivals", or "others" without
    naming them and giving their shares. Vague competitive language is banned. The reader must
    finish understanding the competitive landscape: who the players are and how big each is.
11. **Lead with the plain truth, then elaborate.** State the simple point first ("ASML is the
    only company that makes the machines for the most advanced chips, so it sets its own
    prices"), then add detail. Avoid clanky, abstract constructions.
12. **Precise even at the cost of slight repetition.** Say what an action is performed on
    ("etches circuit patterns onto the silicon wafer", not "etches layers"). Specificity wins.
13. **Explain the dynamics between players, for every name, whether or not it is in the
    portfolio.** Who competes with whom, on what part of their business, and where each one's
    advantage lies. The reader should understand the rivalries, not just a list of companies.
14. **Demand framing.** When explaining who wants the product, describe where demand actually
    comes from in general first (for AI, the frontier labs and enterprises adopting AI), then,
    only after, point to the specific portfolio names with "in your portfolio". Never make the
    general explanation sound like it was built around the portfolio.

## 5. Information architecture (hierarchy)

Strictly top down. Sector first, then ecosystem, then phase or role, then company.

- **L0 - The picture.** One short passage: what this whole sector is a bet on.
- **L1 - How the ecosystem works.** The dynamics first. Why it exists (the demand), the
  shape of how the pieces fit together (described plainly, not forced into a metaphor), the
  few forces that move every stock in it, and how to tell a boom from a bust.
- **L2 - The phases or roles.** Each step or role in the sector, explained as a unit:
  what it is for, what goes in and comes out, why power and profit concentrate there (or do
  not), the KPIs to watch, and who competes with their share of the pie.
- **L3 - The companies.** Drill-down per company. The header is **Name (TICKER)**. Every
  company, with no exceptions, carries all of these fields:
  - **Role:** what it does, in the context of its phase.
  - **Revenue source:** how it earns, and the one to three real business drivers.
  - **Competitive landscape:** the named rivals and their market shares, this company's own
    share, and how they compete (which part of the business overlaps). Never vague.
  - **Moat:** this company's specific, durable advantage, or an honest note that it has little
    (a commodity). Not a generic abstraction; the concrete reason it is or is not replaceable.
  - **Indicators to watch:** the few numbers that tell you how it is doing.
  - **Catalysts:** the events that move it.
  - **Worst / Base / Best:** qualitative trajectories driven by macro and company factors, not
    price predictions, each with the factor that would cause it.
  - **Supply links:** which other holdings this name supplies, and which supply it. These are the
    edges of the portfolio supply-chain graph (see section 6). Only real, established relationships
    count; a name with none is genuinely isolated, which is itself information. Storing the edges on
    the record keeps the graph append/delete-friendly.

  Per-phase template (L2): the **role** of the step, where the **profit concentrates** and
  why, the **indicators to watch**, and the **competitive landscape** of that step (named
  players and shares). When a phase contains two business models that compete (for example
  merchant chips versus custom chips), explain that rivalry at the phase level before the
  companies.

Sectors are separate. Do not mix one sector's value chain into another's. (Healthcare is
its own sector with its own dynamics; it does not belong inside the technology chain.)

## 6. Visual and interaction requirements (the document must be visual, not a wall of text or cards)

- **Diagrams do the heavy lifting.** The connections between parts are shown, with real
  directional arrows and clear labels, not described in a list of cards.
- **Color coding** is consistent: each phase or group has its own color, used on its node,
  its arrow, its share chart, and its company cards.
- **Show the pie.** Market shares appear as small bar or proportion visuals, not only as
  numbers in prose.
- **Show the forces.** The ecosystem-level dynamics get a visual (for example a compact
  dashboard of the few forces that move the sector).
- **Two-level drill-down**, not a long scroll of cards: tap a phase for its explainer, tap a
  company for its detail. One detail open at a time.
- **A portfolio supply-chain graph.** Beyond the general ecosystem diagram, a view specific to the
  holdings: each owned name is a node, directed arrows mean "supplies / sells to," so the reader
  sees who depends on whom inside their own book (for example ASML to TSMC to Nvidia to CoreWeave).
  Names with no real supply relationship are drawn as isolated, which itself tells the reader how
  much of the book is one interdependent system versus standalone bets. Edges come from each
  company's Supply links field, so adding or removing a holding updates the graph automatically.
- **High contrast and readability.** Bright, legible text. No grey-on-dark mush.
- **Self-contained and themeable.** Inline SVG icons, not sourced or copyrighted images, so
  it works offline, scales cleanly, and can be restyled to match the app.
- **Responsive.** Works on a phone and reads well wider for sharing.

## 7. Maintenance model

- **One record per company.** Adding or removing a name is editing one entry. Never a full
  rebuild.
- **Evergreen.** This is not refreshed daily. It changes only when the universe changes, and
  then only by appending or deleting the affected entries.

## 8. Current scope (this instance: the watchlist)

**Group by the canonical theme taxonomy, do not invent your own.** The source of truth is
the `theme` field in `config.yaml`, which the pipeline rolls up into
`snapshot.portfolio.composition`. The primer's phases and groups must match those theme
names exactly, so the primer and the app never disagree. Today's themes:

- **Technology, the AI compute build-out** (the connected set):
  - `semicap equipment` (the toolmakers): ASML, AMAT, LRCX, KLAC
  - `foundry` (the factory): TSM
  - `memory` (the feed): MU, SNDK
  - `AI silicon` (the brains): NVDA, AVGO, MRVL
  - `semiconductor IP` (the design ingredients, a small adjacent role): CEVA
  - `optical/connectivity` (the wiring): COHR, LITE, CRDO
  - `AI infrastructure` (the cloud / the landlord): CRWV
  - `software` (the application layer): NOW, CRWD
- **Technology, frontier and enabling tech** (each a standalone context, NOT part of the AI
  chain): `rare-earth materials` (MP), `quantum computing` (IONQ), `lidar` (OUST).
- **Healthcare**: `healthcare/GLP-1`, the metabolic ecosystem: drugmakers (LLY) and consumer
  access and telehealth (HIMS), with the drug mechanism explained.

The earlier mistake was putting healthcare and raw materials inside the AI chain. They are
separate. When the universe changes, the theme tag is added in `config.yaml` first, then the
primer entry is appended to match.

## 9. Process

1. Write the content for a sector first, researched and sourced, to the rules above. Review
   the substance before building visuals.
2. Build the visual, interactive version on top of approved content.
3. Repeat per sector or ecosystem.
4. Fact-check sweep on every figure.
5. Integrate as the `/primer` tab. Keep content and presentation separable so the content
   can be reused.

Deliverable for review at each step is a standalone HTML file, opened directly in a browser,
before anything is wired into the app.

## 10. Anti-patterns (mistakes already made, do not repeat)

- Mixing sectors (healthcare or raw materials placed inside the AI chain).
- A stack of text cards instead of a real diagram with arrows and color.
- Low-contrast grey text that is hard to read.
- Thin definitions and jargon with no mechanism ("fabless means it designs but does not
  manufacture" teaches nothing on its own).
- Competitive claims with no market share.
- Forcing one analogy across the whole document until it stops making sense.
- Em dashes in reader-facing text.
- Stating figures from memory instead of researching and sourcing them.

## 11. Status

**Content phase: COMPLETE and reviewed by the user (checkpoint locked).** All 22 names covered
to the standard in this brief, researched and sourced, em-dash free, with competitive landscape,
market share, moat, and supply links per company.
- Brief: this file (rules 0-14, templates, taxonomy, portfolio-graph requirement, all current).
- Tech content (17 names): `primer-content-tech.md`. L1 rewritten as a plain causal chain
  (compute needs GPUs need a designer, a foundry, and equipment; a working machine adds memory
  and interconnect; machines fill data centers; data centers are rented as cloud; demand comes
  from AI labs and software). No forced metaphor.
- Healthcare content (LLY, HIMS): `primer-content-healthcare.md`. The GLP-1 ecosystem with the
  drug mechanism explained.
- Frontier content (MP, IONQ, OUST): `primer-content-frontier.md`. Three standalone bets.

**Visual build, TECHNOLOGY: BUILT, REVIEWED, APPROVED, LOCKED** (`primer-tech.html`, generated by
`build_primer.py` from `primer_template.html`). The earlier `primer.html` was rejected for
paraphrasing (it retyped content into a JS model: "The raw work AI does..." instead of the approved
"An AI model is a huge collection of numbers..."). The locked build avoids that by lifting literal
bytes from the `.md` + an `--audit` that proves verbatim fidelity. Healthcare and Frontier are built
on the same blueprint. **The full, mandatory blueprint is section 14 below — read it before building
any new sector.**

---

## 12. The visual-build directive (READ BEFORE BUILDING ANYTHING)

The three content files are the approved, locked text. The user reviewed every word. They are the
literal source. The build is a presentation layer over them, nothing more.

**First-draft rule, absolute:** render the content text VERBATIM. Same words, same sentences, same
order, same flow, same structure. Then ADD a visual layer on top, and only that:
- bold and highlight the important phrases,
- color-code by phase / theme (use the same accents across diagram, chart, and text),
- add diagrams, charts, market-share bars, and the portfolio supply-chain graph, all BUILT FROM
  the figures and relationships already written in the text,
- icons.

You may NOT, in the first draft: paraphrase, condense, shorten, reword, reorder, merge, split,
substitute, or delete any sentence. If you find yourself typing the content into a JS object or
rewording for "flow", STOP. That is the exact mistake that lost and drifted the text. Instead,
consume the markdown as-is (render the markdown to HTML, then decorate it), or copy each sentence
character for character. Before showing the user, AUDIT the build against the content files for
verbatim fidelity (the rendered prose must match the `.md` word for word). Only after the user
approves the first draft may edits be proposed, and then sentence by sentence with their sign-off.

## 13. Next steps (immediate, for the new session)

1. **Build the visual document by rendering the three content `.md` files verbatim**, adding the
   visual layer on top (bold, color, diagrams, charts, the portfolio supply-chain graph from the
   `theme` taxonomy and the per-company supply links). Change no words. Lose nothing.
2. **Deliver as a standalone HTML** the user opens directly in a browser, for review, before any
   app integration. Verify it renders (screenshots) and audit it for verbatim fidelity first.
3. **Then integrate** as the `/primer` tab (matches the app's dark theme; see sections 5-7).
4. Apply the same to all three sections (Tech, Healthcare, Frontier) and the portfolio graph.

Reusable interaction ideas from the rejected `primer.html`: the SVG supply-chain diagram with
color-coded phase boxes and supplier arrows; tap a phase for a drawer, tap a company for a drawer;
market-share bars with the owned name highlighted; a Worst/Base/Best toggle; the supply-link edges.
Keep the *mechanics*, replace the *text* with the verbatim content.

---

## 14. The visual-build blueprint (LOCKED — follow this for every new sector)

The Technology section was built, reviewed, and approved by the user. This is the blueprint a new
session MUST follow when building Healthcare, Frontier, or any future sector. Do not reinvent it.

### 14.1 The toolchain (in repo)
- **`build_primer.py`** — the generator. It PARSES the approved `primer-content-<sector>.md` and
  lifts every sentence as a LITERAL substring; it never retypes prose into a JS/Python object
  (that retyping is exactly what got the first build rejected). Decoration only ever WRAPS existing
  text in markup, so the characters are never altered.
- **`primer_template.html`** — the shared shell: all CSS, the guarded JS (diagrams/collapsibles/nav
  build only if their elements exist), and `__NAV__` / `__MAIN__` / `__DATA__` placeholders. Reuse
  it for every sector; do not fork the CSS.
- **Outputs:** `primer-<sector>.html`, one standalone file per sector, opened directly in a browser
  for review before any app integration.
- **The audit is mandatory:** `python3 build_primer.py --audit` re-reads each produced HTML and
  proves (A) every prose chunk shown is a verbatim substring of the `.md` (no paraphrase/addition)
  and (B) every source prose sentence appears in the build (nothing dropped). It must print
  `AUDIT PASS` before the build is shown to the user. The audit drops the **bold field labels**
  (Role./Moat./...) from the completeness corpus because they are rendered as styled micro-labels.

### 14.2 Verbatim handling (the prime directive, mechanised)
- `[VISUAL: ...]` / `[ACCENT: ...]` markers in the `.md` are build directives: consume them (place
  the real visual there), never render them as text.
- Worst/Base/Best is ONE verbatim sentence split on its literal " / " into three parts (red/grey/
  green rows). The audit splits the corpus on " / " too.
- Supply links: Tech has no per-company field, so its edges are DERIVED (the `SUPPLIES` dict) and
  shown as a derived field (not audited as prose). Healthcare/Frontier DO carry a verbatim
  "Supply links" field, so render it as a normal field (and it IS audited).

### 14.3 The design system (what "delivering" looks like — all of these are required)
- **Structure must be visible at a glance.** Sticky left contents rail (Roman I, II, III… top
  level; numbered phases/sub-sections with a colour dot each). Ghosted-but-VISIBLE section numerals
  (outline + glow in the accent — NOT `surface-2`, that reads invisible). Every section: eyebrow
  kicker → big serif H2. The reader must see "this is the phase, these are the companies in it".
- **8-accent palette**, vivid and AA on near-black, neighbours differ in hue: equipment magenta
  `#e879c9` · foundry teal `#2dd4bf` · memory violet `#a78bfa` · AI-silicon blue `#5ea8ff` · IP
  green `#4ade80` · optical rose `#fb7185` · cloud amber `#fbbf63` · software sky `#7dd3fc`. Each
  theme's accent is used identically on its node, arrow, chart and section (`style="--cat:…"`).
  Frontier reuses amber/violet/teal per its `[ACCENT]` markers.
- **Emphasis to draw the eye (not just numbers)** via one combined regex in `deco()` that only
  wraps: `.fig` = figures in COLOUR ONLY (no box/chip/border — the user rejected boxed numbers);
  `.ent` = competitor/company names, semibold bright (`ENTITIES` list); `.key` = key concept terms
  (monopoly/commodity/oligopoly/lock-in/price maker/leading edge…) italic+semibold (`TERMS` list).
- **Headers/labels are at least as big as body text**, never smaller. Field micro-labels
  (ROLE/MOAT/…) are 15.5px (= body), uppercase mono in the accent.
- **Charts from figures already in the text.** Share-of-a-whole → DONUT (owned slice in the accent,
  centre shows the owned %, direct-labelled legend); a revenue RANKING in $B → filled high-contrast
  horizontal BARS (`.bar-fill` MUST be `display:block` or it collapses to 0×0). A donut may need a
  derived "others/rest" remainder slice to close to 100%; label it "others"/"Rest of market".
- **Ticker cards are collapsible `<details>`** (collapsed by default; per-group "Expand all";
  tapping a ticker in a diagram opens its card). Lets the reader scan industries and open only the
  names they care about. Forces are distinctly-coloured cards. High contrast; responsive (nav hides
  < 1040px). Self-contained inline SVG; fonts via CDN degrade gracefully.

### 14.4 Per-sector structure differs — adapt the parser, reuse the components
The three content files have DIFFERENT shapes; the design components are shared, the parse/assemble
is per-sector:
- **Tech:** L0 → L1 causal chain (concept blocks + dependency map) → four forces → reading-the-cycle
  gauges → L2/L3 phases (8) each with companies → one-minute → sources.
- **Healthcare:** L0 → L1 (Why it exists / How the drugs work / The landscape / The forces [numbered
  cards] / Indicators) → companies (LLY, HIMS) under the single `healthcare/GLP-1` theme. No phases.
  Charts: Lilly vs Novo donut; a small 3-effect GLP-1 mechanism diagram for the `[VISUAL]`.
- **Frontier:** L0 → three INDEPENDENT theme sections (`rare-earth materials` / `quantum computing`
  / `lidar`), each a "The field" intro + one company, drawn standalone (the L0 says read each on its
  own). Charts where a share figure exists (MP: China ~90% magnet share; OUST: Hesai/RoboSense).

### 14.5 Verification (the workflow that proved it)
Build → `--audit` (must PASS) → open in browser. NOTE: preview screenshots go black at non-zero
scroll on these very tall pages; verify a section by temporarily `display:none`-ing the earlier
sections so the target renders in the first viewport. Confirm: numerals visible, bars filled,
figures colour-only, names/terms emphasised, labels ≥ body, cards collapse/expand, diagram jumps
open cards. Only then show the user.
