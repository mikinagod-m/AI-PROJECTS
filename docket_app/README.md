# Docket — Aimia Credit Control (prototype)

A small self-hosted app: upload an invoice or debit note, it gets read with
**local OCR (Tesseract)** and classified against the confirmed routing
rules, and lands in a shared queue backed by SQLite. No cloud AI, no API
key, nothing leaves your server — same pattern as the expense-app's
`ocr.py`.

This is still a prototype — good enough for Joan and the team to try out and
react to, not yet hardened for production (see "Known limitations" below).

## 1. Requirements

- Python 3.9 or later (you already have this)
- **Tesseract OCR** and **Poppler** installed on the machine — the same
  system dependencies your expense-app already relies on. If the expense-app
  works on this server, both are already present and you can skip to step 2.
  Otherwise:
  - Windows: install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki
    and Poppler from https://github.com/oschwartz10612/poppler-windows/releases,
    then add both `install-dir\bin` folders to your PATH.
  - macOS: `brew install tesseract poppler`
  - Linux: `apt install tesseract-ocr poppler-utils`

## 2. Install

```
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Run it

```
python app.py
```

You should see it start on port 8001. Open **http://localhost:8001** on the
same machine to check it's working. That local URL is not Joan's live app.

## 4. Let Joan test it (live)

Live server: **http://10.3.0.45:8001**
Live folder: `C:\Users\michaelm1\Documents\docket_app` on that PC.

This laptop copy is for editing. Joan's queue data (`docket.db`, `uploads/`)
lives on the live machine. Do not copy those files from here onto live.

## 5. Ship to live

Only after you have tested on **http://localhost:8001** and someone asks to
update live:

```
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\push-live.ps1 -DryRun
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\push-live.ps1
```

The script copies code only, leaves `docket.db` / `uploads/` / `venv/`
untouched, restarts Docket on the live PC, and checks
**http://10.3.0.45:8001**. If restart fails, double-click **Stop Docket App**
then **Start Docket App** on that PC.

If Joan is **not** on the same network (working from home, different site),
this won't reach her as-is — that needs either a VPN into your office
network, or properly hosting this on a server with a real domain and HTTPS.

## 6. Where your data lives

- `docket.db` — a SQLite file in this folder. This **is** your data. Back it
  up regularly (just copy the file) and don't delete it.
- `uploads/` — the original PDFs/images people upload, referenced by the
  queue so you can always open the source document.

## How accurate is the OCR extraction?

Tested against the real invoices from Sainsbury's, Tesco, Asda, and Bidfood
used to build this prototype:

- **Classification (type, owner, routing)** was correct in every case
  tested — this is straightforward keyword matching against your confirmed
  rules, and doesn't depend on OCR quality nearly as much.
- **Amounts and invoice numbers** were exactly right on 5 of 7 documents
  after tuning. The two misses: one invoice's total simply wasn't found
  (left blank rather than guessed wrong), and two Asda invoices had their
  invoice number missed because of how Tesseract reads a two-column layout.
- Multi-column layouts (address block next to a figures block) are the main
  source of OCR trouble — Tesseract sometimes merges columns onto one
  garbled line. The parsing rules were tuned against this specific failure
  mode, but a supplier changing their invoice template could reintroduce it.

**Every field in the ledger is directly editable** — click into customer,
invoice number, date, or any amount to correct it, same as the notes field.
Nothing here should be trusted blindly; it's built to save typing on the
clear cases and get out of the way on the unclear ones.

## Known limitations (prototype, not production)

- **No login/authentication.** Anyone with the URL can see and edit
  everything. Fine for an internal trial on a trusted network, not fine for
  wider rollout.
- **No automatic ingestion.** Someone still has to download the document
  from email/portal and upload it here — this replaces printing and Unity
  logging, not the initial "getting the file" step.
- **CCDM, CCDL, CCSD (Damages, Delivery Error, Short Delivery)** still route
  to "Various" with no folder, since that wasn't nailed down yet.
- **Single point of failure.** If your machine or the app process stops,
  the app is unreachable until it's restarted. Fine for a trial, not for
  daily production use without more thought given to uptime.
- **Only the first 8 pages of a PDF are read**, to keep uploads fast — fine
  for these invoices, but worth knowing if a much longer document ever
  comes through.
