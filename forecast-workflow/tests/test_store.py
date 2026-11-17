from store import init_db, seed_if_empty, list_skus, get_cover_n, set_cover_n, upsert_sku, delete_sku
from engine import SkuMaster


def test_seed_twelve_and_supskim_zero(tmp_path):
    db = tmp_path / "pch1.sqlite"
    init_db(db)
    seed_if_empty(db)
    skus = {s.part: s for s in list_skus(db)}
    assert len(skus) == 12
    assert skus["SUPSKIM-123"].cases_per_hour == 0.0
    assert skus["SCGM500-123"].cases_per_hour is None
    assert skus["CHOC450"].demand_driver == "forecast"
    assert get_cover_n(db) == 8


def test_seed_not_duplicated(tmp_path):
    db = tmp_path / "pch1.sqlite"
    init_db(db)
    seed_if_empty(db)
    seed_if_empty(db)
    assert len(list_skus(db)) == 12


def test_cover_n_roundtrip(tmp_path):
    db = tmp_path / "pch1.sqlite"
    init_db(db)
    set_cover_n(db, 12)
    assert get_cover_n(db) == 12