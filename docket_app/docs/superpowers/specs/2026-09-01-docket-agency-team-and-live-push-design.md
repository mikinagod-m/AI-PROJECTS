# Docket Agency Team and Live Push — Design

**Date:** 2026-09-01
**Status:** Approved (2026-09-01)
**Laptop copy:** `C:\Users\Michaelm1\Documents\AI-Projects\docket_app`
**Live copy:** `\\10.3.0.45\c$\Users\michaelm1\Documents\docket_app`
**Live URL:** `http://10.3.0.45:8001`

## Goal

Give Docket the same working model as the expense app:

1. A named agency team in Cursor so substantial work is scoped, built, and checked before it is treated as done.
2. An explicit one-command push from this laptop copy to the live Windows box, without overwriting Joan's queue data.

Edits happen here. Live does not change until a human asks to push.

## Non-goals

- No copy-on-save and no Cursor `afterFileEdit` hook.
- Do not open or edit the live folder as the day-to-day workspace.
- Do not add authentication, inbox ingest, Postgres, cloud OCR, HTTPS, or a reverse proxy.
- Do not invent owners or folders for CCDM, CCDL, or CCSD.
- Do not overwrite live `docket.db`, `uploads/`, `venv/`, or `.runtime/`.
- Do not auto-push after every agent session. Push only when the user asks.

## Context (confirmed)

Two copies, same pattern as Expenses (`:8000` / `Documents\expense-app`):

| Role | Location |
|---|---|
| Edit | This laptop: `Documents\AI-Projects\docket_app` |
| Live | `10.3.0.45`: `C:\Users\michaelm1\Documents\docket_app`, served on port **8001** |

The expense-app repo has an agency playbook but no deploy script. Updates were copied over the LAN admin share, then the process was restarted. Docket follows that, but as a repeatable script.

Flask runs with `debug=False`, so live Python does not reload on file copy. A push that skips restart leaves Joan on the old build.

## Team

Always-on Cursor rule plus a playbook. Hierarchical: one session orchestrates; specialists do not all rewrite the same file at once.

| Role | Owns | Must not |
|---|---|---|
| Product Lead | Objective, acceptance criteria, Joan's routing table, release risk | Invent CCDM/CCDL/CCSD owners; add luxury features not requested |
| OCR / Classify | `ocr_classify.py` | Reintroduce the eight bugs listed in `PROJECT_BRIEF.md` |
| Backend | `app.py`, SQLite schema, `/api/*`, upload handling | Cloud APIs; replacing SQLite; removing inline field edits |
| Frontend | `templates/index.html` (HTML/CSS/vanilla JS, no build step) | A JS framework; a second `<script>` tag; removing inline editing |
| QA | Local `http://127.0.0.1:8001` (or `http://10.3.2.247:8001`), Needs Review, `node --check` on extracted page JS | Declare done from HTTP 200 alone |
| Deploy | `scripts/push-live.ps1`, live restart, live health check | Copy live data dirs; push without a user request |

`PROJECT_BRIEF.md` is mandatory reading before OCR, routing, or launcher-script work.

## Workflow

For every substantial request:

1. **Intake (Product Lead)** — objective, acceptance criteria, constraints, non-goals.
2. **Build locally** — smallest diff; OCR and UI follow existing files, not a new stack.
3. **Verify (QA)** — exercise the changed path on the laptop app; if `templates/index.html` changed, extract the `<script>` and run `node --check`.
4. **Stop** — do not push.
5. **Push (Deploy)** — only if the user asks to push / ship / update live.
6. **Ship note** — what changed, what was checked, live URL, whether restart succeeded.

Trivial copy tweaks may skip a formal brief but still must not push without a user ask.

## Push script

Path: `scripts/push-live.ps1` (plain ASCII only, same constraint as `start-hidden.ps1` / `stop-hidden.ps1`).

Live destination (fixed, do not invent another path if missing):

```
\\10.3.0.45\c$\Users\michaelm1\Documents\docket_app
```

### Copy

Robocopy (or equivalent) of source files:

**Include:** `app.py`, `ocr_classify.py`, `templates\`, `start-hidden.ps1`, `stop-hidden.ps1`, `Start Docket App.vbs`, `Stop Docket App.vbs`, `requirements.txt`, `README.md`, `PROJECT_BRIEF.md`, `AGENCY_TEAM.md`, `.cursor\rules\agency-team.mdc`, `scripts\push-live.ps1`.

**Exclude:** `docket.db`, `uploads\`, `venv\`, `.runtime\`, `__pycache__\`, `*.pyc`, `.git\`.

Before copy, record live `docket.db` last-write time and size when the file exists. After copy, those values must be unchanged. If they changed, the script failed.

### Restart

After a successful copy, restart via WinRM against `10.3.0.45`:

- Remote working directory: `C:\Users\michaelm1\Documents\docket_app`
- Run `stop-hidden.ps1` then `start-hidden.ps1`
- Start and stop at the same permission level (do not mix elevated and non-elevated)

If WinRM cannot restart: leave the copied files in place, print a clear message that Joan may still be on the old process until someone double-clicks **Stop Docket App** then **Start Docket App** on that PC. Do not treat that as a full success.

### Verify

`Invoke-WebRequest` `http://10.3.0.45:8001` — expect status 200 and HTML title containing `Docket`.

Full success = copy ok + db unchanged + restart ok + health check ok.

### Failure rules

| Condition | Action |
|---|---|
| Live folder missing | Stop. Do not search other paths. |
| Copy fails | Do not restart. |
| Restart fails after copy | Report: code is on disk, process may still be old. |
| Health check fails after restart | Report fail. Do not claim Joan is on the new build. |

## Repo files to add

| File | Purpose |
|---|---|
| `.cursor/rules/agency-team.mdc` | `alwaysApply: true` team contract |
| `AGENCY_TEAM.md` | Playbook and prompt templates |
| `scripts/push-live.ps1` | The only agent-runnable live push |
| `README.md` | Port 8001 (not 8000) plus a short "Ship to live" section |

No new test framework. QA remains local app + `node --check` when JS in `index.html` changes.

## Local vs live

The laptop may also run Docket on port 8001 (`10.3.2.247`). That is not live. Push always targets `10.3.0.45:8001`. Agents must not treat a local 200 as proof that Joan's URL updated.

## Open items unchanged

Auth, auto-ingest, unmapped CCDM/CCDL/CCSD owners, and production hosting stay out of this spec. Flag them; do not build them here.
