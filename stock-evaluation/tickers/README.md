# Ticker playbooks

One markdown file per ticker (or fund), named by its SEC-style ticker (`META.md`, `BRK-B.md`,
`QQQ.md`). It is the first thing the skill reads for that name, so keep it to what the next
evaluation needs: thesis and the adjustments that encode it, scenario anchors with the company's own
history, company-specific data sources and quirks, what to watch, a dated log.

The working files (`inputs.json`, `narrative.py`, `reports/`, `source/`) live in
`~/AlphaResearch/research/<TICKER>/`, not here: the playbook is the knowledge, the folder is the
state. Start a new one from `_TEMPLATE.md`.
