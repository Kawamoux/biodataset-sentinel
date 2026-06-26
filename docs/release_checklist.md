# Release checklist

Use this checklist before tagging a release or sharing generated reports.

## Repository checks

```bash
python -m unittest discover -s tests
```

Confirm that the repository contains only synthetic data:

- `examples/` should contain small, documented fixtures;
- generated `reports/` and `results/` directories should stay untracked;
- no private data, credentials, or local machine paths should be present.

## Functional smoke test

```bash
biosentinel audit \
  --samples examples/samples.csv \
  --matrix examples/counts.csv \
  --features examples/features.csv \
  --outcome-column condition \
  --batch-column batch \
  --html-report report.html \
  --json-report report.json
```

Expected result for the bundled example:

- status `pass`;
- zero errors;
- zero warnings;
- informational findings for filtering decisions.

## Report review

Before sharing any report generated from real data:

- inspect `privacy_*` findings;
- confirm sample identifiers are suitable for the intended audience;
- confirm feature identifiers and descriptions do not reveal restricted study
  details;
- avoid publishing raw report files when a summarized quality statement is
  sufficient.
