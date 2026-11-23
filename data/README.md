# Data scope

These processed CSV snapshots were supplied with the project. Each row retains its provider reference and the original check date. The prior snapshot release was labelled v1.0 on 19 May 2026.

| File | Unit of observation and use |
|---|---|
| [programme_index.csv](processed/programme_index.csv) | One provider's programme page. Import rejects a repeated provider ID and page URL. |
| [fee_source_index.csv](processed/fee_source_index.csv) | One provider reference link, which can cover several courses. Display-title, cohort and year fields take priority where populated. |
| [fee_snapshot.csv](processed/fee_snapshot.csv) | One extracted fee row. Major, specialisation, cohort, year and basis may vary for the same programme. Distinct rows are retained and duplicate input rows reject the release. |

## Interpretation

Fee detail matches on provider ID and the entire programme name with case and whitespace normalised. It excludes numeric-only programme names from exact matches. The fee browser retains flagged records to support checking the extraction. Raw names, transformation notes and extraction methods remain in the saved CSVs.

The date `last_checked` belongs to the source record. Importing an older file today does not update the check date. The SQL manifest stores the file hash and row count. Quality findings carry the CSV filename and ending source line, including the header in line numbering. Missing basis, questionable basis containing a currency sign and unknown classifications are review flags.

Provider pages and fee sources have their own terms. This repository grants no additional licence to redistribute the source material.
