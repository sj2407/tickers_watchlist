# Field guide, Part 1: The AI build-out

> Content draft for the `/primer` tab. Ecosystem first, then companies. Every market-share
> figure is sourced (see end). No em dashes. No forced metaphors. Every technical term is
> defined in place. Every company carries its competitive landscape, market share, and moat.
> Visual cues in **[brackets]** mark where the built version carries a diagram or chart.
> Groups follow the `theme` taxonomy in `config.yaml`.

---

## L0 · What you are looking at

Almost everything you own in technology is one bet: that the world keeps spending enormous sums
to build and run artificial intelligence. The rest of this section explains what building and
running AI actually requires, following the need from one step to the next, and places each
company at the exact job it does.

---

## L1 · How the ecosystem works

Start from what AI needs, and follow what each thing in turn requires.

**Compute.** An AI model is a huge collection of numbers. Training it, and later running it for
users (called inference), means doing one kind of arithmetic, multiplying and adding numbers,
trillions of times per second. That raw arithmetic is called compute. A more capable model needs
more compute. Every company below exists to supply compute or something compute depends on.

**The chip.** Compute happens on a chip: a fingernail-sized piece of silicon holding billions of
microscopic on-off switches called transistors. Toggling those switches in patterns is how a chip
does arithmetic. The type matters. A CPU (central processing unit, the general-purpose chip in a
normal computer) does one complex task at a time. A GPU (graphics processing unit) does thousands
of identical simple calculations at once. AI's arithmetic is exactly thousands of identical simple
calculations, so AI runs on GPUs, and Nvidia designs the ones almost everyone uses.

**Designing a chip and making a chip are separate jobs.** Nvidia, Broadcom and Marvell design
chips and own no factories. The factory that physically builds a chip is called a foundry, and
TSMC is the one that matters. A foundry builds chips on wafers (thin round slices of silicon, each
about the size of a dinner plate, on which hundreds of chips are printed at once and then cut
apart). A foundry cannot operate without the machines that print and etch circuit patterns onto
those wafers, which is what the equipment makers (ASML, Applied Materials, Lam, KLA) sell. So a
single finished chip already requires three companies: a designer, a foundry, and the foundry's
equipment supplier.

**One chip is never enough, so two more parts get added.** A frontier model needs far more compute
than any single chip can deliver, so thousands of chips are wired together to act as one machine.
That requires two more components alongside the processors:
- **Memory.** A processor sits idle unless it is fed data fast enough to stay busy. Memory chips
  hold that data and deliver it. The AI-critical type, HBM (high-bandwidth memory), is built by
  bonding several thin memory chips into a vertical stack and placing that stack right next to the
  processor, so data has a very short distance to travel and arrives fast. Micron and SanDisk make
  memory.
- **Interconnect.** For thousands of chips to behave as one, they must pass data to each other at
  very high speed. Across a few feet inside a rack this is done with electrical cables (Credo).
  Across a building it is done with light sent through glass fiber, which the optical companies
  (Coherent, Lumentum) make.

**The data center.** Thousands of these wired-together chips, with their memory, interconnect,
power and cooling, fill a purpose-built warehouse called a data center. Building and running one
costs billions.

**Cloud.** Almost no company builds its own data center, so it rents compute by the hour from one
that has. That rental business is the cloud. The general clouds (Amazon, Microsoft, Google) rent
every kind of computing. A newer kind, called a neocloud, rents AI chips and little else.

**Where the demand comes from.** The biggest pull on all of this is the frontier AI labs (OpenAI,
Anthropic, Google DeepMind, Meta, xAI), which train and run ever-larger models, alongside the many
ordinary companies adding AI to their products. The cloud giants (Microsoft, Amazon, Google, Meta)
spend the money on the hardware to serve that demand, which is why their spending is the number
that moves the whole sector. In your portfolio, the software names ServiceNow (NOW) and CrowdStrike
(CRWD) sit on this demand side: they sell business software, add AI features to it, and buy compute
rather than build it.

**The chain, stated once:** AI needs compute. Compute needs GPUs. A GPU needs a designer, a foundry
to manufacture it, and the equipment that lets the foundry exist. A working AI machine adds memory
and interconnect to those GPUs. The machines fill data centers. The data centers are rented out as
cloud. Demand comes from the AI labs and from companies putting AI into software.

**[VISUAL: a dependency map. Each named thing (compute, GPU, designer, foundry, equipment, memory,
interconnect, data center, cloud, demand) is a labelled node. Arrows read "requires". Tapping a
node shows its one-line definition.]**

### The four forces that move every stock
Almost any large move in these names traces to one of four forces.

1. **The AI capital-spending cycle.** A handful of giant buyers (Microsoft, Amazon, Google, Meta,
   and the AI labs) set how many tens of billions they will spend on AI hardware each year. When
   that number rises, money flows to every company in the chain. When they pause to absorb what
   they bought, every company feels it. This is the single most important number in the sector.
2. **The memory price cycle.** Memory is a commodity made by only three firms, so its price swings
   hard between shortage and glut. The same chip can be highly profitable one year and sold below
   cost the next. This cycle drives the memory names and the equipment names that sell to them.
3. **Export controls and geography.** The most advanced chips and tools are treated as strategic
   assets. US limits on selling to China, and the concentration of the best factories in Taiwan,
   are standing risks that move these stocks on a single headline.
4. **Monopoly versus commodity.** Some steps have only one capable supplier, which makes that
   company a price maker. ASML is the only company that makes the machines for the most advanced
   chips, and TSMC is the only foundry that can manufacture them at the cutting edge, so both set
   their own prices and earn the fattest margins. Other steps have several capable suppliers, for
   example memory (three makers) and most software (many rivals), so those companies compete on
   price and win on cost and execution instead. For any name here, the first question is simply: is
   it the only option, or one of several.

### Reading the cycle at a glance
Four numbers tell you whether the sector is expanding or contracting: are the big buyers raising or
cutting AI capital spending, are equipment order books filling or emptying, are memory prices rising
or falling, and are chip lead times stretching or shrinking. **[VISUAL: a gauge strip of these four.]**

---

## L2 + L3 · The phases and the companies in them

Each phase covers the same ground: the role of the step, where the profit concentrates and why, the
indicators to watch, and the competitive landscape with named players and shares. Then each company,
with its role, revenue source, competitive landscape, moat, indicators, catalysts, and scenarios.
Groups follow the `theme` taxonomy.

---

### Phase · Chip-making equipment   `theme: semicap equipment`
**[ACCENT: sky]**

**The role.** Make and sell the machines a foundry uses to print and etch circuit patterns onto
silicon wafers. A chip is built in hundreds of these steps, so without this equipment no chip exists.

**Where the profit concentrates.** A few specific steps can be done by only one company's machine,
which makes parts of this phase a monopoly. The phase also sells to every chipmaker at once, so it
earns regardless of which chip company wins.

**Indicators to watch.** Equipment order bookings, the customers' capital-spending plans, the share
of sales exposed to China export bans, and service revenue (the recurring part).

**The competitive landscape.** Five firms (ASML, Applied Materials, Lam Research, Tokyo Electron,
KLA) control roughly 70% of all chip-equipment spending, and each owns a different step, so they
rarely compete head to head. You own four of the five. **[VISUAL: share bar of the big five.]**

#### ASML (ASML)
- **Role.** Makes lithography machines, the tools that use light to print circuit patterns onto
  silicon wafers. Its top machine, EUV (extreme ultraviolet lithography), is the only way to make
  the most advanced chips.
- **Revenue source.** Sells a small number of machines at 150 to 350 million dollars each, plus
  ongoing service. Demand comes from the race to denser chips, which forces every leading chipmaker
  to keep buying.
- **Competitive landscape.** In EUV it has 100% share; no other company can build the machine. In
  older, simpler lithography (called DUV, deep ultraviolet), Canon and Nikon of Japan compete, but
  those tools cannot make leading-edge chips.
- **Moat.** A monopoly built over decades, and dependent on a supply chain only ASML has assembled
  (its precision optics come from a single partner, Carl Zeiss). A rival would need a decade and
  tens of billions of dollars to attempt a copy.
- **Indicators to watch.** EUV unit shipments, China revenue share (large and exposed to bans),
  order backlog, and uptake of its next machine, High-NA EUV.
- **Catalysts.** Capital-spending up-cycles, the High-NA ramp, changes to China rules.
- **Worst / Base / Best.** A chip downturn plus tighter China bans delay orders for a year or two. /
  AI keeps the order book full and the monopoly compounds. / High-NA becomes required for every
  advanced AI chip and ASML is the sector's hardest bottleneck.

#### Applied Materials (AMAT)
- **Role.** Makes many of the non-lithography machines: depositing thin films onto the wafer,
  etching patterns into it, and implanting ions to change the silicon's properties. The widest
  product range in the industry.
- **Revenue source.** Machines plus a large recurring service business on a big installed base.
  Driven by total factory spending and by advanced packaging (joining several finished chips into
  one part, which AI chips increasingly need).
- **Competitive landscape.** Competes with Lam Research and Tokyo Electron across deposition and
  etch, and overlaps with KLA in some measurement. Roughly 26 billion dollars of revenue in fiscal
  2025, among the top two equipment makers.
- **Moat.** Breadth and scale: it sells more types of tool than anyone, so customers buy many
  machines from one vendor, and its huge installed base throws off steady, high-margin service
  revenue.
- **Indicators to watch.** Equipment spending, advanced-packaging traction, China exposure, service
  revenue.
- **Catalysts.** The capital cycle, and new transistor designs that pack more switches into the same
  space and need more of its tools per chip.
- **Worst / Base / Best.** A memory glut and a China pullback shrink budgets. / Broad exposure rides
  AI spending and service smooths the cycle. / Packaging and new transistor designs lift its
  tools-per-chip and it gains share.

#### Lam Research (LRCX)
- **Role.** Specializes in two steps performed on the wafer: etching (carving patterns into it) and
  deposition (laying down ultra-thin layers on it), with unusual strength in memory chips, which are
  built as tall vertical stacks of layers.
- **Revenue source.** Machines plus service, weighted toward memory. Driven by memory factory
  spending and by the growing number of etch and deposition steps per chip.
- **Competitive landscape.** Competes directly with Applied Materials and Tokyo Electron in etch and
  deposition. Roughly 17 billion dollars of revenue, a top-four equipment maker.
- **Moat.** Deep specialization and a leading position in etch and deposition, especially for the
  tall 3D structures in modern memory, plus a large installed base and service relationships.
- **Indicators to watch.** Memory capital spending, the number of etch and deposition steps per
  advanced chip, China exposure.
- **Catalysts.** The HBM and 3D-memory build-out, which is heavy on its tools.
- **Worst / Base / Best.** A memory downturn, its biggest exposure, hits hard. / More vertical layers
  keep demand growing through cycles. / HBM drives a multi-year up-cycle in its tools.

#### KLA (KLAC)
- **Role.** Inspection. Its machines scan chips during manufacturing to find defects too small to see
  and to verify that everything is built to specification. One missed defect can ruin an expensive
  wafer that holds hundreds of chips.
- **Revenue source.** High-margin machines plus service. As chips get more complex, mistakes get
  costlier, so inspection spending grows faster than the rest of equipment.
- **Competitive landscape.** Dominant in inspection and process control, with no close rival in its
  core niche; Applied Materials competes in some measurement. Roughly 11 billion dollars of revenue,
  smaller than the others but the most profitable.
- **Moat.** A near-monopoly in inspection built on decades of accumulated defect-detection know-how
  and data, which is why its margins are the highest in equipment.
- **Indicators to watch.** Inspection intensity at new chip generations, capital spending, margins.
- **Catalysts.** AI-chip yield problems that make inspection unavoidable.
- **Worst / Base / Best.** A spending pause trims inspection and margins compress. / Complexity makes
  inspection outgrow the market. / Yields become make-or-break and KLA gains share and pricing.

---

### Phase · Foundry   `theme: foundry`
**[ACCENT: indigo]**

**The role.** Physically manufacture the chips that other companies designed, by building them on
silicon wafers using the equipment from the previous phase. This is the most capital-intensive and
technically hard step. "Leading edge" means the newest, densest, fastest generation of chip (each
generation is called a node, named for its size, like 3nm or 2nm), which only one or two factories
in the world can make.

**Where the profit concentrates.** A single leading-edge factory costs 20 to 40 billion dollars and
takes years to build, so few firms can compete and only one leads. That scarcity is the source of
pricing power for the whole chain.

**Indicators to watch.** Factory utilization, the mix of advanced versus older chips (advanced is far
higher margin), AI-packaging capacity, capital-spending guidance, gross margin.

**The competitive landscape.** One company dominates, and you own it.

#### TSMC (TSM)
- **Role.** Manufactures chips for almost everyone (Nvidia, Apple, AMD) and sells none of its own
  brand, so it competes with none of its customers and is the trusted neutral factory. It also leads
  the advanced packaging that fuses an AI chip and its HBM memory into a single part.
- **Revenue source.** Charges per wafer, with leading-edge work and AI packaging priced highest.
  Driven by AI demand and its scarce advanced capacity.
- **Competitive landscape.** Roughly 70% of the contract-manufacturing market and over 90% of
  leading-edge production. Samsung of South Korea is the only other firm attempting the leading edge,
  at mid-single-digit share, and Intel is trying to enter as a third source. Neither is close.
- **Moat.** Process leadership built up over years, enormous scale, a neutral position (it competes
  with no customer, so everyone trusts it), and the 30-billion-dollar-plus, multi-year barrier to
  building a rival fab.
- **Indicators to watch.** Advanced-node revenue share, AI-packaging capacity, capital spending,
  gross margin, customer concentration (Apple and Nvidia are large).
- **Catalysts.** The AI capital cycle, each new node ramp, pricing, and Taiwan geopolitics above all.
- **Worst / Base / Best.** A Taiwan shock or an AI digestion dents demand and re-rates it. / It stays
  the leader and advanced capacity stays sold out. / It prices scarce capacity for record margins
  with no credible rival.

---

### Phase · Memory   `theme: memory`
**[ACCENT: violet]**

**The role.** Feed the processors with data. Memory chips hold the numbers a processor works on and
deliver them fast. There are two kinds. DRAM (dynamic random-access memory) is the fast working
memory a processor reads and writes constantly, and it loses its contents when the power is off. NAND
flash is slower storage that keeps its contents without power (the chips inside SSDs and phones). For
AI the critical type is HBM, a stack of DRAM chips placed against the processor.

**Why this phase behaves differently.** Memory is a commodity, so the makers compete mostly on price
and the price swings violently between shortage and glut. The same chip can be very profitable or
loss-making depending on the year. The new twist: AI-grade HBM is scarcer and more profitable than
ordinary memory, which is reshaping the cycle.

**Indicators to watch.** Memory spot prices, the HBM supply-demand balance, bit-shipment growth, and
whether the makers hold capital-spending discipline rather than flooding the market.

**The competitive landscape.** DRAM is an oligopoly of three: SK Hynix (about 34%), Samsung (about
33%), and Micron (about 26%), both of South Korea except US-based Micron. HBM, the AI part, is led by
SK Hynix (about 60%), with Micron second (about 20%) and Samsung third (about 17%). NAND storage is
more crowded: Samsung leads (about 32%), then SK Hynix (about 19%), Kioxia of Japan (about 15%),
SanDisk (about 12%), and Micron (about 10%). You own Micron and SanDisk. **[VISUAL: DRAM, HBM, and
NAND share bars.]**

#### Micron (MU)
- **Role.** Makes DRAM, NAND, and crucially HBM for AI. The only memory maker based in the US.
- **Revenue source.** Sells memory by the bit, so profit swings with the price cycle. Driven by HBM
  demand and the DRAM price.
- **Competitive landscape.** One of the three DRAM makers (about 26%), and the clear number two in
  HBM (about 20%) behind SK Hynix (about 60%), ahead of Samsung. Its rivals are larger and Korean;
  Micron's distinction is being American.
- **Moat.** Limited, because memory is a commodity. What protects it is the structure of the market:
  only three firms can make DRAM, the capital barrier to a fourth is enormous, and being the one US
  maker matters for supply-security politics. The HBM up-cycle is currently giving it real, if
  cyclical, pricing power.
- **Indicators to watch.** HBM share and pricing, DRAM spot prices, capital spending, the rise of a
  Chinese maker (CXMT).
- **Catalysts.** The HBM up-cycle, qualifying on Nvidia's newest platforms, memory-price turns.
- **Worst / Base / Best.** A glut crushes prices and profit goes negative. / HBM tightens the market
  and lifts the cycle above past peaks. / AI keeps memory structurally short for a long up-cycle.

#### SanDisk (SNDK)
- **Role.** Makes NAND flash, the storage memory that keeps data with the power off. Recently spun
  out of Western Digital as its own listed company.
- **Revenue source.** Sells flash by the bit, living entirely by the NAND price cycle. Driven by
  storage demand, now including AI, against industry supply.
- **Competitive landscape.** About 12% of NAND, the fourth or fifth largest, behind Samsung (about
  32%), SK Hynix (about 19%), and Kioxia (about 15%), and near Micron (about 10%). NAND has more
  players than DRAM, so it is more competitive and lower margin.
- **Moat.** Weak, by design of the market: NAND is a commodity with five serious makers. What it has
  is scale and a long-standing manufacturing joint venture with Kioxia that shares the cost of
  factories. It is a higher-risk, cyclical bet, not a defended franchise.
- **Indicators to watch.** NAND spot prices, AI-storage demand, supply discipline, the costs of being
  newly independent.
- **Catalysts.** A NAND up-cycle, AI-driven storage growth.
- **Worst / Base / Best.** A NAND price crash pressures the young company. / AI storage firms the
  cycle for a focused pure-play. / Undersupply plus AI data growth drive a strong cycle and re-rating.

---

### Phase · Chip design   `theme: AI silicon`
**[ACCENT: emerald]**

**The role.** Decide what a chip does and lay out its circuits, then send that design to a foundry to
manufacture. These companies own no factories. This phase contains two business models that compete
for the same customer budget, and understanding that rivalry is the key to the whole phase.

A **merchant** designer makes one chip and sells it to everyone; Nvidia is the merchant giant. A
**custom** designer instead co-engineers a chip for a single large customer, almost always a cloud
giant that wants its own chip (called an ASIC, a chip built for one specific purpose) to avoid paying
Nvidia's high margins; Broadcom and Marvell lead this custom work. The rivalry that matters: every
custom chip a cloud giant builds with Broadcom or Marvell is compute it does not buy from Nvidia. So
the custom designers are the structural counterweight to Nvidia, and Nvidia's defense is that its
chips plus its software are easier than designing your own.

**Indicators to watch.** Data-center revenue growth, custom-chip program wins, the strength of
Nvidia's software lock-in, and how concentrated each designer's customers are.

**The competitive landscape.** Merchant GPUs: Nvidia roughly 86 to 92%, AMD roughly 5 to 8%, the rest
custom and others. Custom silicon: Broadcom roughly 55 to 70% (about 12 billion dollars of AI revenue
in 2025), Marvell roughly 15 to 35% (about 1.5 billion, but growing about 60% a year). Broadcom and
Marvell compete directly for custom programs; both compete indirectly with Nvidia for the cloud
giants' total spend. **[VISUAL: two share bars, merchant and custom.]**

#### Nvidia (NVDA)
- **Role.** Designs the GPUs that run AI, the networking that links thousands of them, and CUDA, the
  software developers use to program its chips (a parallel programming layer most AI code is written
  against).
- **Revenue source.** Sells chips and whole AI computers at high margins. Driven directly by how much
  the cloud giants spend.
- **Competitive landscape.** Roughly 86 to 92% of AI accelerators. Its only real merchant rival is
  AMD (about 5 to 8%); the bigger long-term threat is its own customers' custom chips, built with
  Broadcom and Marvell.
- **Moat.** The strongest in the chain after ASML and TSMC, and it is software, not silicon: CUDA. AI
  developers have written years of code against CUDA, and moving to another chip means rewriting it,
  so customers stay even when rivals are cheaper. On top of that sits a full-stack lead (chips,
  networking, and systems) and the fastest release cadence in the industry.
- **Indicators to watch.** Data-center revenue, customers' own-chip efforts, China policy, and the
  supply of advanced packaging and HBM that gate its output.
- **Catalysts.** Each new chip generation, buyer capital-spending guidance, China rules.
- **Worst / Base / Best.** Custom customer chips plus a spending pause slow growth and reset high
  expectations. / It stays the default and CUDA holds share as the market grows. / AI compounds for
  years and it sells whole systems and software, not just chips.

#### Broadcom (AVGO)
- **Role.** Two businesses. One co-designs custom AI chips for cloud giants like Google, the main
  alternative to buying Nvidia. The other is infrastructure software, anchored by VMware (software
  that lets one physical server run many separate virtual machines, used to run most corporate data
  centers). It also makes much of the networking that links AI chips.
- **Revenue source.** Custom-chip programs, networking chips, and software subscriptions. Driven by
  cloud giants wanting their own silicon, and by VMware.
- **Competitive landscape.** The clear leader in custom AI silicon (roughly 55 to 70%, about 12
  billion dollars of custom AI revenue in 2025), with Marvell the distant second. In networking it
  competes with Nvidia; in software, broadly with other enterprise vendors.
- **Moat.** The deepest custom-silicon engineering relationships with the handful of cloud giants
  (these are multi-year and very sticky once a chip is in production), strong networking IP, and the
  high switching cost of VMware software once a data center runs on it.
- **Indicators to watch.** Number and ramp of custom programs, customer concentration, networking
  share, software margins, the debt taken on for acquisitions.
- **Catalysts.** New hyperscaler design wins, VMware execution.
- **Worst / Base / Best.** A key custom customer pulls work in-house or delays, and chip cyclicality
  bites. / Custom silicon and software compound into a diversified AI winner. / Several hyperscaler
  programs scale at once and it becomes the clear number two in AI silicon.

#### Marvell (MRVL)
- **Role.** Like Broadcom, co-designs custom AI chips for cloud giants and makes the connectivity
  chips that move data around data centers, but smaller and more concentrated on this one opportunity.
- **Revenue source.** Custom-chip design wins plus connectivity and optics-interface chips. Driven by
  the AI build-out and a few large programs ramping.
- **Competitive landscape.** The number two in custom silicon (roughly 15 to 35%), a fraction of
  Broadcom's revenue today (about 1.5 billion versus 12 billion) but growing about 60% a year from a
  smaller base. It competes directly with Broadcom for these programs.
- **Moat.** Its own custom-silicon design wins, which are sticky once a chip ships, and strong
  connectivity and optical-interface IP. Its disadvantage versus Broadcom is scale: fewer programs and
  less engineering depth, so a single win or loss moves it more.
- **Indicators to watch.** Design-win timing (lumpy), customer concentration, share gains or losses
  versus Broadcom.
- **Catalysts.** New hyperscaler wins, more connectivity content per system.
- **Worst / Base / Best.** Design wins slip or Broadcom out-competes and revenue disappoints. / Custom
  programs ramp and connectivity grows with AI. / It takes a bigger slice of custom silicon and
  becomes a core AI-infrastructure name.

---

### Phase · Semiconductor IP   `theme: semiconductor IP`
**[ACCENT: emerald, lighter]**

**The role.** This is a different layer from chip design, and easy to confuse with it. These
companies do not design or sell whole chips. They design small, reusable circuit blocks (a Bluetooth
radio, a signal processor, an on-device AI engine) and license those blocks to chipmakers, who drop
them into their own chip designs and pay a royalty on every chip that ships. Think of it as selling
pre-made ingredients of a chip, not the chip. The customers are mostly makers of smaller chips for
phones, cars, and connected devices, not the data-center GPUs above.

**The competitive landscape.** Arm of the UK dominates chip IP overall (its instruction set is in
nearly every phone). The names you own here play in narrower corners Arm does not.

#### Ceva (CEVA)
- **Role.** Licenses reusable circuit blocks for wireless connectivity, signal processing, and
  on-device AI, and collects a small royalty on each chip that ships using them. It owns no factories
  and makes no chips of its own.
- **Revenue source.** Upfront license fees plus per-unit royalties that can run for years. Driven by
  the spread of smart, connected, AI-enabled devices.
- **Competitive landscape.** A small niche player. Arm is the giant of chip IP; Ceva is far smaller
  and focused on signal-processing and edge-AI blocks that Arm does not specialize in. Its other
  competition is customers who design such blocks in-house instead of licensing. AI was over 20% of
  its licensing revenue in 2025.
- **Moat.** Modest: a niche IP portfolio embedded inside customers' chips, plus a royalty stream that
  scales with their unit volumes. It is small and dependent on its customers' success, with a much
  larger rival in Arm, so the moat is a niche, not a fortress.
- **Indicators to watch.** New license signings (especially AI), the unit volumes of customers' chips
  that drive royalties, competition from Arm and from in-house designs.
- **Catalysts.** An on-device-AI royalty inflection across billions of devices.
- **Worst / Base / Best.** Device volumes stay soft while bigger players squeeze royalties. /
  Connected-device growth lifts royalties steadily. / On-device AI everywhere drives a royalty
  inflection.

---

### Phase · Interconnect and networking   `theme: optical/connectivity`
**[ACCENT: teal]**

**The role.** Carry data between chips fast enough that thousands of them behave as one machine. The
distance decides the method. Across a few feet inside a rack, electrical cables are cheaper and use
less power. Across a building, the signal is converted into light and sent through glass fiber, using
a part called a transceiver (a small plug that turns electrical data into light to send, and light
back into data to receive). Each time clusters get larger, the required speed roughly doubles, so
this phase upgrades constantly.

**Where the profit concentrates.** When clusters grow, moving data, not computing it, becomes the
bottleneck. In optics, companies that make their own laser chips, rather than buying them, keep more
of the value.

**Indicators to watch.** The transition to faster links (from 800 gigabits per second toward 1.6
terabits), cloud spending on networking, in-house laser-chip capability, and pricing pressure.

**The competitive landscape.** These companies are not interchangeable; they split by distance and by
integration. In optical transceivers the top five suppliers (Coherent, Lumentum, Broadcom, Accelink,
InnoLight) make roughly half a market growing from about 15.6 billion dollars in 2025 toward 25
billion by 2029. In short electrical cables, a separate niche, Credo invented the category and holds
about 88% of it. **[VISUAL: optics share bar, plus Credo's cable share.]**

#### Coherent (COHR)
- **Role.** Makes the optical transceivers that move data between machines as light, and the laser
  chips inside them.
- **Revenue source.** Optical components and transceivers, plus industrial lasers. Driven by AI
  bandwidth demand pushing faster transceivers.
- **Competitive landscape.** The transceiver-market leader at roughly 16%, ahead of Lumentum,
  Broadcom, InnoLight, and Accelink. The top five together make about half the market.
- **Moat.** Vertical integration: it makes its own laser chips (using a material called indium
  phosphide) rather than buying them, which protects its margin and supply when lasers are scarce.
  That, plus scale and breadth, is what separates it from rivals who assemble bought-in parts.
- **Indicators to watch.** The 800G-to-1.6T transition, datacom revenue, margins, acquisition debt,
  customer concentration.
- **Catalysts.** Each speed upgrade, AI-cluster build-outs.
- **Worst / Base / Best.** Pricing competition and cyclicality squeeze margins while debt weighs. /
  AI bandwidth drives faster transceivers and integration protects margin. / It becomes a top supplier
  for AI clusters as link speeds keep doubling.

#### Lumentum (LITE)
- **Role.** Like Coherent, makes optical parts that move data as light, plus lasers (including the
  arrays used for phone face-sensing). Data-center optics is its AI growth engine.
- **Revenue source.** Optics for cloud customers, plus telecom equipment and lasers. Driven by cloud
  spending on AI networking.
- **Competitive landscape.** A top-five optics supplier, smaller in data-center transceivers than
  Coherent, competing with Coherent and InnoLight. It carries a weaker legacy telecom business that
  has been a drag.
- **Moat.** Real but narrower than Coherent's: strong laser and optical IP and its own
  compound-semiconductor chips, but less scale and integration in datacom, and the telecom weight,
  make it the challenger rather than the leader here.
- **Indicators to watch.** Data-center optics growth against soft telecom, customer concentration, the
  speed transition.
- **Catalysts.** An AI optical-demand inflection where its laser tech wins share.
- **Worst / Base / Best.** Telecom stays weak and cloud orders are lumpy, stalling the recovery. /
  Data-center optics offsets soft telecom for a gradual recovery. / AI optical demand inflects and its
  tech wins share for a strong turnaround.

#### Credo (CRDO)
- **Role.** Makes power-efficient active electrical cables and the chips inside them for the short,
  high-speed links between chips in a rack, where heat and power, not distance, are the limit. A
  different job from the optical companies above, which handle the longer links.
- **Revenue source.** Sells these cables and connectivity chips, tied to cluster size. More chips per
  cluster means exponentially more of these short links.
- **Competitive landscape.** It invented the active-electrical-cable category and holds about 88% of
  it. Its direct rivals are Astera Labs and Marvell. It also competes indirectly with optical: if
  optics get cheap enough at short range, electrical cables lose ground.
- **Moat.** First-mover dominance in a niche it created, plus a power-efficiency edge that wins
  designs. The risk to the moat is that the niche is small and much larger players (Broadcom, Marvell)
  could push into it.
- **Indicators to watch.** Adoption rate, customer concentration, competition from bigger players,
  gross margin.
- **Catalysts.** Its cables becoming a standard at 800G and 1.6T, new hyperscaler customers.
- **Worst / Base / Best.** Bigger rivals or optical links displace its niche and concentrated
  customers pause. / Adoption grows with cluster size. / Its cables become the default for short links
  and it scales fast from a small base.

---

### Phase · AI cloud   `theme: AI infrastructure`
**[ACCENT: cyan]**

**The role.** Buy AI chips, house them in data centers, and rent the compute by the hour. A
specialized kind, the neocloud, rents only AI chips. They are more than pure middlemen: they stand up
GPU capacity in months rather than the years a hyperscaler takes, run the software that schedules and
manages thousands of chips, build the high-speed networking between them, and in some cases secure
their own power. But because they all rent the same Nvidia chips, none has a strong product advantage,
so they compete on speed of buildout, access to scarce GPUs, price, contracts, and power.

**Why this phase is risky.** It is capital-intensive and debt-heavy. The operator borrows billions to
buy chips, then must rent them out faster than they lose value. The economics work while AI compute is
scarce and break quickly if it is not. This is the highest-risk link in the chain.

**Indicators to watch.** Contracted backlog (revenue locked in), utilization, customer concentration,
debt, and how fast the chips depreciate.

**The competitive landscape.** The general clouds (Amazon's AWS, Microsoft Azure, Google Cloud)
dominate overall cloud and also rent GPUs. Among the AI-only neoclouds, CoreWeave is the largest, with
Nebius the fast-rising number two, then Lambda and Crusoe. Neoclouds are expected to reach about 20%
of the AI-cloud market by 2030. **[VISUAL: neocloud share, and neocloud vs hyperscaler split.]**

#### CoreWeave (CRWV)
- **Role.** An AI cloud built only to rent Nvidia GPUs at scale, usually on multi-year contracts with
  AI labs and tech firms, with its own management software and networking around the chips.
- **Revenue source.** Charges for GPU compute, mostly contracted years ahead. Driven by AI-compute
  demand and how fast it installs chips.
- **Competitive landscape.** The neocloud leader: revenue rose from about 1.9 billion dollars in 2024
  to 5.1 billion in 2025, with a contracted backlog near 67 billion and customers including OpenAI and
  Microsoft. Its closest challenger is Nebius (an Amsterdam full-stack AI platform whose market value
  nearly matches CoreWeave's), followed by Lambda (developer-focused) and Crusoe (built on stranded and
  renewable energy). It also competes with the hyperscalers, who rent GPUs too but cost far more.
- **Moat.** Thin and contested, because everyone rents the same Nvidia chips. What it has instead is
  scale, the fastest buildout, privileged access to scarce GPUs through a close Nvidia relationship,
  and a huge contracted backlog that locks in revenue. It is the highest-risk name in the chain
  precisely because the moat is weakest and the debt is largest.
- **Indicators to watch.** Backlog and its quality, utilization, customer concentration, debt, chip
  depreciation, the Nvidia relationship.
- **Catalysts.** New large contracts, continued compute scarcity.
- **Worst / Base / Best.** A big customer slows, chips depreciate faster than expected, and debt
  bites. / Contracted demand keeps utilization high and it scales. / Compute stays scarce and its
  buildout speed makes it a key neutral provider.

---

### Phase · Software   `theme: software`
**[ACCENT: pink]**

**The role.** Sell software that businesses run every day, and add AI features to it. These companies
touch no silicon. They are buyers of compute and a read on AI demand.

**Why this phase is steadier.** Software is not a commodity and needs little capital. The advantage is
lock-in: once a company runs its workflows or its security on your platform, switching is painful. The
main risk is different too: a giant like Microsoft bundling a good-enough version for free.

**Indicators to watch.** Subscription growth, net retention (whether existing customers spend more each
year), AI-feature adoption, and pressure from Microsoft.

**The competitive landscape.** Software is large and fragmented, but each of your names leads its own
corner, described per company below.

#### ServiceNow (NOW)
- **Role.** The platform big companies use to run internal processes (IT requests, HR onboarding,
  customer-service cases). When a work request flows through software, it is often ServiceNow. It is
  adding AI agents to do that work automatically.
- **Revenue source.** Recurring subscriptions that grow as customers add departments and AI features.
- **Competitive landscape.** The clear leader in IT-service management at roughly 44%. Its rivals are
  BMC and other legacy IT-workflow vendors, Atlassian (whose Jira covers team workflows), and
  increasingly Salesforce and Microsoft as ServiceNow expands beyond IT into HR and customer service.
- **Moat.** It becomes the system of record for a company's workflows. Once a large organization runs
  its core processes on ServiceNow, switching means re-engineering how the company operates, so
  retention is very high and it can expand into new departments from the inside.
- **Indicators to watch.** Subscription growth, net retention, AI-agent adoption and pricing, IT-budget
  health.
- **Catalysts.** Enterprise AI-workflow adoption, new product lines.
- **Worst / Base / Best.** IT budgets tighten and AI repricing pressures seat-based revenue. /
  Digitization and AI agents expand its footprint for durable growth. / It becomes the platform for
  enterprise AI work and takes more of the IT stack.

#### CrowdStrike (CRWD)
- **Role.** Protects company computers. A small program (an agent) runs on every laptop and server and
  uses cloud-scale data and AI to detect and stop attacks. It is expanding from that into a broad
  security platform.
- **Revenue source.** Per-device subscriptions that grow as customers add modules. Driven by security
  spending and the push to consolidate many separate security tools onto one platform.
- **Competitive landscape.** The number two in endpoint security at roughly 14%, behind Microsoft at
  roughly 40%, which leads because it bundles its Defender product into Windows and Office
  subscriptions. Other rivals are SentinelOne, Palo Alto Networks, and Trend Micro.
- **Moat.** A single lightweight agent that is easy to deploy, data network effects (more customers
  means more attack data, which improves detection for all), and exceptional loyalty: it keeps over
  97% of customers each year and steadily sells them more modules. The main threat to that moat is
  Microsoft giving away a good-enough alternative.
- **Indicators to watch.** Module adoption, net retention, Microsoft competition, the lingering effect
  of its 2024 outage.
- **Catalysts.** Consolidation wins, new security modules.
- **Worst / Base / Best.** Microsoft bundling and the outage overhang slow new business. /
  Consolidation drives module adoption and retention compounds. / It becomes the default security
  platform at scale.

---

## Reading your tech book in one minute
- The names a customer cannot easily replace (ASML, TSMC, and Nvidia through CUDA) are the safest
  profit pools, because they set prices rather than take them.
- The commodities (memory: MU, SNDK; optics: COHR, LITE) are higher-risk bets on a price cycle: strong
  in a shortage, painful in a glut, with little product moat.
- The challengers (AVGO and MRVL in custom silicon, CRDO in cabling) are bets that "design your own
  chip" keeps taking share from "buy Nvidia".
- The software names (NOW, CRWD) are the steadier, lock-in businesses, least exposed to the hardware
  cycle, each a leader in its own corner.
- One number moves most of them together: how much the few giant buyers spend on AI each year.

---

## Sources
- Foundry share: [Dataconomy, Q3 2025](https://dataconomy.com/2025/12/23/tsmc-dominates-foundry-market-with-72-share-in-q3-2025/)
- Equipment (WFE) structure: [TechInsights](https://www.techinsights.com/blog/wfe-market-share)
- DRAM and HBM share: [Counterpoint](https://counterpointresearch.com/en/insights/global-dram-and-hbm-market-share); [Astute Group, HBM](https://www.astutegroup.com/news/general/sk-hynix-holds-62-of-hbm-micron-overtakes-samsung-2026-battle-pivots-to-hbm4/)
- NAND share: [TechPowerUp / TrendForce, 2025](https://www.techpowerup.com/340410/nand-flash-revenue-surged-over-20-in-2q25-sk-group-market-share-jumped-to-21)
- Nvidia AI accelerator share: [Silicon Analysts](https://siliconanalysts.com/analysis/nvidia-ai-accelerator-market-share-2024-2026)
- Custom ASIC (Broadcom, Marvell): [Tom's Hardware, 2026](https://www.tomshardware.com/tech-industry/semiconductors/custom-ai-asics-examined-from-broadcom-to-mtia)
- Optical transceivers: [MarketsandMarkets](https://www.marketsandmarkets.com/Market-Reports/optical-transceiver-market-161339599.html)
- Active electrical cables, Credo: [CNBC, Oct 2025](https://www.cnbc.com/2025/10/17/500-purple-cables-put-credo-in-middle-of-the-ai-boom.html)
- Neoclouds (CoreWeave, Nebius): [DataCenterKnowledge](https://www.datacenterknowledge.com/cloud/earnings-roundup-neoclouds-shift-from-gpu-race-to-power-wars); [Yahoo Finance, Nebius vs CoreWeave](https://finance.yahoo.com/markets/stocks/articles/neocloud-competition-heats-nebius-market-040100091.html)
- Endpoint security share: [Microsoft Security Blog, 2025](https://www.microsoft.com/en-us/security/blog/2025/08/27/microsoft-ranked-number-one-in-modern-endpoint-security-market-share-third-year-in-a-row/)
- ServiceNow ITSM share: [ServiceNow, Gartner, 2025](https://www.servicenow.com/blogs/2025/no-1-6-tech-workflow-segments)
