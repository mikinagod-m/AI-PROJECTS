from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from openpyxl import load_workbook

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


class ParseError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class LoadWarning:
    code: str
    message: str


@dataclass
class ExtractSet:
    opening: dict[str, float]
    forecast: dict[str, dict[date, float]]
    production: dict[str, dict[date, float]]
    warnings: list[LoadWarning]


_SHEET_STOCK = "stkavail.new2"
_SHEET_FORECAST = "fcastbydate"
_SHEET_WO = "wo.replen"


def horizon_weeks(forecast, production) -> list[date]:
    weeks: set[date] = set()
    for series in (forecast, production):
        for by_week in series.values():
            weeks.update(by_week)
    return sorted(weeks)


def parse_extracts(stk_path, fcast_path, wo_path) -> ExtractSet:
    opening, stock_warnings = _read_opening(stk_path)
    forecast, forecast_warnings = _read_series(
        fcast_path,
        _SHEET_FORECAST,
        part_fallback=2,
        first_week_col=4,
        skip_before=False,
    )
    production, production_warnings = _read_series(
        wo_path,
        _SHEET_WO,
        part_fallback=2,
        first_week_col=5,
        skip_before=True,
    )
    return ExtractSet(
        opening,
        forecast,
        production,
        [*stock_warnings, *forecast_warnings, *production_warnings],
    )


def parse_workbook_extracts(path) -> ExtractSet:
    wb = load_workbook(path, data_only=False)
    try:
        opening, stock_warnings = _opening_from_book(wb, path)
        forecast, forecast_warnings = _series_from_book(
            wb,
            path,
            _SHEET_FORECAST,
            part_fallback=2,
            first_week_col=4,
            skip_before=False,
        )
        production, production_warnings = _series_from_book(
            wb,
            path,
            _SHEET_WO,
            part_fallback=2,
            first_week_col=5,
            skip_before=True,
        )
    finally:
        wb.close()
    return ExtractSet(
        opening,
        forecast,
        production,
        [*stock_warnings, *forecast_warnings, *production_warnings],
    )


def _read_opening(path):
    wb = load_workbook(path, data_only=False)
    try:
        return _opening_from_book(wb, path)
    finally:
        wb.close()


def _read_series(path, sheet_name, part_fallback, first_week_col, skip_before):
    wb = load_workbook(path, data_only=False)
    try:
        return _series_from_book(
            wb, path, sheet_name, part_fallback, first_week_col, skip_before
        )
    finally:
        wb.close()


def _opening_from_book(wb, path):
    ws = _require_sheet(wb, path, _SHEET_STOCK)
    warnings: list[LoadWarning] = []
    header_row, headers = _header(ws)
    part_col = _locate_column(
        headers, "part number", 4, path, _SHEET_STOCK, warnings, "Part Number"
    )
    phys_col = _locate_column(
        headers, "phys stock", 6, path, _SHEET_STOCK, warnings, "Phys Stock"
    )
    opening: dict[str, float] = {}
    for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
        part = _part_key(_at(row, part_col))
        if part is None:
            continue
        opening[part] = _quantity(
            _at(row, phys_col),
            warnings,
            source=_source(path, _SHEET_STOCK),
            part=part,
            week=None,
        )
    return opening, warnings


def _series_from_book(wb, path, sheet_name, part_fallback, first_week_col, skip_before):
    ws = _require_sheet(wb, path, sheet_name)
    warnings: list[LoadWarning] = []
    header_row, headers = _header(ws)
    part_col = _locate_column(
        headers, "part number", part_fallback, path, sheet_name, warnings, "Part Number"
    )
    week_cols = _week_columns(headers, first_week_col, skip_before)
    if not week_cols:
        raise ParseError(f"{_file_name(path)}: sheet {sheet_name} has no dated week columns")
    series: dict[str, dict[date, float]] = {}
    source = _source(path, sheet_name)
    for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
        part = _part_key(_at(row, part_col))
        if part is None:
            continue
        by_week = series.setdefault(part, {})
        for col, week in week_cols:
            by_week[week] = _quantity(
                _at(row, col),
                warnings,
                source=source,
                part=part,
                week=week,
            )
    return series, warnings


def _require_sheet(wb, path, sheet_name):
    if sheet_name in wb.sheetnames:
        return wb[sheet_name]
    folded = sheet_name.casefold()
    for name in wb.sheetnames:
        if name.strip().casefold() == folded:
            return wb[name]
    raise ParseError(f"{_file_name(path)}: sheet {sheet_name} not found")


def _header(ws):
    last = min(ws.max_row or 1, 25)
    header_row = 1
    for row_idx in range(1, last + 1):
        values = [cell.value for cell in ws[row_idx]]
        if any(_header_text(value) == "part number" for value in values):
            header_row = row_idx
            break
    headers = [cell.value for cell in ws[header_row]]
    return header_row, headers


def _locate_column(headers, header_name, fallback, path, sheet_name, warnings, label):
    for idx, value in enumerate(headers, start=1):
        if _header_text(value) == header_name:
            return idx
    if len(headers) < fallback:
        raise ParseError(f"{_file_name(path)}: sheet {sheet_name} missing {label} column")
    warnings.append(
        LoadWarning(
            "column_fallback",
            f"{_file_name(path)}: sheet {sheet_name} missing {label} header; using column {_col_letter(fallback)}",
        )
    )
    return fallback


def _week_columns(headers, first_week_col, skip_before):
    found = []
    for idx, value in enumerate(headers, start=1):
        if idx < first_week_col:
            continue
        if skip_before and _header_text(value) == "before":
            continue
        week = _as_week(value)
        if week is not None:
            found.append((idx, week))
    return found


def _quantity(value, warnings, source, part, week):
    try:
        qty, was_date = cell_quantity(value)
    except ValueError as exc:
        warnings.append(
            LoadWarning(
                "unreadable_quantity",
                f"{source}: unreadable quantity for {part}: {exc}",
            )
        )
        return 0.0
    if was_date:
        when = f" {week.isoformat()}" if week is not None else ""
        warnings.append(
            LoadWarning(
                "date_quantity",
                f"{source}: date-formatted quantity for {part}{when} read as {qty:g}",
            )
        )
    return qty


def _part_key(value):
    if value is None or isinstance(value, (bool, datetime, date)):
        return None
    text = str(value).strip()
    if text == "":
        return None
    return text


def _as_week(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _header_text(value) -> str:
    if isinstance(value, str):
        return value.strip().casefold()
    return ""


def _at(row, col):
    index = col - 1
    if index < 0 or index >= len(row):
        return None
    return row[index]


def _source(path, sheet_name) -> str:
    return f"{_file_name(path)} sheet {sheet_name}"


def _file_name(path) -> str:
    return Path(path).name


def _col_letter(index: int) -> str:
    letters = ""
    while index > 0:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


@dataclass
class SkuMaster:
    part: str
    description: str
    cases_per_hour: Optional[float]
    demand_driver: str


@dataclass
class Trial:
    sku: str
    week: date
    cases: float


@dataclass
class SkuSeries:
    part: str
    description: str
    opening: float
    weeks: list[date]
    forecast: list[float]
    production: list[float]
    trials: list[float]
    stock: list[float]


@dataclass
class Stockout:
    part: str
    description: str
    week: date
    cases_short: float


@dataclass
class CoverFlag:
    part: str
    description: str
    week: date
    cover_weeks: float


@dataclass
class Board:
    series: list[SkuSeries]
    stockouts: list[Stockout]
    cover: list[CoverFlag]
    warnings: list[LoadWarning]
    weeks: list[date]


# PHASE 2: material netter (BOM, PO, lead time) — not implemented
def project(extracts: ExtractSet, master: list[SkuMaster], trials: list[Trial], cover_n: int = 8) -> Board:
    parts = [sku.part for sku in master]
    weeks = horizon_weeks(
        {part: extracts.forecast.get(part, {}) for part in parts},
        {part: extracts.production.get(part, {}) for part in parts},
    )
    week_set = set(weeks)
    master_parts = set(parts)
    trial_cases: dict[tuple[str, date], float] = {}
    for trial in trials:
        if trial.sku not in master_parts:
            raise ParseError(f"trial SKU not on master: {trial.sku}")
        if trial.week not in week_set:
            raise ParseError(f"trial week not on horizon: {trial.week.isoformat()}")
        key = (trial.sku, trial.week)
        trial_cases[key] = trial_cases.get(key, 0.0) + trial.cases

    warnings = list(extracts.warnings)
    series: list[SkuSeries] = []
    stockouts: list[Stockout] = []
    cover: list[CoverFlag] = []
    for sku in master:
        opening, missing = _opening_for(extracts.opening, sku.part)
        if missing:
            warnings.append(
                LoadWarning(
                    "missing_opening_stock",
                    f"{sku.part}: missing opening stock",
                )
            )
        forecast = [_at_week(extracts.forecast, sku.part, week) for week in weeks]
        production = [_at_week(extracts.production, sku.part, week) for week in weeks]
        trial_row = [trial_cases.get((sku.part, week), 0.0) for week in weeks]
        stock = _project_stock(opening, forecast, production, trial_row)
        series.append(
            SkuSeries(
                sku.part,
                sku.description,
                opening,
                list(weeks),
                forecast,
                production,
                trial_row,
                stock,
            )
        )
        stockout = _first_stockout(sku.part, sku.description, weeks, stock)
        if stockout is not None:
            stockouts.append(stockout)
        flag = _cover_flag(sku.part, sku.description, weeks, forecast, stock, cover_n)
        if flag is not None:
            cover.append(flag)
    return Board(series, stockouts, cover, warnings, weeks)


def _opening_for(opening: dict[str, float], part: str) -> tuple[float, bool]:
    if part not in opening:
        return 0.0, True
    return float(opening[part]), False


def _at_week(series: dict[str, dict[date, float]], part: str, week: date) -> float:
    return float(series.get(part, {}).get(week, 0.0))


def _project_stock(opening, forecast, production, trials) -> list[float]:
    previous = opening
    stock: list[float] = []
    for forecast_qty, production_qty, trial_qty in zip(forecast, production, trials):
        previous = previous - forecast_qty + production_qty + trial_qty
        stock.append(previous)
    return stock


def _first_stockout(part, description, weeks, stock) -> Optional[Stockout]:
    for week, qty in zip(weeks, stock):
        if qty < 0:
            return Stockout(part, description, week, abs(qty))
    return None


def _cover_flag(part, description, weeks, forecast, stock, cover_n) -> Optional[CoverFlag]:
    best_week = None
    best_cover = None
    for index, week in enumerate(weeks):
        window = forecast[index:index + cover_n]
        if not window:
            continue
        average = sum(window) / len(window)
        if average == 0:
            continue
        cover_weeks = stock[index] / average
        if best_cover is None or cover_weeks > best_cover:
            best_cover = cover_weeks
            best_week = week
    if best_cover is None or best_week is None or best_cover <= cover_n:
        return None
    return CoverFlag(part, description, best_week, best_cover)
