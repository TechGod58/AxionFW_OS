from calculator_app import (
    evaluate,
    simple_interest,
    compound_interest,
    mortgage_payment,
    snapshot,
)


def test_calculator_eval():
    out = evaluate("2+2")
    assert out["ok"] is True
    assert out["result"] == 4


def test_calculator_simple_interest():
    out = simple_interest(1000, 5, 2)
    assert out["ok"] is True
    assert out["code"] == "CALC_SIMPLE_INTEREST_OK"
    assert out["interest"] == 100.0
    assert out["total"] == 1100.0


def test_calculator_compound_interest():
    out = compound_interest(1000, 5, 1, compounds_per_year=12)
    assert out["ok"] is True
    assert out["code"] == "CALC_COMPOUND_INTEREST_OK"
    assert out["total"] > 1050.0


def test_calculator_mortgage_payment():
    out = mortgage_payment(300000, 6.5, 30)
    assert out["ok"] is True
    assert out["code"] == "CALC_MORTGAGE_OK"
    assert out["monthly_payment"] > 1000.0
    assert out["months"] == 360


def test_calculator_snapshot_modes():
    snap = snapshot()
    assert snap["ready"] is True
    assert "mortgage" in snap["modes"]
