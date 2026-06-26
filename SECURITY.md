# Security and data handling

BioDataset Sentinel is designed for pre-analysis review of biological datasets.
It should be run before sharing data, reports, or derived artifacts outside a
controlled research environment.

## Supported data policy

The repository only contains synthetic example data. Do not commit:

- patient-level data;
- human participant metadata;
- unreleased collaborator data;
- local filesystem paths;
- credentials, tokens, keys, or service URLs;
- reports generated from private datasets.

Generated reports should be treated as research artifacts because they may
contain sample identifiers, feature identifiers, and metadata-derived context.

## Reporting concerns

Open a GitHub issue for reproducible problems that do not disclose private data.
For anything involving sensitive files or private datasets, share only a minimal
synthetic reproduction.

## Local review before publication

Before publishing a dataset or report, run:

```bash
biosentinel audit \
  --samples samples.csv \
  --matrix matrix.csv \
  --json-report report.json \
  --html-report report.html
```

Then review all `privacy_*` findings manually. The scanner is conservative; it
helps prioritize review, but it does not certify that a dataset is safe to
share.
