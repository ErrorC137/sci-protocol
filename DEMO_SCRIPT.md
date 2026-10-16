# UPLO pitch flow (5-6 minutes)

**Today's Capital. Tomorrow's Breakthroughs.** One story, end to end: commercial battery recycling is financed
today, part of the margin funds battery-upcycling research, and research money moves only when milestones are
verified. Rehearse twice on the deployed URL. Times in brackets are targets; the total is about 5 min 45 s.

Honesty rules for the whole pitch: the testnet raise, escrow, release and refund are **real on-chain mechanics** (mock
stablecoin, no real value). The Overview KPIs, the invoice book and the calculator figures are **demo data /
illustrative**, and the screens say so; say it out loud too. Never call demo numbers traction.

## Setup (before you go on stage)

- Browser profile **A**: researcher wallet. **B**: funder wallet. **C**: attestor wallet (the wallet that ran
  `/setup`, unless you named another attestor there). All on **Avalanche Fuji**; each needs a little test AVAX for gas.
- Wake the API 5 minutes early (Render free sleeps after 15 idle minutes; the first request takes ~50 s). Opening any
  app page keeps it awake. Check the sidebar footer says **API online**.
- Seed through the UI about 25 minutes before you present (no Foundry needed on Fuji). In profile A, first run
  `/profile` → **Load demo researcher** → Find matches (this stores the profile the raise form reads), then:
  - `/raise/new` → **project 1: "Direct Cathode Regeneration pilot"**. Milestones due in days (e.g. "Regenerated
    NMC cathode meets capacity spec on a 1 kg pilot batch" · 3,000 mUSDC; "Third-party cell test report" · 5,000),
    raise open for 14 days.
  - `/raise/new` → **project 2: "LFP Upcycling Process (failure-path demo)"**, raise closing in ~5 **minutes**,
    milestone 1 due in ~20 **minutes**. Funder (profile B): fund project 2 in full before the raise closes. By beat 6
    its milestone deadline has passed. Do **not** submit evidence for it.
  - Local anvil instead: `FAIL_DELAY=1200 npm run dev:chain` seeds both with the same names from `data/demo/` (docs/DEPLOY.md §6).
- Clear localStorage in profile A again after seeding, so the wizard starts empty on stage.
- Tabs: **1** `/` landing (profile A, scrolled to top) · **2** `/overview` · **3** `/commercial-finance` ·
  **4** `/profile` (A) · **5** `/raise/1` (B, funder) · **6** `/raise/1` (C, attestor) · **7** `/raise/2` (B) · **8** `/validation`.

---

### 1. The landing: problem → capital flow → two pools (45 s) · tab 1
Scroll slowly; let the ring do the work.
- **Hero**: "Today's capital. Tomorrow's breakthroughs."
- **The gap**: "Battery recyclers already earn revenue, but their buyers pay in about 90 days. Meanwhile battery
  *upcycling* research is stuck at TRL 4 to 6: too early for banks, too late for most grants. UPLO uses the first to
  fund the second."
- **Capital flow** (pinned section, five stations light the ring): "A verified $100,000 invoice. The recycler gets
  $95,000 today. At day 90 the financier gets $98,000, the platform earns $2,000, and 20% of the contribution, $240,
  goes to the Innovation Treasury. That funds milestone-gated research. Licensed technology flows back to the
  recyclers. The loop closes." *(The screen labels this an illustrative example, not market rates.)*
- **Two pools**: "Investor principal in commercial financing is **never** used for research. Two segregated pools."

### 2. Overview: the loop as a product (30 s) · tab 2
- Point at the **Capital flow** diagram: recycling (TRL 7-9) → UPLO → Innovation Funding → R&D (TRL 4-6), and the
  copper arc of licensed technology coming back.
- "Top row is **demo data**, badged. The second row is **live**: raises, escrowed mUSDC and approved milestones read
  from the chain right now, and 150 funding routes in our research pipeline."
- Active opportunities: on-chain raises first (project 1 and 2), then demo rows.

### 3. Commercial Finance: the money maths (40 s) · tab 3
- "Pool A finances verified invoices." The invoice book is simulated and anonymised; say so.
- **Calculator**: start at the $100k example, then drag **Platform fee** to 3% and **Treasury allocation** to 30%:
  "Every dollar is accounted for. The treasury is funded from platform margin only; if costs exceed the fee, nothing
  flows to research." Drag the fee to 6% to show the warning that no financier would fund it.
- "Real invoice financing needs licensed partners and legal agreements. That's on the page, and it's our next step."
- **Reset to $100k example** before moving on.

### 4. Research Pipeline: a researcher arrives (75 s) · tab 4
`/profile` → **Load demo researcher** (Direct Cathode Regeneration pilot, TRL 5) → click through the five steps.
- Point at the privacy banner. **Say: "Notice we never asked what the technology is."** Matching uses controlled
  categories and stage only; keywords never leave the browser.
- **Find matches →** "42 eligible of 150, 108 excluded by hard rules. **Rules decide eligibility; the model only
  explains.**" Point at a Thai funder (PMU-C or NRCT), then **What would unlock more funding → Register a company**.
- TED Fund card → **Start application** → **Generate pre-filled draft**: green from the profile, amber to verify,
  red needs a person. "It never invents technical claims, never ticks a consent, never submits for you."

### 5. Innovation Pool: fund the research (40 s) · tab 5 (funder)
`/raise/1`: "Milestones first, then an all-or-nothing raise into escrow. This is Pool B in action."
- **Get test mUSDC** → **fill remaining** → **Contribute** → "Fully funded. The money is in milestone escrow."

### 6. Validation: evidence → approve → release, then the failure path (75 s) ← the credibility moment
- **Researcher** (tab 4 → `/raise/1`): write an evidence note → **Submit evidence**.
- **Attestor** (tab 6): **Approve** → **Release 3,000 mUSDC to researcher**. The ledger shows "Released 3,000".
- **Funder** (tab 7, `/raise/2`): *Milestone 1 missed its deadline* → **Trigger refund** → **Claim my refund** →
  "Your refund has been paid."
- **Say: "No progress, no money. A missed milestone sends money back to the backers."**
- Tab 8 `/validation` (5 s): "Every evidence, approval, release and refund is a public verification record."

### 7. Close on scope honesty (20 s)
> "This is a testnet demo with a mock stablecoin. The attestor is centralized today. The commercial-finance pool and
> the KPIs are simulated, and real invoice financing needs licensed partners and legal agreements. On-chain tokens
> would represent rights only where enforceable agreements back them; nothing here is a securities offering. Next:
> one recycler pilot with a licensed financing partner, and a multi-attestor set for research milestones.
> Finance today's industry. Build tomorrow's technology."

*Optional beats if you have time:* `/evidence` (NMC811 relithiation claim chart with a verbatim quote behind every
"disclosed" cell, "we never call it novel") · the Thai Word form `thai-research-proposal-demo.docx` on `/apply/<id>` ·
`/vault` (encrypt a note in the browser, anchor only its hash: an existence proof, not prior art or a patent filing).

---

## Q&A prep
- **"Where does the money for research really come from?"** Pool B: a fixed share of platform margin (20% of the
  gross contribution in the illustrative example), corporate R&D partners, and backers who accept research risk
  directly. Never Pool A principal.
- **"Is the $100k example your real pricing?"** No. It's an illustrative example from our business model, not market
  rates. Membership prices are proposals under market test.
- **"Do you need a licence to finance invoices?"** Real receivables financing needs licensed financing partners and
  legal agreements (receivables assignment, buyer confirmation). That's why Commercial Finance is a simulation today
  and our first pilot is with a licensed partner.
- **"Isn't this a securities offering?"** Revenue-share tokens very likely are securities. That's why this is a
  testnet mechanism demo. A real deployment needs counsel and an appropriate legal wrapper.
- **"Who's the attestor?"** One wallet today, shown on the raise page and in the contract. The roadmap is a
  multi-attestor set (funder + independent lab + domain reviewer).
- **"Can the LLM hallucinate eligibility?"** No. Rules decide; the model only explains the top results after the
  fact. Without a key it falls back to templates.
- **"What if the attestor is slow and the researcher misses a deadline?"** Submitted evidence blocks the refund until
  the attestor decides; review latency never counts against the researcher (it's in the contract).
- **"Is the vault prior art?"** No. It proves a ciphertext existed at a time, held by a wallet. Nothing more.
- **"How fresh is the funding data?"** The curated corpus is reviewed by hand and the Discover page flags entries that
  haven't been verified against the funder's site. Say honestly how many you've verified.
