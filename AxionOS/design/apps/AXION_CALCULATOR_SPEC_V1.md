# AXION Calculator Spec v1

## Product
- Name: **Axion Calculator**
- ID: `axion-calculator`

## Design Goals
- Windows-familiar layout, Axion-native implementation
- Fast launch, keyboard-first friendly
- Standard + Scientific + Financial tabs

## Tabs (v1)

### 1) Standard
- basic arithmetic
- percent, memory keys, sign toggle

### 2) Scientific
- trig/log/power/root
- degrees/radians mode

### 3) Mortgage
Inputs:
- home price / loan principal
- down payment (amount or %)
- APR
- term (years)
- property tax (annual)
- homeowners insurance (annual)
- PMI (optional)
- HOA (optional)

Outputs:
- monthly P&I
- monthly escrow total
- full monthly payment
- total interest paid
- amortization summary

### 4) Credit Cards
Inputs:
- current balance
- APR
- minimum payment rule
- planned monthly payment

Outputs:
- payoff months
- total interest
- interest saved vs minimum-only
- payoff date estimate

### 5) Car Loans
Inputs:
- vehicle price
- down payment
- trade-in value
- taxes/fees
- APR
- term months

Outputs:
- amount financed
- monthly payment
- total paid
- total interest

## UX Requirements
- persistent last-used tab
- clear input validation and inline error hints
- copy/share result summary
- optional "save scenario" snapshots (local)

## Data/Privacy
- local-only by default
- no cloud sync required in v1
- saved scenarios stored in user profile space

## Accessibility
- full keyboard navigation
- screen-reader labels
- high-contrast mode support

## v1 Definition of Done
- All five tabs functional with correct formulas and edge-case handling
- Finance outputs match verification vectors within tolerance
- Startup < 300ms warm launch target
