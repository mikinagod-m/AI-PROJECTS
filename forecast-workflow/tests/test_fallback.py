from datetime import date
import pytest
from openpyxl import Workbook
from engine import ParseError, load_any, parse_pch1_grid

W1 = date(2026, 11, 16)


def test_grid_reads_three_row_blocks(tmp_path):
    path = tmp_path / "pch1.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "PCH1"
    ws["D1"] = "DATA"
    ws["E1"] = W1
    ws["A3"] = "CHOC450"
    ws["B3"] = "MBK CHOC NRSPO 10X450G"
    ws["D3"] = "FORECAST"
    ws["E3"] = 40
    ws["C4"] = 112
    ws["D4"] = "PRODUCTION"
    ws["E4"] = 10
    ws["B5"] = "STOCK AVAILABLE"
    ws["D5"] = 100
    wb.save(path)
    extracts = parse_pch1_grid(path)
    assert extracts.opening["CHOC450"] == 100.0
    assert extracts.forecast["CHOC450"][W1] == 40.0
    assert extracts.production["CHOC450"][W1] == 10.0
    assert any(w.code == "fallback_pch1_grid" for w in extracts.warnings)


def test_load_any_prefers_three_tabs_over_grid(tmp_path):
    from openpyxl import load_workbook
    from tests.xlsx_helpers import write_three_sheet_book
    path = tmp_path / "all.xlsx"
    write_three_sheet_book(path, [W1], [("CHOC450", 50, 0)], [("CHOC450", [3])], [("CHOC450", [1])])
    wb = load_workbook(path)
    ws = wb.create_sheet("PCH1", 0)
    ws["E1"] = W1
    ws["A3"] = "CHOC450"
    ws["D3"] = "FORECAST"
    ws["E3"] = 1
    ws["D4"] = "PRODUCTION"
    ws["E4"] = 1
    ws["B5"] = "STOCK AVAILABLE"
    ws["D5"] = 999
    wb.save(path)
    extracts = load_any([path])
    assert extracts.opening["CHOC450"] == 50.0
    assert extracts.forecast["CHOC450"][W1] == 3.0
    assert all(w.code != "fallback_pch1_grid" for w in extracts.warnings)


def test_grid_ignores_cached_week_stock(tmp_path):
    path = tmp_path / "pch1.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "PCH1"
    ws["E1"] = W1
    ws["A3"] = "CHOC450"
    ws["D3"] = "FORECAST"
    ws["E3"] = 40
    ws["D4"] = "PRODUCTION"
    ws["E4"] = 10
    ws["B5"] = "STOCK AVAILABLE"
    ws["D5"] = 100
    ws["E5"] = 70
    wb.save(path)
    extracts = parse_pch1_grid(path)
    assert extracts.opening["CHOC450"] == 100.0
    assert extracts.forecast["CHOC450"][W1] == 40.0
    assert extracts.production["CHOC450"][W1] == 10.0


def test_load_any_pch1_only_uses_grid(tmp_path):
    path = tmp_path / "pch1.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "PCH1"
    ws["E1"] = W1
    ws["A3"] = "CHOC450"
    ws["D3"] = "FORECAST"
    ws["E3"] = 40
    ws["D4"] = "PRODUCTION"
    ws["E4"] = 10
    ws["B5"] = "STOCK AVAILABLE"
    ws["D5"] = 100
    wb.save(path)
    extracts = load_any([path])
    assert extracts.opening["CHOC450"] == 100.0
    assert extracts.forecast["CHOC450"][W1] == 40.0
    assert extracts.production["CHOC450"][W1] == 10.0
    assert any(w.code == "fallback_pch1_grid" for w in extracts.warnings)


def test_load_any_three_files(tmp_path):
    from tests.xlsx_helpers import write_fcast, write_stkavail, write_wo
    stk = tmp_path / "stk.xlsx"
    fc = tmp_path / "fc.xlsx"
    wo = tmp_path / "wo.xlsx"
    write_stkavail(stk, [("CHOC450", 80, 1)])
    write_fcast(fc, [W1], [("CHOC450", [4])])
    write_wo(wo, [W1], [("CHOC450", [2])])
    extracts = load_any([stk, fc, wo])
    assert extracts.opening["CHOC450"] == 80.0
    assert extracts.forecast["CHOC450"][W1] == 4.0
    assert extracts.production["CHOC450"][W1] == 2.0
    assert all(w.code != "fallback_pch1_grid" for w in extracts.warnings)


def test_load_any_rejects_unknown_workbook(tmp_path):
    path = tmp_path / "other.xlsx"
    wb = Workbook()
    wb.active.title = "Sheet1"
    wb.save(path)
    with pytest.raises(ParseError):
        load_any([path])
    with pytest.raises(ParseError):
        load_any([])
