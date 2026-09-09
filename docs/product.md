# TaxiMobile — Product Specification

## Current standing — 2026-09-02

The repository implements the broad provider-independent passenger, driver,
operations, fixed-route, scheduling, payment-record, safety/support, and national
city-control foundations specified here. That implementation has not established
product-market fit, cooperative adoption, legal authority in any city, service
quality with a real driver cohort, or readiness for public deployment. Those are
evidence gates, not software features. See [`gaps.md`](gaps.md) for audited launch
blockers and [`roadmap.md`](roadmap.md) for source versus deployment status.

## 1. Overview

TaxiMobile is a cooperative digital platform designed to allow licensed taxi drivers to collectively provide a modern ride-hailing service without depending on or being displaced by large private ride-hailing companies. Its approved growth target is a Morocco-wide network introduced through independently governed city deployments rather than one undifferentiated national launch.

The platform is intended to provide passengers with the convenience associated with applications such as Uber and Lyft while preserving the economic position and independence of traditional taxi drivers.

The central principle is:

> Technology should strengthen the taxi industry rather than replace it.

TaxiMobile is therefore not intended to create a new class of gig workers competing against taxi drivers. Its primary supply of rides comes from participating licensed taxi drivers.

---

## 2. Cooperative Model

TaxiMobile is designed around a cooperative model.

Participating taxi drivers should collectively have meaningful control over the platform rather than functioning solely as contractors supplying a private technology company.

The platform should therefore be designed so that:

* Taxi drivers are the primary service providers.
* Drivers retain their existing professional status and licenses.
* The platform does not encourage drivers to compete against each other through artificially low prices.
* Platform fees should be transparent.
* The economic interests of participating drivers should be prioritized.
* Major changes to the platform should eventually be subject to cooperative governance.
* The platform should avoid extracting excessive value from each completed ride.
* Driver data should not be treated as a commodity.
* The platform should not intentionally create dependency on the platform without corresponding benefits to participating drivers.

The exact legal structure of the cooperative will be determined separately and is outside the initial software specification.

---

## 3. Problem

Traditional taxi services have several disadvantages when compared with modern ride-hailing applications:

* Passengers may have difficulty finding an available taxi.
* Passengers may not know when a taxi will arrive.
* Dispatching can be inefficient.
* There may be limited information about the vehicle or driver before pickup.
* Payment options may be inconvenient.
* Drivers may have difficulty finding passengers efficiently.
* Existing taxi infrastructure may lack modern digital tools.

At the same time, conventional ride-hailing platforms can create problems for taxi drivers and the broader transportation ecosystem:

* Drivers may be subjected to platform commissions.
* Drivers may become economically dependent on a private platform.
* Dynamic pricing can create uncertainty.
* Large platforms can compete directly with regulated taxi services.
* Platform ownership and decision-making are concentrated.
* Driver data and customer relationships may be controlled by the platform.

TaxiMobile attempts to address the first group of problems without reproducing the second.

---

## 4. Primary Users

TaxiMobile has four primary categories of users.

### 4.1 Passengers

Passengers use the application to:

* Request service from the participating taxi network without browsing online taxis.
* Request rides.
* Browse published fixed routes, directions, start/finish points, and flat fares even when no taxi is currently online.
* Request immediate rides or schedule future rides where the selected city enables them.
* Specify pickup and destination locations.
* See relevant ride information.
* Track an approaching taxi.
* Communicate with the driver when necessary.
* Pay for rides through supported payment methods.
* View previous rides.
* Rate or provide feedback on rides.

### 4.2 Taxi Drivers

Taxi drivers use the application to:

* Register as participating drivers.
* Apply for authorization in one or more recruiting cities.
* Verify their professional credentials.
* Indicate when they are available.
* Receive ride requests.
* Receive ordinary, fixed-route, and scheduled offers with the information needed to choose.
* Accept or decline requests according to platform rules.
* Navigate to passengers.
* Manage active rides.
* Record completed rides.
* Receive payment.
* View earnings and ride history.

### 4.3 Cooperative and City Administration

The cooperative administration uses administrative tools to:

* Verify drivers.
* Manage participating vehicles.
* Manage accounts.
* Resolve disputes.
* Monitor platform operation.
* Manage cooperative policies.
* Review platform statistics.
* Configure and gradually activate city services.
* Publish directional fixed routes and their flat fares.
* Configure city tariffs, scheduling surcharges, and transparent operator fees.
* Review city-scoped driver applications and operational readiness.
* Handle security and moderation issues.

Administrative authority should be limited according to clearly defined cooperative governance rules.

### 4.4 National Platform Operations

National platform operators use a protected web console to coordinate the city
rollout, assign scoped operator/city authority, review aggregate network health,
and audit sensitive changes. National access is not an excuse for unrestricted
routine access to passenger identities, driver documents, exact locations, or
another city's private operational records. `operations.md` defines this control
plane and its scope model.

---

## 5. Core Product Principle

TaxiMobile should not attempt to win against existing ride-hailing services by turning taxis into another version of Uber.

The platform should instead make the existing taxi service more accessible and efficient through technology.

The application should therefore prioritize:

1. Reliable taxi availability.
2. Fair treatment of drivers.
3. Transparent pricing.
4. Low and transparent platform costs.
5. Driver ownership or meaningful cooperative participation.
6. Passenger safety.
7. Privacy.
8. Accessibility.
9. Efficient dispatching.
10. Long-term sustainability.

---

## 6. Initial Ride Model

A passenger creates a ride request by providing:

* Pickup location.
* Destination.
* Optional additional information.

The platform identifies eligible nearby participating taxis.

Eligible drivers may receive the request and accept it.

Once a driver accepts:

```text
Passenger
    ↓
Ride Request
    ↓
Dispatch System
    ↓
Eligible Drivers
    ↓
Driver Accepts
    ↓
Driver Travels to Pickup
    ↓
Passenger Pickup
    ↓
Ride in Progress
    ↓
Passenger Arrives
    ↓
Ride Completed
    ↓
Payment
    ↓
Receipt / Ride History
```

The exact dispatch algorithm will be defined separately in `rides.md`.

### 6.1 Passenger supply privacy

Passenger discovery is service-first, not driver-surveillance-first. Before a
driver accepts a request, the passenger must not see online taxi markers,
available-driver counts, identities, candidate rankings, or live supply
heatmaps. The passenger sees the service catalog, fare, published fixed routes,
and honest request status. Existing limited assigned-driver identity and
post-assignment location rules begin only after backend-confirmed acceptance.

### 6.2 Fixed-route service

Each city may publish versioned directional taxi routes. A published direction
has a start, finish, optional ordered stops, static route geometry, and flat
transport fare. Outbound and inbound are explicit directions. Published routes
remain discoverable when no driver is online; visibility never promises that a
driver is currently available. A passenger request still becomes an offer that
an eligible driver may accept or decline.

### 6.3 Scheduled service

Cities may enable future pickup reservations with explicit booking horizons,
driver-offer windows, cancellation rules, and a visible scheduling surcharge.
Scheduling a request does not promise a driver. The passenger sees whether the
request was received, a driver committed, dispatch is approaching, or the
booking could not be fulfilled. Future reservations remain separate from the
live ride state until dispatch handoff.

---

## 7. Pricing Philosophy

TaxiMobile should not initially attempt to reproduce the pricing model of private ride-hailing companies.

The platform should prioritize:

* Transparency.
* Compliance with applicable taxi regulations.
* Predictability for passengers.
* Fair compensation for drivers.
* Sustainable cooperative operation.

Where taxi fares are regulated by local authorities, the application should represent those rules rather than attempting to bypass them.

The software should keep pricing logic separate from the user interface so that applicable pricing rules can be changed without rebuilding the entire application.

---

## 8. Driver Participation

A driver should not be able to participate simply by downloading the application.

The platform should support a verification process appropriate for the jurisdiction in which it operates.

Potentially required information may include:

* Identity information.
* Taxi license information.
* Driver credentials.
* Vehicle information.
* Required professional documentation.
* Contact information.
* Payment information.

The exact documents and verification process will depend on the jurisdiction.

Sensitive documents should be protected and should not be unnecessarily exposed to other users.

---

## 9. Passenger Safety

Safety is a core product requirement.

The platform should provide appropriate mechanisms for:

* Driver identification.
* Vehicle identification.
* Ride tracking.
* Ride history.
* Clear direction to local emergency services without claiming platform dispatch.
* Reporting problems.
* Dispute handling.
* Account security.

The launch implementation provides ride-bound safety reports, separate
restricted review, and participant-safe acknowledgements/status. It is not an
emergency service, does not place calls or dispatch help, and must say so. Any
future direct emergency, trip-sharing, or evidence-upload integration requires a
jurisdiction-specific legal, privacy, reliability, and operational decision.

---

## 10. Driver Privacy

Driver privacy is a fundamental design requirement.

The platform should collect only information necessary to operate the service.

Examples of information that should not be unnecessarily exposed to passengers include:

* Personal addresses.
* Private contact information.
* Internal cooperative information.
* Unnecessary financial information.

Location information should only be exposed when necessary for the operation of a ride or another legitimate platform function.

---

## 11. Passenger Privacy

Passenger data should similarly be minimized.

The platform should not sell passenger location histories or personal information.

Location information should be retained only for as long as necessary for legitimate operational, legal, safety, or accounting purposes.

Specific retention periods will be defined later.

---

## 12. Cooperative Data Ownership

The long-term objective is for the cooperative and its participating drivers to retain meaningful control over operational data.

The platform should avoid creating unnecessary dependence on proprietary infrastructure.

Where practical:

* Data formats should be documented.
* APIs should be documented.
* Database structures should be understandable.
* Important operational data should be exportable.
* The cooperative should retain control over its own data.

Technical implementation should support the cooperative model rather than creating a technological lock-in.

---

## 13. Platform Revenue

The platform should not be designed around maximizing extraction from each ride.

Potential sources of sustainable revenue may include:

* A small transparent fee per ride.
* Cooperative membership fees.
* Institutional partnerships.
* Optional paid services.
* Cooperative investment.
* Other collectively approved revenue mechanisms.

The approved configuration model supports an explicit operator service fee as
either a bounded percentage of a documented transport-fare subtotal or a flat
amount per completed booking. City policy also determines whether that amount is
deducted transparently from settlement or added as a separate passenger-visible
service fee. Scheduled service may have a separately displayed scheduling
surcharge. Zero-fee policies are explicit rather than implied.

Every policy is city/operator scoped, versioned, effective-dated, auditable, and
snapshotted on the booking and financial records. The software must not hard-code
one commission, combine separate fees into an unexplained deduction, or calculate
a percentage from undefined “profit.”

---

## 14. Initial Geographic Scope

The first implementation and national expansion should be designed for Morocco.

However, geographic assumptions should not be unnecessarily hard-coded into the application.

Deployment proceeds one city at a time through `DRAFT`, `CONFIGURING`, `PILOT`,
and `ACTIVE` states. Each city owns versioned service boundaries, operator
assignments, driver requirements, pricing, fixed routes, scheduling policy,
matching configuration, support ownership, and rollout evidence. The
architecture should also permit later expansion to other jurisdictions with
different:

* Taxi regulations.
* Fare structures.
* Languages.
* Currencies.
* Payment systems.
* Licensing requirements.

The first deployment should nevertheless prioritize the requirements of the initial Moroccan operating environment.

---

## 15. Languages

The initial application should be designed with multilingual support in mind.

The initial target languages are:

* Arabic.
* French.
* English.

Localization should be implemented separately from application logic so that additional languages can be added later.

---

## 16. Platform

The passenger and driver applications will initially target:

* Android.
* iOS.

The mobile application will use:

* Kotlin.
* Kotlin Multiplatform.
* Compose Multiplatform.

Shared application logic should be maximized where practical.

Platform-specific functionality should remain isolated in platform-specific source sets.

---

## 17. Backend

The initial backend is a Python 3.12+ FastAPI modular monolith backed by PostgreSQL with PostGIS. SQLAlchemy, asyncpg, and Alembic provide database access and migration control.

The first real-time path is authenticated WebSockets for connected applications and push notifications for background devices. Ride and notification delivery uses a transactional outbox once ride offers are implemented. Redis, a separate task queue, and additional distributed services are deferred until measured scale requires them; they never replace PostgreSQL as the source of truth.

The detailed repository structure, mobile role split, and deployment approach are defined in `implementation.md`.

---

## 18. Non-Goals

TaxiMobile is not initially intended to:

* Replace taxi licensing systems.
* Become a general-purpose gig-work platform.
* Allow unrestricted private drivers to compete with licensed taxis.
* Create artificial surge pricing solely to maximize platform revenue.
* Sell driver or passenger location data.
* Become dependent on a single proprietary technology provider.
* Build every possible transportation service from the beginning.
* Replicate every feature of Uber or Lyft.
* Expose online taxis, driver counts, or candidate locations to passengers before assignment.

The first version should focus on providing a reliable digital dispatch and ride-management system for participating taxi drivers.

---

## 19. Guiding Principle

The success of TaxiMobile should not be measured solely by the number of rides processed.

A successful platform should simultaneously improve:

* Passenger convenience.
* Driver income stability.
* Driver autonomy.
* Taxi utilization.
* Service reliability.
* Cooperative ownership.
* Transparency.
* Safety.

The platform exists to provide technological infrastructure for a cooperative taxi service, not to make taxi drivers dependent on another intermediary.
