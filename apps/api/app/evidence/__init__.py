"""Evidence engine: judge a research submission against REAL patents and REAL literature.

    submission ──> elements (claim parser, or quoted decomposition)
              └──> queries (chemistry-aware expansion) ──> sources (OpenAlex, Crossref, Semantic Scholar,
                   arXiv, PatentsView, EPO OPS, Lens, local BigQuery-built patent corpus) ──> dedupe,
                   priority-date filter, rank
    elements x top references ──> judgments (disclosed / partial / absent), each backed by a verbatim
                                   quote from the reference that a program has checked
    submission ──> TRL from evidence (battery recycling / upcycling rubric, quoted cues)
    everything ──> report + sha256 of the evidence bundle (anchorable in the on-chain AttestationRegistry)

Design rules learned from auditing MatDAO's IP stack (see docs/RESEARCH.md):
  * no invented data: test fixtures carry TEST- ids and are refused outside test mode;
  * closed world: a model judges only references we retrieved; it cannot introduce patent numbers or DOIs;
  * quotes are checked, not trusted; a judgment whose quote is not in the reference does not count;
  * coverage is reported with every conclusion ("not found in the 40 references from 4 sources"),
    never a bare novelty score; FTO output is a signal for an attorney, never a clearance.
"""
