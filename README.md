# NZ Fee Portal
This portal is a prototype reference tool. Tuition fees and programme information should always be verified through the official provider links. The extracted fee snapshots are not guaranteed to cover all providers or all programmes.

A prototype Streamlit web app for searching New Zealand tertiary education programme pages, official fee-source links, and extracted fee snapshots.

Data version: v1.0
Last updated: 2026-05-19
Programme entries: 2405
Official fee sources: 47
Extracted fee snapshots: 1355

## What this app includes

- Programme searchable entries: **2405**
- Programme providers represented: **66**
- Official fee-source links: **47**
- Fee-source providers represented: **24**
- Extracted fee snapshots: **1355**
- Fee-snapshot providers represented: **6**

Generated: `2026-05-19T16:42:28`

## Run locally

```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

## Deploy on Streamlit Community Cloud

Use this repository as the source repo and set the main file path to:

```text
app/streamlit_app.py
```

## Data notes

This is a prototype reference portal, not an official fee database. Users should verify tuition information through the official source links.

The extracted fee snapshot table is not full coverage for all providers; it contains only records that were successfully parsed and cleaned.
