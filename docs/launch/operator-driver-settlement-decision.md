# D05: Fès operator-to-driver settlement decision packet

Prepared 3 November 2026 for [R1/R7](../real-world-launch.md) and
[GAP-024](../gaps.md). Status: **PROPOSAL — no financial policy approved**.
The operating name **Fès Taxi Union** is a working label, not a verified legal
entity. This packet requests decisions from its accountable operator/finance
lead and the owner. It does not authorize a payout, cash collection, real-money
test, production migration, or settlement access grant.

## What the current system proves

The backend records a completed passenger payment, one driver earning for that
payment, immutable fare/fee components, and an operator-allocation amount.
Cash is completed only after explicit assigned-driver confirmation; manual
transfer is completed only after an authorized reviewer matches an external
statement. A `PENDING` payment is not a settled earning. The current refund
contract records only confirmed returned money and funds every refund from the
operator, with zero driver recovery. See [payments](../payments.md),
[pricing](../pricing.md), [operations](../operations.md), and the
[database model](../database.md).

No settlement period, cash remittance, driver payable, payout evidence,
carryover, dispute hold, or closed-period correction exists. `driver_earnings`
is a source fact, not a payment instruction or proof of what reached a bank.
The proposed examples below use the currently documented fee and refund
formulas; their cash-custody and period-clearing treatments remain choices.

## Accounting identities to approve

For each settled ride, retain the immutable `passenger_total`, `driver_net`,
`operator_allocation`, currency, method, city/operator, payment/earning IDs,
tariff/fee/scheduling versions, and settlement timestamp. The current pricing
model enforces:

```text
passenger_total = driver_net + operator_allocation
driver_net = driver_gross - operator_fee_deduction + driver_adjustments
```

The first equality describes the existing no-extra-adjustment quote examples.
If future approved adjustments change the net, the ledger must separately
explain the difference instead of forcing it into operator allocation. A
refund is a separate operator-funded fact; it does not edit the original ride,
payment, earning, or this historical allocation.

The settlement ledger must separately track **earned** driver amount,
**physical custody**, **cash due to the operator**, **operator due to the
driver**, **amount actually remitted/paid**, and **unresolved balance**. No
single `net` field may stand in for all six. Each entry remains scoped to one
currency; no cross-currency netting is implied.

## Worked examples for finance review

The amounts are synthetic MAD examples, not approved Fès fares or fee policy.
Each uses a 40.00 transport fare and a 2.00 operator fee funded through
`DRIVER_SETTLEMENT_DEDUCTION`, with no adjustment or scheduling surcharge.

| Settled ride | Passenger paid | Driver earning | Operator allocation | Where 40.00 is held after payment | Provisional obligation to decide |
| --- | ---: | ---: | ---: | --- | --- |
| `CASH` | 40.00 | 38.00 | 2.00 | Driver collected cash | Driver remits 2.00 to operator if the approved model lets the driver retain 38.00. |
| `MANUAL_TRANSFER` | 40.00 | 38.00 | 2.00 | Verified operator-controlled recipient, **if approved** | Operator pays 38.00 to driver if that recipient is the operator's settlement account. |

For one of each ride, the source facts show 80.00 passenger-paid, 76.00 earned
by the driver, and 4.00 operator allocation. They do **not** decide whether
the 2.00 cash remittance and 38.00 transfer payable may offset:

| Clearing choice | Actual movements for this example | Ledger requirement |
| --- | --- | --- |
| A. Separate remittance and payout | Driver remits 2.00; operator pays 38.00. | Record two references, two confirmations, and each outstanding balance independently. |
| B. Authorized net clearing | Operator pays 36.00 after applying a documented 2.00 cash offset. | Record both original obligations, the 2.00 offset and its approval, the 36.00 movement and reference; never replace the original 38.00 earning. |

Neither option is selected here. A cash-only period must not display a negative
driver payout as if money had moved. A transfer-only period must not display a
paid earning until payout evidence is reconciled. Pending cash and unverified
transfer claims contribute **zero** settled earning and must remain outside the
payable calculation.

The same decomposition applies to scheduled work. For an illustrative 5.00
operator-beneficiary scheduling surcharge on the 40.00 ride above, passenger
total is 45.00, driver net remains 38.00, and operator allocation is 7.00.
The approved policy must say whether the scheduling amount shares the same
cash-remittance and transfer-clearing rules; the ledger cannot infer this from
the payment method alone.

For a later confirmed 10.00 passenger refund on any example, the original
38.00 driver earning stays unchanged under the current operator-funded refund
policy. A new 10.00 operator refund expense and its actual cash/outbound
reference must be recorded separately. If a driver hands the refund to a cash
passenger, finance must decide and evidence the reimbursement or authorized
offset; the app cannot silently reduce the earning or remittance.

## Decisions required before schema or payout implementation

| ID | Accountable decision | Choices and evidence required |
| --- | --- | --- |
| S01 | Legal counterparty and custody | Name the registered organization, each payment recipient, who legally holds passenger cash/transfer proceeds, who can receive driver remittances, and the bank/cash-handling evidence. The generic union label is insufficient. |
| S02 | Period and cutoff | Choose daily/weekly/other period, Fès local cutoff, late-settlement placement, driver/operator/city scope, closure authority, holidays and correction window. Do not derive the period from an API timestamp or server timezone. |
| S03 | Clearing method | Select A separate movements or B authorized net clearing above, or provide another fully balanced worked example. Specify whether cash may offset transfer payables, whether balances carry over, and when a cash debt blocks payout. |
| S04 | Fee/surcharge treatment | Approve the actual Fès tariff and one versioned operator-fee mode/funding policy; identify scheduling-surcharge beneficiary and how each component clears for cash and transfer. Zero values must remain explicit. |
| S05 | Adjustments, refund and dispute holds | Define allowed signed line types, approval thresholds, evidence, reversal/correction process, whether a dispute holds only a payout or also cash remittance, and how an operator-funded refund handed out by a driver is reimbursed. No driver recovery from refunds is approved today. |
| S06 | Payment execution and proof | Choose manual payout/remittance channel for launch, account ownership checks, maker/checker roles, unique external reference, statement-import or independent readback, failure/return handling, and what exactly changes `PENDING` to `PAID`. A requested payout is not a paid payout. |
| S07 | Access, statements and records | Assign who opens/closes periods, approves offsets and payouts, reconciles bank/cash evidence, sees private driver statements, handles disputes, and exports accounting entries. Specify retention/hold and privacy approval for those records. |
| S08 | Exit thresholds | Approve acceptable aged balance, unreconciled amount, duplicate/missing payout tolerance, close delay, pilot volume, stop authority and escalation before any real-money pilot. |

The operator/finance lead should sign worked cases for cash, transfer, mixed
method, scheduled surcharge, partial refund, duplicate reference, late
settlement and disputed payout. The owner then records the approved policy
version, effective date, scope and reviewers in the governed launch evidence.

## Proposed implementation after approval

1. Add append-only period, obligation, clearing/offset, remittance, payout,
   correction and evidence-reference records, each keyed by driver,
   operator, city, currency and policy version. Keep the existing payment and
   earning snapshots immutable. Separate external movement state from a
   calculated payable.
2. Build an idempotent close projection from settled payment/earning IDs.
   Unique source-line keys prevent an earning or refund entering twice;
   concurrent close and payout paths lock the same period. Reopening a closed
   period is prohibited; approved late items or errors create linked
   adjustment/correction lines in a later period.
3. Add scoped maker/checker commands for close, offset approval, payout
   instruction and independent evidence reconciliation. A command's unknown
   result is resolved by an authoritative read of its original reference;
   never issue a new payout to repair an observer failure.
4. Give drivers a read-only statement showing source rides, method, earned,
   cash due, operator payable, approved offsets, paid/remitted, withheld and
   outstanding amounts. Give finance a separate reconciliation/export view.
   Passenger receipts continue to show passenger payment and refund facts,
   not operator payout assumptions.
5. Test conservation across both fee-funding modes, scheduled beneficiary
   variants, cash/transfer/mixed periods, pending payments, refunds,
   reversals, simultaneous close, same-key replay, duplicate external
   references, different operators/cities, access denial and worker restart.
   Then exercise real low-value movements and independent reconciliation
   under the approved pilot authority.

The exact tables, API routes, roles and payout provider are **not yet approved**.
Do not migrate production or expose payout controls from this proposal alone.

## Approval and evidence record

Record in the existing [R1 decision queue](r1-decisions.md) and
[pilot approval/evidence artifacts](../real-world-launch.md), with:

```text
decision_ids: S01-S08
policy_version and effective_at:
city/operator/currency/payment methods:
operator finance authority and reviewer:
owner and independent accounting reviewer:
signed worked-case locations:
cash/transfer recipient and custody evidence locations:
period, clearing, refund, dispute and payout rules:
privacy/retention and access review locations:
pilot threshold and stop authority:
conditions, expiry, invalidation and next action:
```

Keep account identifiers, statements, real participant identities, signatures
and credentials in controlled records outside this public source document.
The implementation gate remains open until S01-S08 and applicable legal,
finance, security and pilot approvals are recorded and independently tested.
