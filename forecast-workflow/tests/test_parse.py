from datetime import date, datetime, timedelta
from pathlib import Path
import pytest
from engine import ParseError, horizon_weeks, parse_extracts, parse_workbook_extracts
from tests.xlsx_helpers import write_stkavail, write_fcast, write_wo, write_three_sheet_book

W1 = date(2026, 11, 16)
W2 = date(2026, 11, 23)
W3 = date(2026, 11, 30)
W4 = date(2026, 12, 7)


def test_parse_phys_stock_ignores_free_stock(tmp_path):
    stk = tmp_path / "stk.xlsx"
    fc = tmp_path / "fc.xlsx"
    wo = tmp_path / "wo.xlsx"
    write_stkavail(stk, [("CHOC450", 100, 9999)])
    write_fcast(fc, [W1, W2], [("CHOC450", [10, 10])])
    write_wo(wo, [W1, W2], [("CHOC450", [0, 0])])
    result = parse_extracts(stk, fc, wo)
    assert result.opening["CHOC450"] == 100.0


def test_before_column_ignored(tmp_path):
    stk = tmp_path / "stk.xlsx"
    fc = tmp_path / "fc.xlsx"
    wo = tmp_path / "wo.xlsx"
    write_stkavail(stk, [("CHOC450", 100, 0)])
    write_fcast(fc, [W1], [("CHOC450", [10])])
    write_wo(wo, [W1], [("CHOC450", [5])], before_values=[8000])
    result = parse_extracts(stk, fc, wo)
    assert result.production["CHOC450"][W1] == 5.0


def test_date_formatted_production_quantity(tmp_path):
    stk = tmp_path / "stk.xlsx"
    fc = tmp_path / "fc.xlsx"
    wo = tmp_path / "wo.xlsx"
    write_stkavail(stk, [("A006GV-M", 0, 0)])
    write_fcast(fc, [W1], [("A006GV-M", [0])])
    write_wo(wo, [W1], [("A006GV-M", [0])], date_qty_cells=[(2, 0, datetime(1911, 6, 12))])
    result = parse_extracts(stk, fc, wo)
    assert result.production["A006GV-M"][W1] == 4181.0
    assert any(w.code == "date_quantity" for w in result.warnings)


def test_horizon_union_when_weeks_do_not_align():
    forecast = {"CHOC450": {W1: 10.0, W2: 10.0}}
    production = {"CHOC450": {W2: 5.0, W3: 5.0, W4: 1.0}}
    assert horizon_weeks(forecast, production) == [W1, W2, W3, W4]


def test_unknown_parts_are_kept_in_extract_but_filter_is_later(tmp_path):
    stk = tmp_path / "stk.xlsx"
    fc = tmp_path / "fc.xlsx"
    wo = tmp_path / "wo.xlsx"
    write_stkavail(stk, [("OTHER", 1, 0), ("CHOC450", 2, 0)])
    write_fcast(fc, [W1], [("OTHER", [1]), ("CHOC450", [1])])
    write_wo(wo, [W1], [("OTHER", [0]), ("CHOC450", [0])])
    result = parse_extracts(stk, fc, wo)
    assert "OTHER" in result.opening
    assert "CHOC450" in result.opening


def test_missing_sheet_raises(tmp_path):
    bad = tmp_path / "bad.xlsx"
    write_stkavail(bad, [("CHOC450", 1, 0)])
    with pytest.raises(ParseError, match="fcastbydate"):
        parse_extracts(bad, bad, bad)


def test_one_workbook_three_tabs(tmp_path):
    book = tmp_path / "all.xlsx"
    write_three_sheet_book(
        book, [W1],
        [("CHOC450", 50, 0)],
        [("CHOC450", [3])],
        [("CHOC450", [1])],
    )
    result = parse_workbook_extracts(book)
    assert result.opening["CHOC450"] == 50.0
    assert result.forecast["CHOC450"][W1] == 3.0
