from datetime import datetime, date
from engine import cell_quantity, cases_per_hour


def test_blank_quantity_is_zero():
    assert cell_quantity(None) == (0.0, False)
    assert cell_quantity("") == (0.0, False)


def test_numeric_quantity():
    assert cell_quantity(1272) == (1272.0, False)
    assert cell_quantity(1272.5) == (1272.5, False)
    assert cell_quantity("3816") == (3816.0, False)


def test_date_cell_uses_excel_serial_not_display():
    # Tracker bug: 4181 formatted as date shows 12-Jun-1911
    qty, was_date = cell_quantity(datetime(1911, 6, 12))
    assert was_date is True
    assert qty == 4181.0


def test_date_only_serial():
    qty, was_date = cell_quantity(date(1911, 6, 12))
    assert was_date is True
    assert qty == 4181.0


def test_cases_per_hour_normalizes():
    assert cases_per_hour(None) is None
    assert cases_per_hour("") is None
    assert cases_per_hour("0") == 0.0
    assert cases_per_hour(0) == 0.0
    assert cases_per_hour("156") == 156.0
    assert cases_per_hour(182) == 182.0