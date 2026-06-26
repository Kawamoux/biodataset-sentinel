# Synthetic example dataset

The files in this directory are synthetic and are intended only to demonstrate
the audit workflow.

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

Expected result:

- no structural errors;
- no batch-outcome confounding warning;
- informational findings for unobserved or constant features.

The example uses balanced batches across two conditions:

| condition | batch |
| --- | --- |
| control | B1, B2, B3 |
| treated | B1, B2, B3 |

This balance is deliberate so the example can be used as a small sanity check
for installation, reporting, and CI scripts.
