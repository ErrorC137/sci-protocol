"""Corpus curation pipeline: watch funder pages, propose corpus changes, a human approves them.

    sites.yaml -> crawl (robots.txt, slow, conditional GET) -> textify (HTML / PDF / DOCX, Thai encodings)
      -> change detection (skip pages whose text has not changed)
      -> extract (Claude, or deterministic Thai/English heuristics without a key)
      -> verify (every value needs a quote found verbatim in the fetched text, or it is dropped)
      -> review queue YAML (decision: pending) -> `apply` merges only accepted items into grants.yaml

Nothing is ever marked `verified: true` automatically: the queue says what the page says, a person
decides whether the corpus should say it too.
"""
