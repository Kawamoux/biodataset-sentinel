# Validation model

BioDataset Sentinel treats pre-analysis quality control as a sequence of
deterministic checks. Each check produces zero or more structured issues. Issues
are sorted by severity and code so repeated runs remain easy to compare.

## Inputs

The audit engine accepts three logical tables:

- sample metadata, keyed by `sample_id`;
- measurement matrix, keyed by `feature_id` with sample identifiers as columns;
- optional feature metadata, keyed by `feature_id`.

The engine does not store absolute input paths in the report object. Reports
refer to a dataset label supplied by the caller.

## Issue severity

`error` means the data cannot be trusted for downstream analysis until the
problem is fixed. Examples include duplicated identifiers, missing matrix
columns, invalid numeric cells, or unmatched sample IDs.

`warning` means the data can be parsed but should be reviewed before analysis.
Examples include possible batch confounding, low replicate counts, suspicious
privacy patterns, or atypical total signal.

`info` means the observation is useful for documentation or filtering decisions.
Examples include all-zero features and constant features.

## Robust signal checks

Per-sample total signal is summarized with minimum, median, and maximum values.
Outliers are identified using the median absolute deviation when at least four
samples are available. This avoids overreacting to one large value when
estimating the center of the cohort.

## Categorical association

Batch-outcome association is summarized with Cramer's V. A value close to 1
means the variables are strongly associated. The current warning threshold is
0.85 for datasets with at least four complete batch/outcome pairs.

This is a design warning, not a hypothesis test. It is meant to tell the analyst
that biological interpretation may be difficult without a batch-aware model or a
more balanced design.

## Privacy checks

The privacy scanner looks for conservative patterns in metadata values and
headers:

- e-mail-like values;
- Windows, Unix, or network path-like values;
- phone-like values;
- long token-like values.

These findings require human review. The scanner does not attempt to classify
real personal data; it identifies values that should not be shared blindly.

## Report contract

JSON reports contain:

- `dataset_name`;
- `created_at_utc`;
- `summary`;
- `issues`;
- `metrics`.

HTML reports render the same information for human review. Both formats are
derived from the same `AuditReport` object.
