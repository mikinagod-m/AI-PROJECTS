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

from engine import ParseError, SkuMaster, Trial, cases_per_hour, load_any, project, session_plan_rows
from store import delete_sku, get_cover_n, init_db, list_skus, seed_if_empty, set_cover_n, upsert_sku

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
        sid = session.get("sid")
        extracts = app.config["EXTRACTS"].get(sid) if sid else None
        if extracts is None:
            return redirect(url_for("load_form"))
        master = list_skus(db_path)
        cover_n = get_cover_n(db_path)
        trials = _parse_trials({"trials": session.get("trials") or []})
        try:
            board = project(extracts, master, trials, cover_n=cover_n)
        except ParseError:
            trials = []
            session["trials"] = []
            board = project(extracts, master, trials, cover_n=cover_n)
        app.config["BOARDS"][sid] = board
        clear_trials = bool(session.pop("clear_trials", False))
        return render_template(
            "board.html",
            board=board,
            clear_trials=clear_trials,
            cover_n=cover_n,
            cover_n_label="starter default — confirm with planning",
            master_parts=[sku.part for sku in master],
            weeks=[week.isoformat() for week in board.weeks],
        )

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

    @app.get("/master")
    def master_page():
        return render_template("master.html", skus=list_skus(db_path), error=None)

    @app.post("/master")
    def master_save():
        try:
            upsert_sku(db_path, _sku_from_form())
        except ParseError as exc:
            return render_template(
                "master.html",
                skus=list_skus(db_path),
                error=exc.message,
            ), 200
        return redirect(url_for("master_page"))

    @app.post("/master/delete")
    def master_delete():
        part = (request.form.get("part") or "").strip()
        if part:
            delete_sku(db_path, part)
        return redirect(url_for("master_page"))

    @app.get("/settings")
    def settings_page():
        return render_template(
            "settings.html",
            cover_n=get_cover_n(db_path),
            error=None,
        )

    @app.post("/settings")
    def settings_save():
        raw = (request.form.get("cover_n") or "").strip()
        try:
            cover_n = int(raw)
        except ValueError:
            return render_template(
                "settings.html",
                cover_n=get_cover_n(db_path),
                error="Cover weeks must be a whole number",
            ), 200
        set_cover_n(db_path, cover_n)
        return redirect(url_for("settings_page"))

    return app


def _sku_from_form() -> SkuMaster:
    part = (request.form.get("part") or "").strip()
    description = (request.form.get("description") or "").strip()
    if not part or not description:
        raise ParseError("Part and description are required")
    try:
        rate = cases_per_hour(request.form.get("cases_per_hour", ""))
    except ValueError as exc:
        raise ParseError("Cases per hour must be a number") from exc
    return SkuMaster(part, description, rate, "forecast")


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


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    db = root / "pch1.sqlite"
    uploads = root / "uploads"
    init_db(db)
    seed_if_empty(db)
    application = create_app(db_path=db, upload_dir=uploads)
    port = int(os.environ.get("PORT", 5053))
    application.run(host="0.0.0.0", port=port, debug=False)
