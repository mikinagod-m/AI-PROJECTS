from datetime import date, datetime
from typing import Optional

_EXCEL_EPOCH = datetime(1899, 12, 30)


def cell_quantity(value) -> tuple[float, bool]:
    if value is None or value == "":
        return 0.0, False
    if isinstance(value, datetime):
        serial = (value.replace(tzinfo=None) - _EXCEL_EPOCH).days
        return float(serial), True
    if isinstance(value, date) and not isinstance(value, datetime):
        serial = (datetime.combine(value, datetime.min.time()) - _EXCEL_EPOCH).days
        return float(serial), True
    if isinstance(value, (int, float)):
        return float(value), False
    if isinstance(value, str):
        return float(value.replace(",", "").strip()), False
    raise ValueError(f"unreadable quantity: {value!r}")


def cases_per_hour(value) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    if isinstance(value, str):
        return float(value.strip())
    return float(value)