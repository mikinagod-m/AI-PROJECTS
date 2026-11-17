# tests/test_app.py
import json
import re
from datetime import date
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook, load_workbook

from app import create_app
from engine import SkuMaster, Trial, session_plan_rows
from store import init_db, seed_if_empty
from tests.xlsx_helpers import write_fcast, write_stkavail, write_wo

W1 = date(2026, 11, 16)


def _client(tmp_path):
    db = tmp_path / "pch1.sqlite"
    init_db(db)
    seed_if_empty(db)
    app = create_app(db_path=db, upload_dir=tmp_path / "up")
    app.config["TESTING"] = True
    return app.test_client()


def _post_extracts(client, tmp_path, opening, forecast, production):
    stk, fc, wo = tmp_path / "s.xlsx", tmp_path / "f.xlsx", tmp_path / "w.xlsx"
    write_stkavail(stk, [("CHOC450", opening, 0)])
    write_fcast(fc, [W1], [("CHOC450", [forecast])])
    write_wo(wo, [W1], [("CHOC450", [production])])
    return client.post(
        "/load",
        data={
            "stkavail": (stk.open("rb"), "stkavail.new2.xlsx"),
            "fcastbydate": (fc.open("rb"), "fcastbydate.xlsx"),
            "wo_replen": (wo.open("rb"), "wo.replen.xlsx"),
        },
        content_type="multipart/form-data",
    )


def test_load_redirects_to_board(tmp_path):
    c = _client(tmp_path)
    rv = _post_extracts(c, tmp_path, opening=100, forecast=10, production=0)
    assert rv.status_code in (302, 303)
    assert "/board" in rv.headers["Location"]
    board = c.get("/board")
    assert board.status_code == 200
    assert (
        b"CHOC450" in board.data
        or b"Stockout" in board.data
        or b"stockout" in board.data.lower()
        or b"PCH1" in board.data
    )


def test_load_error_names_file(tmp_path):
    c = _client(tmp_path)
    rv = c.post("/load", data={}, content_type="multipart/form-data")
    assert rv.status_code == 200
    assert b"stkavail" in rv.data.lower() or b"Missing" in rv.data


def test_board_lists_stockout_and_disclaimer(tmp_path):
    # opening 0, forecast 10, production 0 → stockout week W1
    c = _client(tmp_path)
    loaded = _post_extracts(c, tmp_path, opening=0, forecast=10, production=0)
    assert loaded.status_code in (302, 303)
    board = c.get("/board")
    assert board.status_code == 200
    assert b"is-break" in board.data
    assert b"10 short" in board.data
    assert b"starter default" in board.data
    assert b"No projected stockouts on PCH1 for this horizon." not in board.data


def test_board_healthy_load_has_empty_stockout_sentence(tmp_path):
    # opening 100, forecast 10, production 0 → stock stays positive
    c = _client(tmp_path)
    loaded = _post_extracts(c, tmp_path, opening=100, forecast=10, production=0)
    assert loaded.status_code in (302, 303)
    board = c.get("/board")
    assert board.status_code == 200
    assert b"No projected stockouts on PCH1 for this horizon." in board.data
    assert b"is-break" not in board.data
    assert b"10 short" not in board.data


def test_tray_focus_ring_is_on_the_bar():
    css = Path(__file__).resolve().parents[1].joinpath("static", "app.css").read_text(
        encoding="utf-8"
    )
    assert ".tray-check:focus-visible ~ .tray-toggle" in css
    desktop = css.split("@media (min-width: 900px)", 1)[1]
    assert re.search(r"\.tray-check\s*\{\s*display:\s*none\s*;", desktop)


def test_board_without_load_redirects_home(tmp_path):
    c = _client(tmp_path)
    rv = c.get("/board")
    assert rv.status_code == 302
    assert rv.headers["Location"].endswith("/")


def test_load_deletes_uploaded_temps(tmp_path):
    c = _client(tmp_path)
    rv = _post_extracts(c, tmp_path, opening=100, forecast=10, production=0)
    assert rv.status_code in (302, 303)
    assert list((tmp_path / "up").glob("*.xlsx")) == []


def test_load_parse_error_names_file_without_traceback(tmp_path):
    c = _client(tmp_path)
    bad = tmp_path / "bad.xlsx"
    wb = Workbook()
    wb.active.title = "Notes"
    wb.save(bad)
    rv = c.post(
        "/load",
        data={"workbook": (bad.open("rb"), "tracker.xlsx")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 200
    assert b"Traceback" not in rv.data
    assert b"tracker.xlsx" in rv.data
    assert list((tmp_path / "up").glob("*.xlsx")) == []


def test_load_non_zip_names_file_without_traceback(tmp_path):
    c = _client(tmp_path)
    rv = c.post(
        "/load",
        data={"workbook": (BytesIO(b"this is not a spreadsheet"), "notes.xlsx")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 200
    assert b"notes.xlsx" in rv.data
    assert b"Traceback" not in rv.data
    assert list((tmp_path / "up").glob("*")) == []


def test_post_board_applies_trial(tmp_path):
    c = _client(tmp_path)
    loaded = _post_extracts(c, tmp_path, opening=0, forecast=10, production=0)
    assert loaded.status_code in (302, 303)
    rv = c.post(
        "/board",
        json={"trials": [{"sku": "CHOC450", "week": "2026-11-16", "cases": 10}]},
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["stockouts"] == []
    assert set(data) >= {"stockouts", "cover", "series", "weeks", "warnings"}
    assert "2026-11-16" in data["weeks"]


def test_post_board_unknown_sku_is_message(tmp_path):
    c = _client(tmp_path)
    _post_extracts(c, tmp_path, opening=0, forecast=10, production=0)
    rv = c.post(
        "/board",
        json={"trials": [{"sku": "NOPE", "week": "2026-11-16", "cases": 1}]},
    )
    assert rv.status_code == 400
    assert b"Traceback" not in rv.data
    assert b"NOPE" in rv.data


def test_session_plan_xlsx(tmp_path):
    c = _client(tmp_path)
    _post_extracts(c, tmp_path, opening=0, forecast=10, production=0)
    rv = c.post(
        "/session-plan.xlsx",
        json={"trials": [{"sku": "CHOC450", "week": "2026-11-16", "cases": 10}]},
    )
    assert rv.status_code == 200
    assert rv.mimetype in (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",
    )
    wb = load_workbook(BytesIO(rv.data))
    ws = wb.active
    assert [ws.cell(1, col).value for col in range(1, 5)] == [
        "Part number",
        "Description",
        "Week",
        "Cases",
    ]
    assert ws.cell(2, 1).value == "CHOC450"
    assert ws.cell(2, 2).value == "MBK CHOC NRSPO 10X450G"
    assert ws.cell(2, 4).value == 10


def test_get_session_plan_uses_last_posted_trials(tmp_path):
    c = _client(tmp_path)
    _post_extracts(c, tmp_path, opening=0, forecast=10, production=0)
    posted = c.post(
        "/board",
        json={"trials": [{"sku": "CHOC450", "week": "2026-11-16", "cases": 4}]},
    )
    assert posted.status_code == 200
    rv = c.get("/session-plan.xlsx")
    assert rv.status_code == 200
    wb = load_workbook(BytesIO(rv.data))
    assert wb.active.cell(2, 1).value == "CHOC450"
    assert wb.active.cell(2, 4).value == 4


def _html_attr(html, name):
    match = re.search(rf"\b{name}='([^']*)'", html)
    assert match, name
    return match.group(1)


def test_board_publishes_master_weeks_and_clears_once(tmp_path):
    c = _client(tmp_path)
    loaded = _post_extracts(c, tmp_path, opening=0, forecast=10, production=0)
    assert loaded.status_code in (302, 303)
    board = c.get("/board")
    html = board.data.decode()
    assert 'data-clear-trials="1"' in html
    master = json.loads(_html_attr(html, "data-master"))
    weeks = json.loads(_html_attr(html, "data-weeks"))
    assert "CHOC450" in master
    assert "2026-11-16" in weeks
    again = c.get("/board")
    assert 'data-clear-trials="0"' in again.data.decode()


def test_board_js_stores_trials_and_downloads_plan():
    js = Path(__file__).resolve().parents[1].joinpath("static", "board.js").read_text(
        encoding="utf-8"
    )
    assert "pch1.trials" in js
    assert "sessionStorage" in js
    assert 'fetch("/board"' in js or "fetch('/board'" in js
    assert "session-plan.xlsx" in js
    assert "data-clear-trials" in js
    assert "data-master" in js
    assert "data-weeks" in js
    assert "if (stored.length)" not in js
    assert "commit(stored)" in js
    assert "if (inFlight) return" in js
    assert "inFlight = false" in js
    assert "requestSeq" not in js


def test_session_plan_rows_uses_master_description():
    rows = session_plan_rows(
        [Trial("CHOC450", W1, 10)],
        [SkuMaster("CHOC450", "MBK CHOC NRSPO 10X450G", 112.0, "forecast")],
    )
    assert rows == [("CHOC450", "MBK CHOC NRSPO 10X450G", W1, 10.0)]
