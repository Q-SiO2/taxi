# TaxiMobile documentation map

These documents are the product and architecture authority for the project.
Read the smallest set relevant to the current task. `implementation.md` turns
the product decisions into the repository, mobile, backend, and infrastructure
plan; it does not replace the domain documents.

| Area | Document |
| --- | --- |
| Product mission and scope | `product.md` |
| System boundaries and source of truth | `architecture.md` |
| Concrete build structure and delivery gates | `implementation.md` |
| Delivery order and non-MVP features | `roadmap.md` |
| User interaction constraints | `design.md` |
| Visual identity, motion, and UI plan | `ui.md` |
| Complete screen, component, input, and fallback specification | `extended_ui.md` |
| HTTP contract | `api.md` |
| Identity and permissions | `auth.md` |
| Persistent data model | `database.md` |
| Driver eligibility and participation | `drivers.md` |
| Ride lifecycle | `rides.md` |
| Matching and fairness | `matching.md` |
| Tariffs and fare records | `pricing.md` |
| Payment records and settlement | `payments.md` |
| Security baseline | `security.md` |

## Reading order for a new implementation slice

1. `roadmap.md` and `implementation.md` to confirm the slice and its delivery
   gate.
2. `architecture.md` to identify ownership and boundaries.
3. The relevant domain document (`auth`, `drivers`, `rides`, `matching`,
   `pricing`, or `payments`).
4. `api.md` and `database.md` for external and persistent contracts.
5. `security.md` and `design.md` when the slice touches data or UI.
6. `ui.md` and the relevant section of `extended_ui.md` when the slice changes visual identity, layout chrome, motion, screens, inputs, assets, or shared UI components.
