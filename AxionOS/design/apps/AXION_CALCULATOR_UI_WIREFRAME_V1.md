# AXION Calculator UI Wireframe v1

Product: Axion Calculator (`axion-calculator`)

## 1) Window Layout

```text
+--------------------------------------------------------------------------------+
| AXION CALCULATOR                                                   [ _ ][□][X] |
+-------------------------+--------------------------------------+---------------+
| Tabs                    | Display Panel                        | Quick Actions |
|-------------------------|--------------------------------------|---------------|
| [Standard]              | Main Value:  1,245.67               | [Copy Result] |
| [Scientific]            | Expression: 1250 - 4.33             | [Reset]       |
| [Mortgage]              | Status: Valid Input                 | [Save Scenario]|
| [Credit Cards]          |                                      | [Load Scenario]|
| [Car Loans]             |                                      | [Export TXT]  |
+-------------------------+--------------------------------------+---------------+
| Input/Keypad Area                                                              |
| (dynamic by selected tab)                                                      |
+--------------------------------------------------------------------------------+
| Footer: Mode | Precision | Memory | Last Saved | Local-only indicator           |
+--------------------------------------------------------------------------------+
```

## 2) Tab-Specific Wireframes

### A) Standard

```text
+-----------------------------------+
| Display: 0                        |
+-----------------------------------+
| MC MR M+ M- MS                    |
| %  CE  C  ⌫                       |
| 1/x x² √  ÷                       |
| 7  8  9  ×                        |
| 4  5  6  −                        |
| 1  2  3  +                        |
| ±  0  .  =                        |
+-----------------------------------+
```

### B) Scientific

```text
+--------------------------------------------------+
| Display / Expression                             |
+--------------------------------------------------+
| sin cos tan ln log π e  DEG/RAD                 |
| ( ) xʸ √x n! mod                                |
| memory row + core keypad                         |
+--------------------------------------------------+
```

### C) Mortgage

```text
+---------------- Mortgage Inputs -----------------+
| Principal/Home Price: [__________]              |
| Down Payment:         [____] [%|$]              |
| APR (%):              [____]                    |
| Term (years):         [____]                    |
| Property Tax (yr):    [____]                    |
| Insurance (yr):       [____]                    |
| PMI (mo, optional):   [____]                    |
| HOA (mo, optional):   [____]                    |
+---------------- Mortgage Results ----------------+
| P&I Monthly:          $________                  |
| Escrow Monthly:       $________                  |
| Total Monthly:        $________                  |
| Total Interest:       $________                  |
| Payoff Date:          __________                 |
| [View Amortization] [Copy Summary]              |
+--------------------------------------------------+
```

### D) Credit Cards

```text
+--------------- Credit Card Inputs --------------+
| Current Balance:       [__________]             |
| APR (%):               [____]                   |
| Minimum Rule:          [x% or flat]             |
| Planned Monthly Pay:   [____]                   |
+--------------- Credit Card Results -------------+
| Payoff Months:         ________                 |
| Total Interest:        $________                |
| Interest Saved:        $________                |
| Estimated Payoff Date: __________               |
| [Compare Min vs Planned] [Copy Summary]         |
+--------------------------------------------------+
```

### E) Car Loans

```text
+---------------- Car Loan Inputs ----------------+
| Vehicle Price:         [__________]             |
| Down Payment:          [__________]             |
| Trade-In Value:        [__________]             |
| Taxes + Fees:          [__________]             |
| APR (%):               [____]                   |
| Term (months):         [____]                   |
+---------------- Car Loan Results ---------------+
| Amount Financed:       $________                |
| Monthly Payment:       $________                |
| Total Paid:            $________                |
| Total Interest:        $________                |
| [Copy Summary]                                  |
+--------------------------------------------------+
```

## 3) Interaction Notes

- Every input change recalculates in real time (debounced).
- Invalid fields show inline red hint + tooltip reason.
- Finance tabs support `Save Scenario` snapshots locally.
- `Enter` triggers recompute; `Ctrl+C` copies selected result block.

## 4) State/Color Chips

- Valid: blue indicator
- Warning (edge case): amber
- Error (invalid/no payoff): red

## 5) Accessibility

- Full tab order through fields
- Screen-reader label for each input and result
- Keyboard shortcuts documented in Help overlay
