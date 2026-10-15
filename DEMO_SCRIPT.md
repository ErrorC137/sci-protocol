# Demo script: one researcher, one continuous story (brief §10)

Target length: 5-6 minutes. Do not demo features; follow one person end to end. Rehearse twice on the deployed URL.

**Setup (before you go on stage)**
- Browser profile A: researcher wallet. Profile B: funder wallet. Profile C: attestor wallet. All on Base Sepolia.
- Project B (failure path) seeded so its milestone deadline passes ~5 min before step 6 (docs/DEPLOY.md §6).
- Tab 1 `/profile` (researcher, localStorage cleared). Tab 2 `/raise/1` (funder). Tab 3 `/raise/1` (attestor). Tab 4 `/raise/2` (funder).

---

### 1. The problem (20 s)
> "At one Thai university IP institute, 20 to 30 IPs have ever been licensed out of hundreds to thousands filed. A senior
> researcher at Thailand's national science agency told us she has commercialisation-ready patents she doesn't advance,
> purely for lack of funding to bridge lab to industry. About 10 in 100 Thai grant applications succeed, and each one is
> weeks of manual paperwork."

Landing page, right-hand card.

### 2. A researcher arrives (60 s)
`/profile` → **Load demo researcher** → click through the five steps.
- Point at the green banner. **Say: "Notice we never asked what the technology is."**
- Step 1: fields and sub-domains are controlled vocabulary; free text is rejected by the API.
- Step 2: TRL 4 with plain-language definitions, and the evidence consistency check.
- Step 5: the keywords box. "These never leave this browser - they re-rank locally."

**Find matches →**

### 3. Matches appear (60 s)
- "25 eligible of 75 · 50 excluded by hard rules." **Rules decide eligibility; the model only explains.**
- Open the top card's **Show details**: every rule ✓, then the five ranking components.
- Read one *Why this matched* / *To strengthen* (Claude, top 10 only).
- **Point at a Thai funder (PMU-C / NRCT / ARDA)**: "Nobody else in this room has structured Thai deeptech funding data."
- Right column: **What would unlock more funding → Register a company: +12.**

### 4. One click → the application is pre-filled (60 s)
TED Fund card → **Start application** → **Generate pre-filled draft**.
- **88% pre-filled**: green from the profile, amber to verify (THB amount capped at the grant's maximum), red needs you.
- Scroll to a narrative field: "It drafts a scaffold and leaves honest `[YOU MUST ADD]` gaps. It never invents
  technical claims - that would be fraud exposure, not a feature."
- The declaration is red: "We never tick a consent for you." Export is **locked**: "We never submit for you."

### 5. "But this researcher is TRL 4 - too early for most of these." (60 s)
Matches page → **Raise on-chain** (or open the pre-seeded project A, `/raise/1`).
- "Milestones first - you say what the money is for - then an all-or-nothing raise."
- **Funder tab**: *Get test mUSDC* → *fill remaining* → **Contribute** → "Fully funded - money is in milestone escrow."

### 6. Evidence → approve → release, then the failure path (90 s) ← the credibility moment
- **Researcher tab** `/raise/1`: write an evidence note → **Submit evidence**.
- **Attestor tab**: **Approve** → **Release 3,000 mUSDC to researcher**. The escrow ledger shows "Released 3,000".
- **Funder tab** `/raise/2`: red banner, *Milestone 1 missed its deadline*. **Trigger refund** →
  **Claim my refund: 3,000 mUSDC** → "Your refund has been paid."
- **Say: "No progress, no money. A missed milestone returns money to funders. That's what separates this from every
  'we tokenize X' pitch."**

*(Optional, 20 s: `/vault`. Encrypt a confidential note in the browser, anchor only its hash. "A timestamped existence
proof - not prior art, not a patent filing.")*

### 7. Close on scope honesty (20 s)
> "Testnet only, mock stablecoin. The attestor is centralized today; decentralizing it is next. The fractions are a
> mechanism demo, not a securities offering. Next: verify and expand the Thai corpus with TUIPI and NSTDA, a live
> pilot with one funder, and a multi-attestor set."

---

## Q&A prep
- **"Isn't this a securities offering?"** Answer early and directly: yes, revenue-share fractions very likely are
  securities. That's why this is a testnet mechanism demo. A real deployment needs counsel and almost certainly an
  offshore vehicle with accredited-only access.
- **"Who's the attestor?"** Our backend key today, named in the UI footer and the contract. The roadmap is a
  multi-attestor set (funder + independent lab + domain reviewer).
- **"Can the LLM hallucinate eligibility?"** No. SQL/Python rules decide; the model only explains the top 10 after the
  fact, and is told so. Without a key it falls back to templates.
- **"Is the vault prior art?"** No. It proves a ciphertext existed at a time, held by a wallet. Nothing more.
- **"How fresh is the data?"** Live connectors (Grants.gov, EU) run on a daily schedule; the curated SEA corpus is
  reviewed by hand. Say honestly how many entries you've verified.
- **"What if the researcher misses a deadline because the attestor is slow?"** Submitted evidence blocks the refund
  until the attestor decides; review latency never counts against the researcher (it's in the contract).
