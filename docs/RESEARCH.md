# Research notes (2026-10-15)

Background for the pivot to **financing battery recycling (TRL 7-9) and upcycling research (TRL 4-6) on
Avalanche C-Chain**. The business conclusions are in [BUSINESS_MODEL.md](BUSINESS_MODEL.md).

## 0. How this was produced, and how far to trust it

- **Method.** One research agent per topic, using web search. Each topic was then queued for an independent
  fact-checker whose job was to refute its key claims.
- **No pages were opened directly.** The build sandbox could not open web pages: WebFetch failed on every domain,
  and direct HTTPS is blocked except to package registries. Findings rest on search-engine summaries of the cited
  pages, so treat exact figures as leads to confirm on the primary page.
- **Two topics are unverified recall.** The shared search budget (200 searches per turn) ran out partway through,
  so **Thai law (§7) and DeSci barriers (§8) come mostly from the agents' own recall**. Every one of those findings
  is marked unverified. A follow-up message starts a new search budget, so both can be re-run.
- **Network access.** To let future runs open primary sources, widen Network access in the cloud environment
  settings, or add hosts such as sec.or.th, bot.or.th, krisdika.go.th, eur-lex.europa.eu, docs.avax.network,
  developers.circle.com and api.openalex.org. See
  <https://code.claude.com/docs/en/cloud-environments#network-access>.
- **Local evidence I checked myself.** Anything stated about the MatDAO code was confirmed in the files with
  path:line references. Anything stated about API request shapes was confirmed from the source code of maintained
  client libraries (pyalex 0.21, semanticscholar 0.12, python-epo-ops-client 4.2.2, patent_client 3.2.8), downloaded
  from PyPI.

---

## 1. MatDAO audit (two repos)

Five subsystem audits plus an architect's synthesis. Twelve of the load-bearing claims were re-checked in the files,
and all twelve held.

**Decision: build on sci-protocol and port selected MatDAO platform modules into it.** Port module by module.
MatDAO's backend contributes concepts only, no code.

**Critical findings.** Do not show any of the following to investors.

1. **The patent corpus is fabricated but labelled as Google Patents Public Data.**
   - `scripts/generate_patent_batch2.py` hand-writes records and tags them
     `_source: google_patents_public_data_batch2`. Example: `US-11123456-B2`, "Solid oxide fuel cell", attributed
     to Bloom Energy.
   - Patent numbers follow keyboard patterns, and 31 of the 90 "B2" numbers are at or above 13,000,000, beyond any
     issued US patent. I verified this independently.
   - Every "prior art match" or "FTO hit" MatDAO ever showed cites these records.
2. **The "embeddings" are an MD5-hash fallback with no semantics,** mislabelled as OpenAI text-embedding-3-small.
   Similarity scores come out around 274 instead of between -1 and 1.
3. **The TRL scoring is inverted.** A lab coin-cell text scores TRL 8-9 because it contains the word
   "manufacturing", and a 10 kt/yr plant scores 2-3.
   - `trl-services` adds `Math.random()` to scores and fabricates certifications.
4. **Investor-facing fakes.**
   - The investor dashboard shows a fabricated +74% profit-and-loss.
   - Real project pages show fake "investment sent successfully" alerts.
   - Analysis output uses "Strong Buy" and "IPO upside" language.
5. **Contract bugs.**
   - `SwapRouter` accepts any token as "USDC".
   - Escrow refunds depend on claim order and strand 24% of the pot.
   - Funds lock forever when a raise misses its goal.
   - The `RWA3643` contract is a boolean allowlist, not ERC-3643.
6. **The multi-agent AI never starts.**
   - The coordinator is built with the wrong constructor keyword, so every report comes from templates.
   - Model IDs are retired.
   - LLM output is not grounded in retrieved documents.
7. **Data-security holes.**
   - An unauthenticated proxy exposes researchers' unpublished milestone proofs.
   - An anon-callable SECURITY DEFINER RPC allows insecure direct object reference (IDOR).
   - A DeepSeek key can be sent to api.openai.com.

**Worth reusing as concepts:**
- the `PriorArtSearch` / `OriginalityAssessment` type contract and UI, with per-source status, evidence quotes and
  manual-search links;
- the FTO overlap table fields;
- the TTO (tech-transfer office) review workflow;
- the R2C TRL pyramid;
- the rule "show no number rather than a fake number" from `valuation.py`;
- the numeric-provenance check idea.

**How this repo uses it.** `apps/api/app/evidence/` is the replacement engine. It is built on real sources, takes
fixtures only with `XX-TEST` ids (refused outside test mode), runs its model in a closed world, verifies every quote
against the source text, and states its coverage.

## 2. Bio Protocol (BIO)

- **History.**
  - Molecule started bio.xyz as a biotech-DAO accelerator in 2022.
  - In 2024, community auctions raised a reported $33M+ (figure not audited), and Binance Labs (now YZi Labs) made
    an undisclosed investment.
  - BIO listed on Binance Launchpool on 3 January 2025.
  - V1 launchpad (Base and Solana) followed in March 2025, and V2 in August 2025 (Ignition sales, BioXP, veBIO,
    BioAgents).
  - 2026 brought the BIOS "AI scientist", Science Beach (agent payments via x402) and OpenLabs. Ignition sales have
    been denominated in USDC since April 2026.
- **Market.**
  - BIO peaked at about $0.889 on 3 January 2025 and traded at about $0.028 on 14 October 2026, roughly 97% lower.
  - VITA, CRYO, NEURON and AUBRAI fell 95-98%, peaking at the BIO listing.
  - In April 2026 the token rallied about 120% on an "AI-designed peptide". By PeptAI's own account (August 2026)
    the peptide existed only as computer predictions.
- **Outcomes.**
  - Self-reported: "$50M+ treasuries raised" against "$15M+ funded research".
  - VitaDAO: about $4.7M deployed across 31 projects.
  - No audited accounts and no royalties paid to token holders were found.
- **What transfers to battery research:**
  - the legal wrapper (sponsored-research agreement plus assignment);
  - KYC-gated economic rights;
  - refund-if-target-missed raises;
  - open-source agents with published benchmarks.
- **What to avoid:**
  - a platform token at the centre;
  - points and engagement farming;
  - microcap per-project tokens fully unlocked at launch;
  - mixing "treasury raised" with "research funded" in metrics;
  - announcing results before lab validation.

## 3. Conception X and the IP-NFT stack

- **What "conceptionx" is.** It is **Conception X**, a UK not-for-profit venture programme for PhD students: UCL
  Engineering, 2018, founder Dr Riam Kanso, Barclays backing. It runs 9 months, is free, takes no equity, and the
  students keep their IP. No crypto project by that name was found.
  - Outcomes are self-reported: "200+ companies, £200M+".
- **The lesson to borrow.** Copy its *funnel*: high volume, low friction, a partnership with tech-transfer offices,
  and returns earned through an affiliated angel syndicate. Its no-equity, student-owned-IP premise may not carry
  over to Thai universities.
- **Molecule IP-NFTs.**
  - Structure: a sponsored research agreement plus an assignment of the funder's position to whoever holds the NFT.
    No court has tested this.
  - IP Tokens give governance votes, but no ownership or automatic economic rights.
  - Molecule presented a "Coin-to-Company" model to the SEC Crypto Task Force on 2 March 2026, which in effect moves
    the IP back into a conventional corporation.
- **Evidence on tokenised IP.** No IP-NFT or IP token was found to have paid licensing revenue to holders.
  Liquidity is negligible: VITA-FAST traded about $30 to $1,200 a day against about $62k of pool liquidity. The same
  speculation-without-revenue pattern shows up at Pump.science, ResearchHub and Story Protocol (under $100 a day of
  on-chain revenue against a valuation of about $500M).
- **Materials and batteries.** No DeSci effort in materials or batteries was found.

## 4. On-chain receivables and private credit

- **What scaled:**
  - Figure, a regulated originator using a blockchain as its ledger, holds about 75% of tokenised private credit
    (its SEC prospectus, citing RWA.xyz).
  - Maple scaled only after moving to overcollateralised lending (AUM about $4-4.8B in 2026).
  - Centrifuge now grows through institutional funds; Janus Henderson's JAAA and JTRSY run on Avalanche via Grove.
- **What failed:**
  - Goldfinch: more than $18M of losses on about $100M originated; token holders voted a wind-down in June 2026.
  - Centrifuge: Harbor Trade defaulted on $2.1M; ConsolFreight had about $1.8M stuck with Hanwha.
  - Maple: $36M lost to Orthogonal.
  - TrueFi: losses on Blockwater, Invictus and Alameda.
  - Credix: effectively defunct.
- **Fraud pattern.** Greensill, Hin Leong, First Brands and Tricolor all turned on the same few failures: fictitious
  or "future" receivables, double-pledging, and lenders not controlling collections.
- **Blockchain trade-finance consortia shut down for lack of adoption:** we.trade, Marco Polo, Contour and TradeLens.
- **Thai tools:**
  - CCC s.306/308 (written notice or consent for an assignment).
  - The Business Security Act registry at the DBD.
  - The Bank of Thailand's PromptBiz, with e-invoices and double-financing checks for banks. Whether a non-bank can
    access the check is unknown.
  - e-Tax invoices prove an invoice was issued, not that the debt is valid.
- Analysis of the draft example: [BUSINESS_MODEL.md §3.1](BUSINESS_MODEL.md).

## 5. Avalanche C-Chain

- **Deploy on the C-Chain (Fuji 43113 now, mainnet 43114 later), not an L1.**
  - The L1 protocol fee is small: about 1.33 AVAX per validator per month since Etna.
  - The operating cost is not: AvaCloud mainnet plans run $1,999-$4,999+ a month, and you also need a relayer, a
    bridge and an explorer, and you lose C-Chain liquidity.
  - Intain, Balcony and StraitsX chose L1s for regulatory permissioning, not cost.
- **Helicon (mainnet 22 September 2026) changed block tags.**
  - `latest` now means the last executed block; `safe` and `finalized` mean the last settled block.
  - The minimum gas price is now governed by validators.
  - *Implemented:* the API indexer follows `finalized` on 43113/43114 (`apps/api/app/chain/indexer.py`).
- **Stablecoins.**
  - Mainnet: native USDC `0xB97E…a6E`. Avoid the bridged USDC.e.
  - Fuji: test USDC `0x5425…Bc65` from faucet.circle.com.
  - USDT and EURC addresses came from secondary sources only; verify them.
- **Contract verification.** Use Routescan, which has run snowtrace.io since November 2023. Etherscan's free tier
  reportedly dropped Avalanche around November 2025. *Implemented:* `[etherscan]` entries in
  `contracts/foundry.toml`.
- **RWA headline vs reality.** Rwa.xyz shows about $11.4B "represented", but about 94% of that is one token in one
  wallet. About $1.7B is distributed, roughly half of it from Securitize. The institutional funds (BUIDL, BENJI,
  VBILL, ACRED) are permissioned and cannot be used as your liquidity.
- **Closest comparable.** In about August 2026, POSCO International tokenised trade receivables on Intain's
  Avalanche L1, and Olea bought them.
- **Grants.**
  - Team1 Mini Grants: up to $10k, open applications.
  - Team1 Accelerator Grants: up to $30k, by committee nomination.
  - Team1 Thailand launched in 2026 and runs university workshops.
  - Retro9000's C-Chain round rewards AVAX burned, which does not fit a low-volume RWA platform.
  - No Avalanche program funds battery research.

## 6. Battery recycling and upcycling

- **Technology readiness.**
  - Pyro- and hydrometallurgy: TRL 9.
  - Direct recycling of clean production scrap: about TRL 6-8. Princeton NuEnergy has commercial-scale claims and a
    $50M DOE award (August 2026).
  - Direct regeneration of mixed end-of-life black mass: about TRL 4-6.
  - NCM111→Ni-rich upcycling: gram-scale lab work, about TRL 3-4.
  - These TRLs are the researcher's estimates. The literature says "early to intermediate".
- **Chemistry.** LFP is about 81% of China's 2025 EV installations and over 55% globally. BYD (LFP) leads in
  Thailand.
- **Prices are volatile.**
  - Lithium carbonate: about 58k CNY/t (mid-2025), about 201k (May 2026), about 115k (12 October 2026).
  - Mysteel NCM black mass: about 102k → 92k CNY/t (June-July 2026). LFP black mass: about 22.8k CNY/t
    (10 October 2026).
  - Benchmark CIF Asia NCM payables fell from 120% to 107.5% in Q3 2026.
- **Industry distress and overcapacity.**
  - Li-Cycle: sold to Glencore by credit bid (August 2025).
  - Northvolt: bankrupt; its Revolt recycling plant is being sold to Lyten.
  - Ascend Elements: Chapter 11 (April 2026).
  - Redwood: cut about 10% of staff and pivoted to storage.
  - Umicore: its 150 kt plant is delayed to 2032 or later.
  - China: about 4.2 Mt/yr of whitelisted capacity against about 0.65 Mt processed.
- **Policy.**
  - EU: black mass is classified as hazardous waste, mandatory by 9 November 2026, which bars exports to non-OECD
    countries. Battery passport from 18 February 2027. Recycled-content minimums from 2031, with the methodology
    still in draft.
  - US: black-mass export restriction from 27 August 2026.
  - China: reopened compliant black-mass imports in August 2025, with a 3% tariff in 2026.
- **Thailand.**
  - EV demand is strong: about 147.5k BEV registrations in 2025, and BEVs were 35% of new registrations in August
    2026.
  - No confirmed industrial Li-ion recycler was found.
  - E-waste imports, including batteries, are banned.
  - The WEEE/EPR (producer-responsibility) law is still a draft.
- **Patents.**
  - China leads battery-circularity patenting (EPO-IEA study, April 2026: 42% a year growth in 2017-2023).
  - UCSD (Zheng Chen) holds granted relithiation patents (US 12368194, 12183901, 12176512, 11996557).
  - The WPI/Ascend portfolio is in a 363 sale.
  - OnTo Technology holds direct-recycling patent families ("Cathode-Healing").

## 7. Thai legal constraints [mostly unverified: search budget exhausted]

Checklist and provisional readings: [BUSINESS_MODEL.md §3.5](BUSINESS_MODEL.md). The ones that change the design:
- Return-bearing pool shares are very likely investment tokens, probably debt-like, and need an ICO portal plus SEC
  approval.
- Pooling public money for a promised yield may touch collective-investment, deposit-taking and public-borrowing-fraud
  law, with or without tokens.
- A 15% interest cap applies if a deal is recharacterised as a loan.
- Thai parties should be paid in THB, not stablecoins.
- Thai Bayh-Dole requires the funder's consent to transfer publicly funded results, and march-in rights apply.
- KYC data stays off-chain under the PDPA.
- Going offshore does not legalise an offer to Thai retail investors.

## 8. Barriers to DeSci adoption and growth [unverified recall: re-run when search is available]

The founder asked to recall this topic from an earlier chat that is not accessible here, so it was rebuilt from
scratch. Ranked by severity for this platform:

1. **Securities and regulation.** Revenue-share or yield tokens are investment contracts under US law (Howey; the
   2017 DAO Report) and investment tokens in Thailand. MiCA excludes financial instruments, so MiFID II and
   prospectus rules apply in the EU.
2. **Capital scale versus speculation.** DeSci funding totals tens of millions, against roughly $47-48B a year at
   NIH alone. The late-2024 boom (BIO and Binance, Pump.science) decoupled token prices from research results.
3. **IP enforceability.**
   - An NFT is not legal title (35 U.S.C. §261 requires assignments in writing).
   - Thai university tech-transfer offices are the unavoidable counterparty.
   - Open-science disclosure can destroy patent novelty: the EPO applies absolute novelty, and a blockchain
     timestamp does not create priority.
4. **Institutions.**
   - Promotion still rewards indexed journals, though DORA and CoARA are trying to change that.
   - Universities need fiat contracts, overhead recovery and compliance checks.
   - Crypto stigma persists: Terra, FTX, and in Thailand the Zipmex freeze.
5. **Incentive misalignment.**
   - Token liquidity moves in seconds; research takes years.
   - Null results lower token value.
   - Token-paid peer review has no evidence of improving quality.
6. **Data integrity.** A chain proves provenance, not truth. The carbon-credit precedent (Toucan/KlimaDAO, then
   Verra's 2022 restriction) shows how quality problems can be amplified on-chain.
7. **Governance.** Studies of DAO voting find concentrated power and low participation, and expert committees
   remain the de facto gatekeepers.
8. **Materials versus biotech DeSci.**
   - Discovery to market takes 10-20 years (Materials Genome Initiative).
   - Pilots are capex-heavy: cleantech VC lost over half its $25B+ in 2006-2011 (Gaddy et al. 2017).
   - The buyers are industrial and require qualification.
   - There is no patient-advocacy capital base comparable to longevity's.
   - The strongest pull for on-chain data is EU Battery Regulation provenance, *if* accredited auditors anchor the
     attestations.

## 9. Data sources for evaluating research against real patents and literature

These are what `apps/api/app/evidence/sources/` implements. API shapes were confirmed from client-library source
code, as noted in §0.

| Source | Status for this project | Notes |
|---|---|---|
| OpenAlex | **API key required since 13 February 2026**, with metered usage (search calls billed). Some sources report a free daily allowance. | pyalex 0.21 sends `Authorization: Bearer <key>`. Abstracts arrive as an inverted index, which the engine rebuilds. |
| Crossref | Free. Add `mailto` to join the polite pool. | Abstracts are JATS XML. Used for DOI existence checks. |
| Semantic Scholar | Free; a key is recommended (`x-api-key`). | `publicationDateOrYear` is confirmed in semanticscholar 0.12. |
| arXiv | Free. | Atom XML; `submittedDate` range filter. |
| EPO OPS | Free registration; weekly fair-use quota; OAuth client credentials. | Worldwide bibliographic data, EP/WO claims, INPADOC legal status. **Parser tested on real OPS XML** (patent_client fixtures, Apache-2.0). Dates use `pd within "a b"`. |
| PatentsView PatentSearch | `search.patentsview.org/api/v1`, `X-Api-Key`. **Key issuance reported paused in 2026**; long-term viability uncertain. | US only. Field names unverified against live Swagger. |
| Lens.org | Token; access is approval-gated (terms reported inconsistently). | Patents plus scholarly works and legal status. Response shape follows its docs and is unverified live. |
| Google Patents Public Data (BigQuery) | Billed per byte scanned. **Run `--dry_run` first** (`apps/api/scripts/patent_corpus.sql`). | The best bulk source: claims, CPC codes, priority dates, families, citations. Chinese and Korean recall depends on the machine-translated fields. |
| Thai DIP / WIPO PATENTSCOPE | Thin in BigQuery. | Thai petty patents need a partner feed or manual curation. Flag the gap in reports. |

CPC seed codes (verify against the current scheme): Y02W30/84, H01M10/54, H01M6/52, C22B7/00, C22B23/00, C22B26/12,
C22B47/00, C01D15, C01G51, C01G53, C01G45, H01M4/505, H01M4/525, H01M4/58.

## 10. Tools that make an AI coding agent (and this codebase) more capable

The planned research topic on tooling failed twice: the session limit was hit and the search budget ran out.
Instead, every repository below was **confirmed to exist with `git ls-remote`**, and its **licence was read from the
repo's own LICENSE file** on 2026-10-15. The maturity notes are my assessment, not measured benchmarks.

| Need | Repo | Licence | Recommendation |
|---|---|---|---|
| Fewer tokens spent reading code | [oraios/serena](https://github.com/oraios/serena) | MIT | **Use.** An MCP server with symbol-level tools backed by language servers, so the agent reads functions, not whole files. |
| Current library docs (avoid stale APIs) | [upstash/context7](https://github.com/upstash/context7) | MIT | **Use** for fast-moving libraries (wagmi, viem, Next.js, Foundry). |
| Whole-repo snapshot for one-shot review | [yamadashy/repomix](https://github.com/yamadashy/repomix) | MIT | Occasional use. It packs a repo into one file, which costs more tokens than Serena for routine work. |
| Driving funder portals interactively | [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) | Apache-2.0 | **Use** (also offered as a plugin). Pairs with `tools/portal-fill`, which never submits. |
| LLM-driven browser agents | [browser-use/browser-use](https://github.com/browser-use/browser-use) (MIT); [Skyvern-AI/skyvern](https://github.com/Skyvern-AI/skyvern) (**AGPL**) | | Keep the deterministic Playwright helper for form filling. Skyvern's AGPL licence is a problem for a hosted product. |
| Crawling funder sites | [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) | Apache-2.0 | Optional upgrade for JS-heavy sites. The repo's crawler uses trafilatura plus httpx (robots-aware, slow by design). |
| Paper and patent PDF parsing | [kermitt2/grobid](https://github.com/kermitt2/grobid) (Apache-2.0), [docling-project/docling](https://github.com/docling-project/docling) (MIT), [datalab-to/marker](https://github.com/datalab-to/marker) (Apache-2.0 code; check its model-weights terms) | | **GROBID** for paper metadata and references; **docling** for layout and tables in methods sections. Both are the next step for evidence-engine ingestion. |
| Literature API clients | [J535D165/pyalex](https://github.com/J535D165/pyalex) (MIT), [danielnsilva/semanticscholar](https://github.com/danielnsilva/semanticscholar) (MIT) | | Used here as the reference for request shapes; the engine calls the HTTP APIs directly. |
| Patent API clients | [parkerhancock/patent_client](https://github.com/parkerhancock/patent_client) (Apache-2.0), [ip-tools/python-epo-ops-client](https://github.com/ip-tools/python-epo-ops-client) (Apache-2.0) | | patent_client's recorded real EPO XML is used in this repo's tests (with attribution). |
| Embeddings for papers | [allenai/specter2](https://github.com/allenai/specter2) | (see repo) | Benchmark it against the local embedder on a battery evaluation set before switching. PaECTER for patents is on Hugging Face (`mpi-inno-comp/paecter`), not GitHub. |
| Permissioned RWA tokens | [TokenySolutions/T-REX](https://github.com/TokenySolutions/T-REX), [ERC-3643/ERC-3643](https://github.com/ERC-3643/ERC-3643) | **GPL-3.0** | The reference ERC-3643 implementation. GPL affects how derived contracts can be licensed; check with counsel. |
| Tokenised credit pools | [centrifuge/protocol](https://github.com/centrifuge/protocol) | **Business Source License** | Deploying their audited contracts on Avalanche is an option. Forking the code is restricted by the BSL. |
| Avalanche cross-chain messaging | [ava-labs/icm-contracts](https://github.com/ava-labs/icm-contracts) | (not detected at root) | Only needed if you ever move to an L1. |
| Claude Code subagent collections | [wshobson/agents](https://github.com/wshobson/agents) (MIT), [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents), [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | | Ideas only. This repo ships its own domain subagents in `.claude/agents/` (see README). |
