# tests/test_project.py
from datetime import date
from engine import (
    ExtractSet, SkuMaster, Trial, project, LoadWarning, ParseError
)
import pytest

W1 = date(2026, 11, 16)
W2 = date(2026, 11, 23)
W3 = date(2026, 11, 30)

MASTER = [SkuMaster("CHOC450", "MBK CHOC NRSPO 10X450G", 112.0, "forecast")]


def _ex(opening, forecast, production, warnings=None):
    return ExtractSet(opening, forecast, production, warnings or [])


def test_matches_pch1_chain():
    # opening 100; w1 f=40 p=10 → 70; w2 f=40 p=0 → 30
    extracts = _ex(
        {"CHOC450": 100.0},
        {"CHOC450": {W1: 40.0, W2: 40.0}},
        {"CHOC450": {W1: 10.0, W2: 0.0}},
    )
    board = project(extracts, MASTER, [])
    s = board.series[0]
    assert s.stock == [70.0, 30.0]
    assert board.stockouts == []


def test_blank_is_zero_and_unknown_parts_ignored():
    extracts = _ex(
        {"CHOC450": 5.0, "OTHER": 999.0},
        {"CHOC450": {W1: 0.0}, "OTHER": {W1: 1.0}},
        {"CHOC450": {W1: 0.0}},
    )
    board = project(extracts, MASTER, [])
    assert [s.part for s in board.series] == ["CHOC450"]
    assert board.series[0].stock == [5.0]


def test_stockout_first_negative_week():
    extracts = _ex(
        {"CHOC450": 10.0},
        {"CHOC450": {W1: 5.0, W2: 20.0}},
        {"CHOC450": {W1: 0.0, W2: 0.0}},
    )
    board = project(extracts, MASTER, [])
    assert len(board.stockouts) == 1
    assert board.stockouts[0].week == W2
    assert board.stockouts[0].cases_short == 15.0


def test_missing_opening_stock_warns():
    extracts = _ex({}, {"CHOC450": {W1: 1.0}}, {"CHOC450": {W1: 0.0}})
    board = project(extracts, MASTER, [])
    assert board.series[0].opening == 0.0
    assert any(w.code == "missing_opening_stock" for w in board.warnings)


def test_misaligned_weeks_zero_fill():
    extracts = _ex(
        {"CHOC450": 10.0},
        {"CHOC450": {W1: 10.0}},
        {"CHOC450": {W3: 4.0}},
    )
    board = project(extracts, MASTER, [])
    assert board.weeks == [W1, W3]
    assert board.series[0].forecast == [10.0, 0.0]
    assert board.series[0].production == [0.0, 4.0]
    assert board.series[0].stock == [0.0, 4.0]


def test_cover_excludes_zero_demand():
    extracts = _ex(
        {"CHOC450": 800.0},
        {"CHOC450": {W1: 0.0, W2: 0.0, W3: 0.0}},
        {"CHOC450": {W1: 0.0, W2: 0.0, W3: 0.0}},
    )
    board = project(extracts, MASTER, [], cover_n=8)
    assert board.cover == []


def test_cover_flags_when_above_n():
    extracts = _ex(
        {"CHOC450": 100.0},
        {"CHOC450": {W1: 5.0, W2: 5.0}},
        {"CHOC450": {W1: 0.0, W2: 0.0}},
    )
    board = project(extracts, MASTER, [], cover_n=8)
    assert len(board.cover) == 1
    assert board.cover[0].cover_weeks > 8


def test_trial_adds_production_and_can_clear_stockout():
    extracts = _ex(
        {"CHOC450": 0.0},
        {"CHOC450": {W1: 10.0}},
        {"CHOC450": {W1: 0.0}},
    )
    board = project(extracts, MASTER, [])
    assert board.stockouts
    board2 = project(extracts, MASTER, [Trial("CHOC450", W1, 10.0)])
    assert board2.stockouts == []
    assert board2.series[0].trials == [10.0]
    assert board2.series[0].stock == [0.0]


def test_trial_invalid_sku():
    extracts = _ex({"CHOC450": 0.0}, {"CHOC450": {W1: 0.0}}, {"CHOC450": {W1: 0.0}})
    with pytest.raises(ParseError, match="SKU"):
        project(extracts, MASTER, [Trial("NOPE", W1, 1.0)])


def test_horizon_includes_weeks_from_non_master_rows():
    # CHOC450 only has W1 forecast; OTHER's W3 production is still a horizon column.
    extracts = _ex(
        {"CHOC450": 10.0},
        {"CHOC450": {W1: 4.0}},
        {"OTHER": {W3: 7.0}},
    )
    board = project(extracts, MASTER, [Trial("CHOC450", W3, 3.0)])
    assert board.weeks == [W1, W3]
    s = board.series[0]
    assert s.production == [0.0, 0.0]
    assert s.trials == [0.0, 3.0]
    assert s.stock == [6.0, 9.0]
