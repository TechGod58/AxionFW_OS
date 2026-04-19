# AXION Calculator Test Vectors v1

Purpose: verify financial calculations with reproducible baseline scenarios.

## Tolerance
- Monthly payment tolerance: ± $0.05
- Total interest tolerance: ± $1.00
- Month count tolerance (cards): ± 1 month

---

## Vector 1: Mortgage

Inputs:
- Principal: 250000
- APR: 6.50%
- Term: 30 years
- Property Tax (yr): 3600
- Insurance (yr): 1200
- PMI: 0
- HOA: 0

Expected (approx):
- P&I Monthly: $1580.17
- Escrow Monthly: $400.00
- Total Monthly: $1980.17
- Total Interest (loan only): $318861.20

---

## Vector 2: Credit Card

Inputs:
- Balance: 8000
- APR: 22.99%
- Planned Monthly Payment: 250

Expected (approx):
- Payoff Months: 48
- Total Interest: $3930.00
- Payoff possible: YES

Negative amortization check:
- If payment <= monthly interest, return explicit "No payoff under current payment".

---

## Vector 3: Car Loan

Inputs:
- Vehicle Price: 30000
- Down Payment: 3000
- Trade-In: 2000
- Taxes+Fees: 1500
- APR: 7.00%
- Term: 60 months

Derived:
- Amount Financed: 26500

Expected (approx):
- Monthly Payment: $524.73
- Total Paid: $31483.80
- Total Interest: $4983.80

---

## QA Notes

- Use fixed-rate installment formula for mortgage/car loan tabs.
- Use payoff-month formula with no-payoff guard for credit cards.
- Verify rounding strategy is consistent (display vs internal precision).
