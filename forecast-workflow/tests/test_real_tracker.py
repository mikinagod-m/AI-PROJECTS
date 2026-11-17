from pathlib import Path

import pytest

from engine import parse_workbook_extracts, project
from store import init_db, list_skus, seed_if_empty

TRACKER = Path(__file__).resolve().parents[1] / "PCH1 Stock Planning Tracker Formula.xlsx"


@pytest.mark.skipif(not TRACKER.exists(), reason="tracker workbook not in repo")
def test_real_tracker_identity(tmp_path):
    extracts = parse_workbook_extracts(TRACKER)
    db = tmp_path / "db.sqlite"
    init_db(db)
    seed_if_empty(db)
    board = project(extracts, list_skus(db), [])
    s = board.series[0]
    expected = s.opening - s.forecast[0] + s.production[0] + s.trials[0]
    assert s.stock[0] == expected