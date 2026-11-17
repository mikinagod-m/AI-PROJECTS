# PCH1 stock risk

Flask app for Cheryl’s PCH1 Monday review: load Unity extracts, see stockouts and cover, stack trial production, download a session plan. There is **no Unity write-back** and no saved planning history.

## Run locally

From this folder (with dependencies from `requirements.txt` installed):

```bash
python app.py
```

Open **http://127.0.0.1:5053** (override with the `PORT` environment variable). On first run the app creates `pch1.sqlite` and seeds the PCH1 line master.

## Loading data

On **Load extracts**, Cheryl can either:

1. **Primary:** upload three Unity exports — `stkavail`, `fcastbydate`, and `wo.replen` (Excel files).
2. **Fallback:** upload one workbook that contains the same three sheet names (`stkavail.new2`, `fcastbydate.new`, `wo.replen`). This mirrors the filled **PCH1 Stock Planning Tracker** layout until live Unity pulls exist.

The board projects finished goods only; it does not replace Warwick’s material logic.

## Settings

**Cover weeks** defaults to **8** and is labelled as a **starter default — confirm with planning**, not a signed factory rule. Change it under **Cover weeks** in the UI.

## Line master

Twelve PCH1 SKUs are seeded on a fresh database. Edit parts, descriptions, and cases/hour under **Line master** (cases/hour is stored for future use; stock math does not use it in v1).

## Session trials and download

Trials apply only for the current browser session. Use **Download session plan** for a spreadsheet of trial adds Cheryl intends to raise — not an automatic push to Unity.