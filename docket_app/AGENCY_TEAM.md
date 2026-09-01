# Docket Agency Team Playbook

Reusable agency team for Docket (Aimia credit control) so work stays scoped, checked on this laptop, and only then shipped to live `http://10.3.0.45:8001`.

Read `PROJECT_BRIEF.md` in full before OCR, classification, or launcher-script work.

## Team Structure

### 1) Product Lead
- Converts requests into objective, acceptance criteria, constraints, and non-goals.
- Treats Joan's routing table as the source of truth.
- Does not invent owners or folders for CCDM, CCDL, or CCSD.

### 2) OCR / Classify
- Owns `ocr_classify.py` (local Tesseract + keyword rules, no cloud AI).
- Must not reintroduce: VAT rate vs VAT amount, sort-code-as-date, header-row totals, first-page-only OCR, two-column suffix matching, duplicate `<script>` (frontend), non-ASCII in `.ps1`, or deleting the pid file after a failed stop.

### 3) Backend
- Owns `app.py`, SQLite `documents` table, `/api/*`, `uploads/` handling.
- OCR is there to save typing, not to be trusted blindly. Keep every ledger field editable.

### 4) Frontend
- Owns `templates/index.html` (HTML, CSS, vanilla JS, no build step).
- Tabs: Queue, Needs Review, Upload, Routing Rules.
- After editing this file, extract the `<script>` contents and run `node --check`. HTTP 200 is not proof the JS runs.

### 5) QA
- Exercises the changed path on `http://127.0.0.1:8001` (laptop). That is not Joan's URL.
- Covers happy path plus Needs Review / missing fields.
- Does not declare done from an HTTP 200 alone.

### 6) Deploy
- Owns `scripts/push-live.ps1`.
- Copies code only to `\\10.3.0.45\c$\Users\michaelm1\Documents\docket_app`.
- Never copies `docket.db`, `uploads/`, `venv/`, or `.runtime/`.
- Runs only when the user asks to push, ship, or update live.

## Default Workflow

1. **Intake (Product Lead)** - objective, acceptance criteria, constraints, non-goals.
2. **Build locally** - smallest diff in the existing files.
3. **Verify (QA)** - laptop app; `node --check` if page JS changed.
4. **Stop** - do not push.
5. **Push (Deploy)** - only if the user asked.
6. **Ship note** - what changed, what was checked, `http://10.3.0.45:8001`, restart result.

Trivial copy tweaks may skip a formal brief. They still must not push without a user ask.

## Reusable Prompt Templates

### Product Lead Prompt
"Turn this request into a concrete implementation brief for Docket: objective, acceptance criteria, non-goals, constraints from PROJECT_BRIEF.md, and release risk. Do not invent CCDM/CCDL/CCSD owners."

### OCR / Classify Prompt
"Change ocr_classify.py with the smallest diff. Do not reintroduce the bugs listed in PROJECT_BRIEF.md. Include how to verify with a sample upload or notes field."

### Backend Prompt
"Implement the Flask/SQLite change in app.py with a minimal diff. Keep inline field edits. Do not add cloud APIs or replace SQLite."

### Frontend Prompt
"Change templates/index.html only as needed. Vanilla JS, one script block. After editing, extract the script and run node --check."

### QA Prompt
"Test the changed Docket behaviour on http://127.0.0.1:8001, including the failure/Needs Review path. Do not treat a local 200 as a live update."

### Deploy Prompt
"Run scripts/push-live.ps1 only because the user asked to update live. Do not copy docket.db, uploads, venv, or .runtime. Report copy, db-unchanged, restart, and http://10.3.0.45:8001 health."

## Definition of Ready
- Request is specific enough to implement.
- Success criteria are testable on the laptop copy.

## Definition of Done
- Acceptance criteria met locally.
- QA evidence is more than HTTP 200.
- Live updated only via push-live.ps1 after an explicit user ask.
