# Implementation notes

The UI, reusable logic, commands and examples have different responsibilities:

1. `app/streamlit_app.py` loads three saved CSV snapshots and owns the public interface filters and coverage flags. `src/portal_search.py` retains separately tested search helpers; the current public UI does not call that module.
2. `src/db_utils.py` handles CSV-to-SQLite loading and database inspection. `scripts/build_database.py` is its runnable entry point.
3. `scripts/data_quality_report.py` profiles the input and writes a Markdown report. The CI workflow runs tests and produces its own report artifact.
4. `examples/` contains exploratory database queries. These are not required for the app to start.

`local_db/` is generated and ignored by Git. Keep dependencies, local settings and secrets out of the repository. Run all documented commands from the repository root.

The current layout supports inspecting and loading an existing snapshot. Reconstructing the original extraction and cleaning steps would be a separate development task.
