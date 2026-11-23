# Data scope

The files in `processed/` are saved snapshots supplied with this project. They are not raw source pages and must not be presented as an automated live feed.

| File | Use |
|---|---|
| `programme_index.csv` | Programme and provider search; input to the SQLite loader |
| `fee_source_index.csv` | Index of public fee information sources |
| `fee_snapshot.csv` | Extracted fee records with narrower provider coverage |

Inspect the source/link and date fields in each file before using a row. The prior repository release labelled these snapshots `v1.0`, dated 19 May 2026. That release date does not establish that every source was checked on that day.

`programme_index.csv` includes original and transformed names, classification reasons and scores. These fields preserve useful traceability, but the transformation scripts that produced them are not included in this repository. `Unknown` values are classification gaps, even when ordinary missing-value checks pass.

No additional dataset licence is granted by this documentation. Check the terms of the original providers before redistributing or reusing their material.
