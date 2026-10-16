# Business model review: "Circular Innovation Finance"

Review of the draft model (from ChatGPT, in Thai) for funding battery-upcycling research (TRL 4-6) from a
battery-recycling finance business (TRL 7-9), plus a recommended redesign.

**Evidence status, read first.** Figures come from (a) `tools/models/receivables_model.py`, deterministic and
re-runnable; (b) research agents working from web-search result summaries on 2026-10-15 (no source page could be
opened directly from the sandbox); (c) for Thai law and DeSci barriers, mostly the agents' *unverified recall*,
because the shared search budget ran out. Items marked **[unverified]** must be checked by a Thai lawyer or tax
adviser before anyone relies on them. Nothing here is legal, tax or investment advice. Full research notes:
[docs/RESEARCH.md](RESEARCH.md).

---

## 1. Verdict

The draft gets the **accounting hygiene** right: it separates four kinds of money and keeps two segregated pools,
and it does not use investor principal for R&D. Its core thesis does not hold:

- **Platform fees from recycling finance cannot fund meaningful research.** At the draft's own numbers, the 20%
  treasury slice is about 1% of the outstanding book per year. Funding USD 250k a year of research would need about
  **USD 24M advanced continuously**. Under a fairer, tranched structure the platform keeps less, and the figure is
  about **USD 48M**, before any credit losses.
- **The receivables example puts all the risk on the funder.** The platform takes 40% of the spread and bears none of the risk.
- **The financing pool would have few borrowers in Thailand today.** No confirmed industrial Li-ion recycler is
  operating in Thailand, and the domestic feedstock (spent batteries) is thin until about 2030.
- **As drafted, the financing pool is almost certainly a regulated investment product in Thailand.**

**Recommendation: run two separate businesses.**
- A conservative receivables-finance business that has to stand on its own unit economics.
- A research program funded by corporates and grants, which is where the money for TRL 4-6 work actually is.

Use Avalanche as the tamper-evident registry, escrow and attestation layer for both. Issue **no platform token**.

---

## 2. What to keep from the draft

| Draft element | Keep? | Why |
|---|---|---|
| Separate the four kinds of money (investor capital, investor returns, platform revenue, innovation treasury) | **Yes** | Correct, and it is how auditors and regulators will read the books. |
| Pool A (commercial financing) and Pool B (innovation treasury) as separate assets | **Yes, and go further** | Use separate legal entities, not just separate pools. Yield investors and grant-making have conflicting interests (research note: rwa, conceptionx). |
| Never use investor principal for R&D | **Yes** | Correct. |
| Revenue streams 1 and 2 near-term, licensing (3) as long-term upside | **Yes, but reorder** | Membership plus sponsored validation is the realistic primary engine. Financing comes second, and licensing is years away. |
| "Funding research does not automatically give IP rights" (WIPO) | **Yes** | It is also stricter in Thailand for publicly funded research: funder consent and march-in rights apply [unverified detail]. |
| Success fee (case A) before royalties or equity (case B) | **Yes** | Simpler and needs less capital. |
| Example numbers labelled "illustrative, not market rates" | Yes, but **the structure behind the numbers is the problem** | See section 3.1. |

---

## 3. Where it breaks

### 3.1 The invoice example: the economics

Run `python tools/models/receivables_model.py` to reproduce every number below. The RWA research agent computed the
same draft figures independently.

| The draft as written ($100k invoice, $95k advance, funder repaid $98k, platform fee $2k, 90 days) | Value |
|---|---|
| Funder return | **12.8% simple / 13.4% compounded** a year |
| Seller's cost of money | **21.3% simple / 23.1% compounded** a year |
| Platform share of the spread | **40%** (8.5% a year on the advance), with **no credit risk** |
| Good invoices needed to recover one total default | **32** |
| Funder return at 2% PD (default probability) / 50% LGD (loss given default) per cycle | 8.8% |
| Funder return at 3% PD / 60% LGD | 5.5% |
| Funder return at 5% PD / 60% LGD | **0.6%** |
| Funder return if 15% Thai withholding tax applies to offshore funders | 10.9% |
| Funder return if the buyer pays on day 150 / day 180 (flat fee) | 7.7% / 6.4% |

**Missing from the draft:**
- A reserve or holdback. The 95% advance with no reserve sends every credit note, assay adjustment or dispute
  straight into funder principal.
- Time-based pricing. With a flat fee, late payment is the funder's loss.
- A first-loss position for the platform or the originator.
- Concentration limits.
- Cash dominion: collections paid into a lender-controlled account.
- Buyer confirmation.
- Cost lines: verification, insurance, FX, Specific Business Tax, withholding, VAT, legal/SPV costs, servicing.

**Precedents.**
- Platform take rates:
  - Goldfinch: about 10% of interest, held as a reserve.
  - Centrifuge: about 0.4% of loan value.
  - The draft: 40% of the spread.
- Losses: on-chain SME and emerging-market credit lost money repeatedly.
  - Goldfinch: more than $18M lost; wound down in June 2026.
  - Centrifuge: Harbor Trade ($2.1M default); ConsolFreight (about $1.8M exposure).
  - Maple: $36M lost to Orthogonal.
  - TrueFi: losses on Blockwater, Invictus and Alameda.

**The redesign (same model file):** buyer-confirmed invoices, a 90% advance with a 10% reserve released on
payment, a time-based rate of 16% a year, a $300 verification fee, a 20% first-loss tranche held by the platform or
originator, and a platform fee of 15% of interest.

| Tranched design | Seller all-in | Senior | Junior (first loss) | Platform net per invoice |
|---|---|---|---|---|
| No losses | 17.4% | 10.0% | 28.0% | $583 |
| PD 0.5% / LGD 50% | 17.4% | 10.0% | 22.9% | $583 |
| PD 2% / LGD 50% | 17.4% | 10.0% | 7.7% | $583 |
| PD 5% / LGD 60% | 17.4% | 10.0% | **−32.8%** | $583 |
| **Capped at <15% all-in** (12%/yr, senior 8%), PD 2% | 13.4% | 8.0% | **−1.3%** | $449 |

**What this shows:**
- The structure works only with **low-default, buyer-confirmed receivables**: strong refiners or OEMs and short tenors.
- If Thai law treats the deal as a loan, the seller's all-in cost must stay under the **15% civil interest cap**
  [unverified: CCC s.654 and the B.E. 2560 interest law]. The draft's 21.3% would break that cap.
- Under the cap, the junior tranche turns negative at a 2% default rate. That leaves no room for generic SME
  invoices. A Thai lawyer must decide between a **true sale, limited recourse** structure and a loan.

### 3.2 "Recycling cash flows fund upcycling research" does not survive the numbers

| | Draft | Tranched |
|---|---|---|
| Treasury per $100k invoice per 90 days | $240 | $117 |
| Treasury per year as a share of capital advanced | 1.0% | 0.5% |
| **Capital continuously advanced to fund $250k/yr of research** | **$24.4M** | **$47.6M** |

Two more problems sit on top of the arithmetic:
- **The money would be pro-cyclical.** When metal prices fall, recyclers default and payables drop at the same
  moment. In Q3 2026, CIF Asia NCM payables fell from 120% to 107.5%. Lithium carbonate went from about 58k to about
  201k to about 115k CNY/t in 18 months.
- **Recycling margins are thin.** GEM runs at about 10-15% gross margin. Several Western recyclers have failed or
  been restructured:
  - Li-Cycle: CCAA filing, sold to Glencore (2025).
  - Ascend Elements: Chapter 11 (April 2026).
  - Northvolt: bankrupt; its Revolt recycling plant is being sold separately.
  - Redwood: cut staff and pivoted to storage.

So research funding should be committed in advance from **corporate R&D money and grants**. A fixed, disclosed
share of financing profit can top it up, but it cannot be the engine. If lender-derived revenue goes to research,
lenders must be told, and the disclosure may change how the instrument is classified.

### 3.3 Who would actually borrow, in Thailand, now?

- **No industrial Li-ion recycler is confirmed.** None was found operating in Thailand, only MoUs and pilots
  (AMITA/EA with DPIM, EGAT with NSTDA). Check the Department of Industrial Works registry to confirm.
- **Supply of spent batteries is thin.** Thailand banned e-waste imports, including batteries (463 items, June
  2025). The BEV fleet is young. A meaningful end-of-life stream starts around 2030-2032.
- **The chemistry mix has moved.** LFP is about 81% of China's 2025 EV installations, and BYD (LFP) leads in
  Thailand. Recovering lithium from LFP or regenerating LFP is more relevant locally than upcycling NCM111 to
  NCM622/811, which targets a shrinking legacy stream.
- **Where the borrowers are now:**
  - Production scrap from cell and pack plants (Sunwoda and EA when they ramp).
  - Lead-acid recyclers, which are established in Thailand.
  - E-waste and metals recyclers.
  - Regional Li-ion recyclers: EcoNiLi (Malaysia), TES (Singapore). Cross-border lending adds legal complexity.

### 3.4 What a recycling receivable really is

Black-mass and recovered-metal sales are usually **provisionally priced and assay-contingent**. A sample
metal-bearing contract pays about 80% provisionally and settles finally after assays and umpire procedures.

- **Buyers.** The buyers are mostly **Chinese or Korean refiners**. China reopened compliant black-mass imports in
  August 2025 and cut the tariff to 3% in 2026.
- **Risks.** That brings dilution (moisture, impurities, assay disputes), FX, and cross-border enforcement risk.
- **Competition.** Traders already finance this space with prepayments and offtakes and bring their own
  metallurgical expertise: Glencore (Li-Cycle, Nth Cycle) and Trafigura (Ascend, Nth Cycle).
- **Implications.** Finance only the **confirmed provisional portion**, haircut it by the observed swings in
  quarterly payables (10-40%), require independent sampling and umpire clauses, and cap single-refiner exposure.

### 3.5 Legal and regulatory blockers (Thai lawyer checklist) [mostly unverified]

| Issue | Provisional reading | Effect on the draft |
|---|---|---|
| Pool shares or tokens paying a return | Very likely an **investment token**, probably **debt-like** (SEC rules from 16 Nov 2023). Public offering needs SEC approval and an **approved ICO portal**. | No retail Thai investors without the ICO-portal route. Calling it a "utility" or "governance" token does not change this. |
| Pooling money from many people for a promised yield | May touch collective-investment (SEA B.E. 2535), deposit-taking (FIBA B.E. 2551) and public-borrowing-fraud (B.E. 2527) laws, **with or without tokens**. | Highest-severity risk. Design it out; disclosure does not fix it. |
| Interest cap | 15% a year for non-financial-institution loans; over-charging can be criminal (B.E. 2560). | Matters if the deal is recharacterised as a loan (section 3.1). |
| Paying Thai parties in stablecoins | SEC barred licensed operators from facilitating crypto payments (2022). USDT and USDC are treated as cryptocurrencies. | Pay Thai recyclers and universities in **THB on bank rails**. Use the chain as the registry. |
| Factoring licence / Foreign Business Act | No factoring statute was found. A draft "Regulated Financial Service Providers" bill is reported. A company 50%+ foreign-owned likely needs a Foreign Business Licence. | Gating question for the operating company. |
| Assignment of receivables | Written assignment, plus written notice to or consent from the buyer (CCC s.306); unconditional consent cuts off the buyer's defences (s.308); anti-assignment clauses (s.303). | Build buyer acknowledgement into the flow. **Silent assignment does not work.** |
| Taxes | About 3% Specific Business Tax on factoring income; 15% withholding on interest paid to offshore non-banks; VAT on fees. | Already in the model's sensitivities. |
| Research IP (Thai Bayh-Dole, B.E. 2564) | Transferring publicly funded results needs the funder's written consent; march-in rights exist. | IP-NFT-style automatic transfer conflicts with this. Use licences or options from the owner. |
| PDPA | Applies extraterritorially. Biometric KYC is sensitive data. A public chain cannot erase anything. | KYC stays off-chain. Only allowlist attestations go on-chain. |
| Going offshore | Distribution law follows where the investor is. The SEC blocked unlicensed foreign exchanges (2025). Singapore's DTSP regime (June 2025) targets serve-foreigners-only setups. | Offshore does not fix a Thai-retail offer. |

### 3.6 Membership pricing

Benchmarks:
- NSF IUCRC centres: about USD 45-63k a year for full membership, 25-30k for associate.
- An Australian battery-recycling training centre: AUD 200k cash plus 100k in-kind a year per partner.
- DOE ReCell CRADAs: 50% cost share.

The draft's $5k / $12k / $30k tiers are fine as **entry tests**, but corporates buy three things:
- **IP access:** options and first negotiation rights, in writing.
- **Speed and lab capacity:** named partner labs with ICP-OES and cell build-and-cycling capability.
- **Tax treatment:** the Thai R&D super-deduction [unverified: 200%/300% history, certified through NSTDA]. The
  sponsored work must be structured so the corporate keeps the deduction. That usually means a **direct sponsored-research contract with an
  eligible institution**, with the platform as facilitator, not money pooled through an intermediary.

**Price to the benchmarks:**
- Associate (intelligence): USD 10-25k.
- Full (project votes plus a licence option): USD 40-60k.
- Validation sprints: budgets passed through to the labs, plus a 10-15% management fee, shown separately.

### 3.7 Licensing success fees

A success fee is plausible but slow and rare. No IP-NFT or IP token was found to have paid licensing revenue to
token holders. Battery-process IP is easier to design around than pharma composition-of-matter IP, and the space is
crowded:
- UCSD relithiation patents.
- The WPI/Ascend portfolio, now in a 363 sale.
- OnTo Technology.
- Brunp/CATL, which leads the patent landscape.

Budget zero licensing revenue for years 1-3.

---

## 4. Recommended model

```
          ┌──────────────────────────── Entity 1: Circular Trade Finance ───────────────────────────┐
 recycler │ buyer-confirmed invoices → verification (s.306/308 consent, DBD registry, e-Tax match,   │
 (seller) │ PromptBiz where reachable) → advance in THB → buyer pays controlled account → waterfall  │
          │ capital: phase 1 own equity / bank lines / institutional lenders (no public pool)        │
          │ on-chain: hashed invoice/assignment/collection events + attestations (no personal data)  │
          └───────────────┬──────────────────────────────────────────────────────────────────────────┘
                          │ fixed % of NET profit after credit losses, disclosed (top-up, not engine)
          ┌───────────────▼──────────── Entity 2: Upcycling Research Program ───────────────────────┐
 corporates │ memberships (IUCRC-style tiers) · sponsored validation sprints · grants (TSRI, PMU-B, │
 grants     │ NIA, international) · success fees later                                              │
 researchers│ funds via sponsored-research contracts (THB) with licence options; milestone escrow on │
            │ Avalanche where the sponsor pays in stablecoin; lab results attested (ICP-OES, cells) │
            └──────────────────────────────────────────────────────────────────────────────────────┘
 Shared product: the evidence engine (prior art + literature + TRL from evidence) = diligence for research
 and document reconciliation for receivables (the POSCO/Intain receivables pilot on an Avalanche L1 is the comparable)
```

**Phasing**
- **0-6 months, validate before you build.**
  - Get 3-5 corporate letters of intent at benchmark prices.
  - Find one pilot recycler with one strong buyer, and pull 12 months of its invoice and payment history.
  - Get Thai legal opinions on structure (true sale vs loan), the Foreign Business Act, investment-token
    classification and Bayh-Dole.
  - Pick research targets that fit Thai feedstock: LFP lithium recovery or regeneration, and production scrap.
- **6-18 months.**
  - Finance a small book with own or institutional money, using tranching, a reserve, concentration limits and a
    controlled account.
  - Run 2-3 sponsored validation sprints. Publish audited outcome metrics: capital deployed to labs, experiments
    with data, IP filed or licensed.
- **18 months and later.**
  - External investors only through a regulated route: an approved ICO portal for Thai investors, or an offshore
    SPV for eligible non-Thai investors with a Thai servicer.
  - Revisit an Avalanche L1 only if a regulator or capital provider requires permissioned validators.

---

## 5. Tokenomics: recommendation

1. **No platform token.**
   - BIO fell about 97% from its listing-day peak, and BioDAO tokens and AUBRAI fell 95-98%.
   - VitaDAO deployed about $4.7M in about five years.
   - No IP-NFT or IP token was found to have produced licensing payouts to holders, and the flagship IP token's
     liquidity is about $60k.
   - Molecule itself moved toward holding IP in a conventional company (its Coin-to-Company model, presented to the
     SEC in March 2026).
   - Bio's model rests on a deliberate "no claim on profits" stance, which a credit product cannot copy.
   - A speculative token would make corporates and Thai regulators judge the platform by its price.
2. **Pool shares, if and when external investors come in:** permissioned and transfer-restricted.
   - Standards: ERC-3643 (T-REX) or Centrifuge V3 memberlist hooks and ERC-7540 async vaults. Centrifuge V3 is
     already deployed on Avalanche.
   - Distribute only through a regulated channel. Pay in native USDC
     (`0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E`), never USDC.e.
   - Contracts and terms must handle USDC freezes.
3. **Research contributions:** non-transferable receipts with no profit rights (hypercert- or soulbound-style),
   for ESG attribution and reputation.
4. **This repo's `SCIFraction` (ERC-1155 with pro-rata revenue distribution) is a testnet demonstration only.**
   - Its revenue rights are profit-like, so on mainnet it would very likely be a security or investment token.
   - Before any mainnet use, make it non-transferable with no revenue rights, or put it behind KYC/allowlist
     compliance through a regulated issuer.
5. **Governance:**
   - A multisig plus timelock on admin and attestor roles.
   - An independent scientific committee decides research funding, with corporate-sponsor recusal and capped
     sponsor weight.
   - No token voting on which projects get money. DAO governance studies show concentrated voting power and low
     participation [unverified].
6. **Avalanche's role:** C-Chain, not an L1. Use it for:
   - the registry of hashed invoices, assignments and collections;
   - milestone escrow for stablecoin sponsors;
   - attestations of lab results and evidence bundles;
   - passkey wallets (secp256r1 precompile) for non-crypto SMEs.

   For grants, apply to the Team1 Mini Grants (up to $10k) and engage Team1 Thailand. Do not plan on Retro9000's
   C-Chain round: it rewards AVAX burned, and an RWA platform burns very little.

---

## 6. Questions the founder needs to answer

1. Who is the first borrower? Name the recycler, its buyer and the invoice history.
2. Who are the first three corporate members, and what IP terms will they accept?
3. Jurisdiction and ownership of each entity (Foreign Business Act).
4. Investors in phase 1: own money, a bank line, or institutional lenders? Any Thai retail at all?
5. Research targets: are you willing to re-target from NCM111 upcycling to LFP or production scrap?
6. Testnet-only demo vs a mainnet timeline. Mainnet requires an audit, a multisig and legal sign-off first.
