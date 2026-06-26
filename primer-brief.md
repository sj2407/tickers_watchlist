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

**Visual build: ATTEMPTED AND REJECTED.** A first build (`primer.html`) re-typed the content into
a JS data model and paraphrased it. The user caught this: the text drifted from the approved
wording (e.g. the L1 "compute" explainer read "The raw work AI does..." instead of the approved
"An AI model is a huge collection of numbers..."). That approach is wrong. The visual layer is good
(supply-chain diagram, phase/company drawers, market-share bars, scenario toggles, drill-down) and
can be reused as *interaction* reference, but its TEXT must be thrown out and replaced verbatim.
See section 12 for how to do it correctly.

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
