import json
import os
import uuid
from datetime import date
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile

from flask import Flask, jsonify, redirect, render_template, request, send_file, session, url_for
from openpyxl import Workbook
from openpyxl.utils.exceptions import InvalidFileException

from engine import ParseError, Trial, load_any, project, session_plan_rows
from store import get_cover_n, list_skus

_EXTRACT_FIELDS = ("stkavail", "fcastbydate", "wo_replen")
_PLAN_HEADERS = ("Part number", "Description", "Week", "Cases")


def create_app(db_path, upload_dir):
    db_path = Path(db_path)
    upload_dir = Path(upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "pch1-local-dev-only")
    app.config["DB_PATH"] = db_path
    app.config["UPLOAD_DIR"] = upload_dir
    app.config["BOARDS"] = {}
    app.config["EXTRACTS"] = {}

    @app.get("/")
    def load_form():
        return render_template("load.html", error=None)

    @app.post("/load")
    def load_extracts():
        saved: list[Path] = []
        try:
            paths = _receive_extracts(request.files, upload_dir, saved)
            extracts = load_any(paths)
            board = project(extracts, list_skus(db_path), [], cover_n=get_cover_n(db_path))
            sid = session.get("sid") or str(uuid.uuid4())
            session["sid"] = sid
            app.config["BOARDS"][sid] = board
            app.config["EXTRACTS"][sid] = extracts
            session["trials"] = []
            session["clear_trials"] = True
            return redirect(url_for("board_page"))
        except ParseError as exc:
            return render_template("load.html", error=exc.message), 200
        except (BadZipFile, InvalidFileException):
            names = ", ".join(path.name for path in saved) or "upload"
            return render_template(
                "load.html",
                error=f"{names}: not a readable Excel file",
            ), 200
        finally:
            for path in saved:
                path.unlink(missing_ok=True)

    @app.get("/board")
    def board_page():
        board = _current_board(app)
        if board is None:
            return redirect(url_for("load_form"))
        clear_trials = bool(session.pop("clear_trials", False))
        return render_template("board.html", board=board, clear_trials=clear_trials)

    @app.post("/board")
    def board_trials():
        try:
            trials = _trials_from_request()
            sid = session.get("sid")
            extracts = app.config["EXTRACTS"].get(sid) if sid else None
            if extracts is None:
                raise ParseError("Load extracts before adding trials")
            board = project(
                extracts,
                list_skus(db_path),
                trials,
                cover_n=get_cover_n(db_path),
            )
            app.config["BOARDS"][sid] = board
            session["trials"] = _trial_payload(trials)
            return jsonify(_board_payload(board))
        except ParseError as exc:
            return jsonify({"error": exc.message}), 400

    @app.route("/session-plan.xlsx", methods=["GET", "POST"])
    def session_plan():
        try:
            if request.method == "POST":
                trials = _trials_from_request()
                session["trials"] = _trial_payload(trials)
            else:
                encoded = request.args.get("trials")
                if encoded:
                    trials = _parse_trials(_decode_trials(encoded))
                else:
                    trials = _parse_trials({"trials": session.get("trials") or []})
            return _plan_workbook(trials, list_skus(db_path))
        except ParseError as exc:
            return jsonify({"error": exc.message}), 400

    return app


def _receive_extracts(files, folder: Path, saved: list[Path]) -> list[Path]:
    named = {key: _uploaded(files, key) for key in (*_EXTRACT_FIELDS, "workbook")}
    extracts = [named[key] for key in _EXTRACT_FIELDS]
    workbook = named["workbook"]
    if all(extracts):
        return [_keep(item, folder, saved) for item in extracts]
    if workbook is not None and not any(extracts):
        return [_keep(workbook, folder, saved)]
    if workbook is not None:
        raise ParseError("Send stkavail, fcastbydate, and wo_replen, or one workbook")
    missing = [key for key, item in zip(_EXTRACT_FIELDS, extracts) if item is None]
    raise ParseError("Missing " + ", ".join(missing))


def _uploaded(files, key):
    item = files.get(key)
    if item is None or not item.filename:
        return None
    return item


def _keep(upload, folder: Path, saved: list[Path]) -> Path:
    name = Path(upload.filename).name
    if not name:
        raise ParseError("Missing file name")
    dest = folder / name
    upload.save(dest)
    saved.append(dest)
    return dest


def _current_board(app):
    sid = session.get("sid")
    if not sid:
        return None
    return app.config["BOARDS"].get(sid)


def _trials_from_request() -> list[Trial]:
    payload = request.get_json(silent=True)
    if payload is None and request.form.get("trials"):
        payload = _decode_trials(request.form["trials"])
    return _parse_trials(payload)


def _decode_trials(raw: str):
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ParseError("trials must be JSON") from exc
    if isinstance(parsed, list):
        return {"trials": parsed}
    return parsed


def _parse_trials(payload) -> list[Trial]:
    if not isinstance(payload, dict):
        raise ParseError("trials payload must be an object")
    raw = payload.get("trials", [])
    if not isinstance(raw, list):
        raise ParseError("trials must be a list")
    trials: list[Trial] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ParseError("trial must include sku, week, and cases")
        sku = item.get("sku")
        week = item.get("week")
        cases = item.get("cases")
        if not sku or week in (None, "") or cases is None:
            raise ParseError("trial must include sku, week, and cases")
        if isinstance(week, date):
            week_date = week
        else:
            try:
                week_date = date.fromisoformat(str(week)[:10])
            except ValueError as exc:
                raise ParseError(f"trial week is not a date: {week}") from exc
        try:
            qty = float(cases)
        except (TypeError, ValueError) as exc:
            raise ParseError(f"trial cases are not a number: {cases}") from exc
        trials.append(Trial(str(sku), week_date, qty))
    return trials


def _trial_payload(trials: list[Trial]) -> list[dict]:
    return [
        {"sku": trial.sku, "week": trial.week.isoformat(), "cases": trial.cases}
        for trial in trials
    ]


def _board_payload(board) -> dict:
    return {
        "stockouts": [
            {
                "part": row.part,
                "description": row.description,
                "week": row.week.isoformat(),
                "cases_short": row.cases_short,
            }
            for row in board.stockouts
        ],
        "cover": [
            {
                "part": row.part,
                "description": row.description,
                "week": row.week.isoformat(),
                "cover_weeks": row.cover_weeks,
            }
            for row in board.cover
        ],
        "series": [
            {
                "part": row.part,
                "description": row.description,
                "opening": row.opening,
                "weeks": [week.isoformat() for week in row.weeks],
                "forecast": row.forecast,
                "production": row.production,
                "trials": row.trials,
                "stock": row.stock,
            }
            for row in board.series
        ],
        "weeks": [week.isoformat() for week in board.weeks],
        "warnings": [
            {"code": warning.code, "message": warning.message}
            for warning in board.warnings
        ],
    }


def _plan_workbook(trials, master):
    wb = Workbook()
    ws = wb.active
    ws.title = "Session plan"
    ws.append(list(_PLAN_HEADERS))
    for row in session_plan_rows(trials, master):
        ws.append(list(row))
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="session-plan.xlsx",
    )
