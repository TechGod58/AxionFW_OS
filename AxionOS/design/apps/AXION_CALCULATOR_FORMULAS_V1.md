# AXION Calculator Formula Notes v1

## Mortgage (fixed rate)
Monthly rate: r = APR / 12
Payments: n = years * 12
Payment (P&I):
M = P * [r(1+r)^n] / [(1+r)^n - 1]

Total monthly housing estimate:
M_total = M + (tax_annual/12) + (insurance_annual/12) + PMI + HOA

## Credit Card payoff approximation
Given balance B, monthly rate r, payment A:
If A <= B*r then negative amortization (no payoff)
Otherwise payoff months:
N = -ln(1 - rB/A) / ln(1+r)

## Car loan (fixed)
Same installment formula as mortgage using term in months.
Amount financed = price - down - trade_in + taxes_fees
