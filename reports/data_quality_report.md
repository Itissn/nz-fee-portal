# Snapshot quality report

The three input files are identified by SHA-256. Dates are recorded provider checks.

| Dataset | Rows | Providers | First check | Last check |
|---|---:|---:|---|---|
| programme_index | 2405 | 66 | 2026-05-14 | 2026-05-19 |
| fee_source_index | 47 | 24 | 2026-05-14 | 2026-05-19 |
| fee_snapshot | 1355 | 6 | 2026-05-14 | 2026-05-14 |

55 programme records have an exact provider-and-name fee match before cohort filters.
A name match can cover multiple fee bases, majors or student groups.

| Dataset | Quality finding | Affected rows |
|---|---|---:|
| fee_snapshot | currency_in_fee_basis | 163 |
| fee_snapshot | missing_fee_basis | 502 |
| fee_snapshot | numeric_programme_name | 472 |
| fee_source_index | unknown_source_year | 21 |
| programme_index | unknown_subject | 541 |

A record can have several findings. The Data quality tab lists individual CSV line numbers.

| Source CSV | SHA-256 |
|---|---|
| fee_snapshot.csv | `90d6cb56a6c99a48c33d3e663a21311317e0f134e7df5bb335de05d70f98d3c6` |
| fee_source_index.csv | `2ecc140c3a32f2c9024a8615b8f02d771df6b2f8eb0dee2e8b10b006d0fc58e6` |
| programme_index.csv | `f2834073daf0782ed051d94c8a8f19f0b6cd069d24dd31076923d8e17ff1b75d` |
