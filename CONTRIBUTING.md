# Contributing

Contributions are welcome when they keep the project reliable, transparent, and
easy to audit.

## Development workflow

```bash
python -m pip install -e .
python -m unittest discover -s tests
```

The runtime package intentionally has no external dependency. New dependencies
should be proposed only when they materially improve correctness or
maintainability.

## Adding a check

Each new check should provide:

- a stable issue code;
- a severity level;
- a concise message;
- an actionable recommendation;
- tests for positive and negative cases;
- documentation when the scientific rationale is not obvious.

## Data hygiene

Use synthetic fixtures. Do not commit private datasets, local paths, generated
reports from real projects, credentials, or collaborator exports.

When in doubt, reduce a case to the smallest synthetic CSV needed to reproduce
the behavior.
