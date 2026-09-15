# Contributing to InkSurf

InkSurf welcomes reproducible contributions that improve evidence auditing for
Vesuvius Challenge workflows.

## Development setup

```bash
python -m venv .venv
python -m pip install -e ".[catalog,benchmark,structure,fragment]"
python -m unittest discover -s tests
```

## Scientific contract

- Declare the track, visibility regime and geometry tier.
- Keep correlated replicas in one `independence_group`.
- Freeze validation selections, metrics and gates before revealing labels.
- Preserve negative results and report baselines, effect sizes and uncertainty.
- Do not commit scan data, hidden-text previews, discovery coordinates, model
  weights or other data-bearing artifacts.
- Add a reproducible config, machine-readable report and tests for meaningful
  changes.

See `AGENTS.md`, `docs/data_governance.md` and
`docs/evidence_consistency_protocol.md` for the complete project rules.
