import ast
import json
import math


def _safe_eval(expr: str):
    node = ast.parse(str(expr), mode="eval")
    allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.Mod,
        ast.USub,
        ast.UAdd,
        ast.FloorDiv,
    )
    for sub in ast.walk(node):
        if not isinstance(sub, allowed_nodes):
            raise ValueError("unsupported expression")
    return eval(compile(node, "<calculator>", "eval"), {"__builtins__": {}}, {})


def evaluate(expr: str):
    try:
        value = _safe_eval(expr)
    except Exception:
        return {"ok": False, "code": "CALC_EVAL_FAIL"}
    return {"ok": True, "code": "CALC_OK", "result": value}


def simple_interest(principal: float, annual_rate_pct: float, years: float):
    p = float(principal)
    r = float(annual_rate_pct) / 100.0
    t = float(years)
    interest = p * r * t
    total = p + interest
    return {
        "ok": True,
        "code": "CALC_SIMPLE_INTEREST_OK",
        "principal": p,
        "annual_rate_pct": float(annual_rate_pct),
        "years": t,
        "interest": round(interest, 2),
        "total": round(total, 2),
    }


def compound_interest(principal: float, annual_rate_pct: float, years: float, compounds_per_year: int = 12):
    p = float(principal)
    r = float(annual_rate_pct) / 100.0
    t = float(years)
    n = int(compounds_per_year)
    if n <= 0:
        return {"ok": False, "code": "CALC_COMPOUNDS_INVALID"}
    total = p * math.pow((1.0 + (r / n)), (n * t))
    interest = total - p
    return {
        "ok": True,
        "code": "CALC_COMPOUND_INTEREST_OK",
        "principal": p,
        "annual_rate_pct": float(annual_rate_pct),
        "years": t,
        "compounds_per_year": n,
        "interest": round(interest, 2),
        "total": round(total, 2),
    }


def mortgage_payment(principal: float, annual_rate_pct: float, years: int):
    p = float(principal)
    years_int = int(years)
    if years_int <= 0:
        return {"ok": False, "code": "CALC_MORTGAGE_TERM_INVALID"}
    monthly_rate = float(annual_rate_pct) / 100.0 / 12.0
    n = years_int * 12
    if monthly_rate == 0:
        payment = p / n
    else:
        factor = math.pow(1.0 + monthly_rate, n)
        payment = p * ((monthly_rate * factor) / (factor - 1.0))
    total_paid = payment * n
    total_interest = total_paid - p
    return {
        "ok": True,
        "code": "CALC_MORTGAGE_OK",
        "principal": p,
        "annual_rate_pct": float(annual_rate_pct),
        "years": years_int,
        "months": n,
        "monthly_payment": round(payment, 2),
        "total_paid": round(total_paid, 2),
        "total_interest": round(total_interest, 2),
    }


def snapshot():
    return {
        "app": "Calculator",
        "app_id": "calculator",
        "ready": True,
        "modes": [
            "standard",
            "scientific",
            "simple_interest",
            "compound_interest",
            "mortgage",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(evaluate("2+2"), indent=2))
