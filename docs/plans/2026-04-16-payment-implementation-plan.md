# Payment Closure and Platform Alignment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Repair and complete the current appointment payment flow so paid bookings, payment retry, callback settlement, refund, admin operations, and payment-profile routing are all production-usable.

**Architecture:** Treat this as a payment-closure project, not a small bugfix batch. First lock the intended business contract in OpenSpec, then repair the booking/payment/refund closed loop, then align the admin and patient clients to the same response model, and finally harden the flow with idempotency, auth, observability, and rollout safeguards. Reuse the existing `PaymentProfile`, `PaymentRoute`, `PaymentService`, `RefundService`, and appointment payment snapshot fields instead of inventing a parallel payment system.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, PostgreSQL, Redis, Celery, React, Taro, TypeScript, pnpm monorepo, OpenSpec.

---

## Execution Status Snapshot (2026-04-17)

### Completed

- Unified `POST /appointments` response handling for free and paid bookings.
- Returned real `payment_params` for paid bookings and aligned patient miniapp request/response handling.
- Added payment and refund fields to appointment response models and synchronized shared/frontend types.
- Completed retry-payment flow fixes, including `openid` fallback from the current authenticated user.
- Standardized refund request field names and amount unit to yuan.
- Unified refund `out_trade_no` with payment order number format `APPT{appointment.id}`.
- Repaired refund aggregate synchronization for create / callback / failure paths and added callback idempotency.
- Hardened payment callback handling so duplicate success callbacks are idempotent and late success callbacks do not revive expired appointments.
- Fixed timeout cancellation to use conditional status updates and release `booked_slots` exactly once.
- Added regression coverage for payment retry, payment callback, refund callback, timeout race, and payment routing precedence.
- Added tenant-default payment profile fallback and fixed runtime precedence for explicit miniapp instance resolution.
- Finalized the compatibility strategy between `PaymentProfile/PaymentRoute` and legacy `stores.wechat_*` as a soft-deprecation path.
- Added payment/refund lifecycle documentation and a manual joint-debug checklist.

### Verified

- `pytest apps/server/tests/integration/test_appointments_payment_creation_endpoints.py -q`
- `pytest apps/server/tests/integration/test_appointments_router_endpoints.py -q`
- `pytest apps/server/tests/integration/test_payments_router_endpoints.py -q`
- `pytest apps/server/tests/unit/test_payment_refund.py -q`
- `pytest apps/server/tests/unit/test_payment_timeout.py -q`
- `pytest apps/server/tests/unit/test_miniapp_platform_resolvers.py -q`

### Remaining

- ~~Clarify the compatibility order between `PaymentProfile/PaymentRoute` and legacy `stores.wechat_*`.~~ **Done (2026-04-16): soft-deprecation strategy applied.**
  - Store model `wechat_*` columns marked `[DEPRECATED]`.
  - `WechatConfigResolver` store fallback emits `logger.warning("[DEPRECATION]")`.
  - `PaymentConfigResolver` confirmed never reads legacy store fields.
  - Store wechat-config API endpoints return `Deprecation: true` header.
  - Migration path documented: MiniappInstance + PaymentProfile + PaymentRoute.
- Finish payment/refund lifecycle docs and manual joint-debug checklist. **Done (2026-04-16):**
  - Lifecycle doc: `docs/server/payment-lifecycle.md`
  - Joint-debug checklist: `docs/plans/payment-joint-debug-checklist.md`
- No unresolved P0 payment-closure blockers remain in this plan snapshot.

---

## Why This Plan Exists

The repository already contains most payment building blocks:

- appointment payment status and snapshot fields
- payment profile and payment route models
- WeChat pay service wrapper
- payment callback endpoint
- refund record model and refund callback endpoint
- patient miniapp booking and retry-payment UI
- admin refund UI

But the current implementation is not a usable business-closed loop because key contracts are inconsistent:

- paid appointment creation returns a `dict`, while the router still treats the result as an `Appointment`
- patient booking UI expects `payment_params`, but the service returns payment config metadata instead
- payment retry requires `openid`, but the API client does not send it
- appointment response schemas do not expose payment fields needed by patient/admin UIs
- refund UI sends the wrong field names and wrong amount unit
- refund records store a different merchant order number than payment creation uses
- payment endpoints are missing proper auth and ownership checks
- callback, retry, status query, and refund paths are not covered by integration tests

This plan closes those gaps while keeping compatibility with the miniapp-platform payment routing design already described in OpenSpec.

## Scope

### In Scope

- patient paid booking flow
- patient retry payment flow
- payment callback settlement
- appointment payment field exposure in API responses
- admin refund initiation and refund history
- refund callback settlement
- payment endpoint auth and ownership rules
- payment/ refund idempotency and auditability
- integration and regression tests
- docs and rollout checklist

### Out of Scope

- new payment providers beyond current WeChat Pay path
- accounting reconciliation dashboards
- subscription billing / SaaS tenant billing
- a full payment ledger system
- large redesign of the miniapp platform admin console beyond what is required for payment closure

## Target Business Rules

### Booking and Payment

1. Free appointment:
   - consultation fee `<= 0`
   - create appointment
   - status becomes `CONFIRMED`
   - no payment order is created

2. Paid appointment:
   - consultation fee `> 0`
   - create appointment
   - status becomes `PENDING`
   - payment snapshot is frozen on the appointment
   - backend returns payment parameters usable by `Taro.requestPayment`

3. Payment success:
   - WeChat callback is verified
   - callback is processed idempotently
   - appointment status changes `PENDING -> CONFIRMED`
   - `payment_transaction_id`, `paid_at`, and raw settlement metadata are persisted

4. Payment failure or user cancel:
   - appointment remains `PENDING`
   - patient can retry payment within timeout window

5. Payment timeout:
   - scheduled task expires unpaid appointments
   - appointment status becomes `EXPIRED`
   - booked slot is released exactly once

### Refund

1. Only paid appointments can be refunded.
2. Refund amount uses yuan consistently in backend contracts.
3. Refund request must reference the original merchant order used when payment was created.
4. Refund creation is idempotent and auditable.
5. Refund callback updates both `RefundRecord` and appointment refund aggregate fields.
6. Partial and full refunds are supported.

### Security

1. Patient payment operations must require authenticated patient ownership.
2. Admin refund operations must require `appointment:refund`.
3. Payment status query must not expose arbitrary appointment payment state without authorization.
4. Callback endpoints remain unauthenticated, but must verify signature and process safely without tenant confusion.

## Canonical Data and Contract Decisions

### Decision 1: Appointment is the payment aggregate root

The appointment remains the primary business record for booking + payment state.

Use these existing fields as the canonical business snapshot:

- `payment_profile_id`
- `payment_miniapp_instance_id`
- `payment_mode`
- `payment_app_id`
- `payment_mch_id`
- `payment_sub_mchid`
- `payment_notify_url`
- `payment_amount`
- `payment_transaction_id`
- `paid_at`
- `refund_status`
- `refund_amount`

### Decision 2: Merchant order number format is `APPT{appointment.id}`

This already matches `PaymentService._generate_out_trade_no`.

All payment and refund flows must use the same merchant order number:

- payment create uses `APPT{appointment.id}`
- payment callback resolves by `APPT{appointment.id}`
- refund record stores this same value in `out_trade_no`
- refund API and refund callback use this same value

### Decision 3: Backend amount unit is yuan

The backend models use `Numeric(10,2)`, and the WeChat wrapper converts yuan to fen internally.

Therefore:

- API request/response contracts for refund and payment amount should use yuan on the backend side
- client display can convert for display needs
- shared frontend type names must match actual backend semantics

### Decision 4: Payment response contract must be explicit

The appointment creation path must support two valid response shapes:

1. Free booking response:
   - `appointment`
   - `payment_required = false`

2. Paid booking response:
   - `appointment`
   - `payment_required = true`
   - `payment_amount`
   - `payment_params`

`payment_params` must use the same field names expected by `Taro.requestPayment`:

- `timeStamp`
- `nonceStr`
- `package`
- `signType`
- `paySign`

## OpenSpec Change To Create First

Create a new change before implementation:

- Suggested change id: `fix-payment-closure-and-refund-flow`

Affected specs:

- `appointment`
- `payment-profile-routing`

Add or modify requirements for:

- paid booking response contract
- retry payment contract
- appointment payment field exposure
- payment endpoint auth rules
- refund contract and order-number consistency
- callback idempotency and timeout behavior

## Delivery Order

### Phase 0: Spec and contract alignment

### Task 0.1: Create OpenSpec change

**Files:**
- Create: `openspec/changes/fix-payment-closure-and-refund-flow/proposal.md`
- Create: `openspec/changes/fix-payment-closure-and-refund-flow/tasks.md`
- Create: `openspec/changes/fix-payment-closure-and-refund-flow/design.md`
- Create: `openspec/changes/fix-payment-closure-and-refund-flow/specs/appointment/spec.md`
- Create: `openspec/changes/fix-payment-closure-and-refund-flow/specs/payment-profile-routing/spec.md`

**Steps:**
1. Write proposal describing current broken payment closure.
2. Define final booking, retry payment, callback, and refund contracts.
3. Add scenarios for paid booking success, retry payment, payment callback idempotency, partial refund, full refund, and unauthorized payment access.
4. Validate the change with strict OpenSpec validation.

**Verification:**
- Approved spec exists before code changes start.

## Phase 1: Repair paid appointment creation

### Task 1.1: Introduce a dedicated appointment-create response schema

**Files:**
- Modify: `apps/server/app/schemas/appointment.py`
- Modify: `apps/server/app/modules/appointments/router.py`
- Modify: `packages/api/src/modules/appointment.ts`
- Test: `apps/server/tests/integration/test_appointments_router_endpoints.py`
- Test: `apps/server/tests/unit/test_payment_refund.py`

**Steps:**
1. Add a new Pydantic response model for create booking:
   - `appointment`
   - `payment_required`
   - `payment_amount`
   - `payment_params`
2. Change `POST /appointments` to return this new response model instead of plain `AppointmentResponse`.
3. Update the router so it handles both free and paid creation results safely without assuming ORM shape.
4. Keep WebSocket notification behavior only on the embedded `appointment` object.
5. Update package API typings to match the new contract exactly.

**Verification:**
- Free and paid appointment creation both return valid JSON and never crash in the router.
- Paid booking response contains nested `payment_params`.

### Task 1.2: Generate real payment params during booking create

**Files:**
- Modify: `apps/server/app/modules/appointments/service_booking.py`
- Modify: `apps/server/app/modules/payments/service.py`
- Test: `apps/server/tests/unit/test_payment_refund.py`
- Test: `apps/server/tests/integration/test_appointments_router_endpoints.py`

**Steps:**
1. Replace `_prepare_payment_params()` placeholder behavior.
2. Resolve payment config and snapshot it before returning payment parameters.
3. Require `openid` from authenticated patient context or explicitly pass it from the booking request flow.
4. Return WeChat-ready `payment_params` for paid bookings.
5. Ensure no duplicate payment order is created when the same booking request retries after server-side failure.

**Verification:**
- Paid booking create returns callable payment params.
- Free booking create remains unchanged.

## Phase 2: Repair patient retry-payment flow

### Task 2.1: Define one consistent `openid` source

**Files:**
- Modify: `apps/server/app/modules/appointments/router.py`
- Modify: `packages/api/src/modules/appointment.ts`
- Modify: `apps/patient-miniapp/src/pages/appointment/index.tsx`
- Modify: `apps/patient-miniapp/src/packageBooking/pages/appointment/detail.tsx`
- Review: auth/openid source in patient app state

**Decision:**
Prefer server-side lookup of patient openid from authenticated user profile instead of requiring the client to send `openid` on retry-payment.

**Steps:**
1. Remove `openid` as a required public query parameter from retry payment if the authenticated user already has a bound openid.
2. If the project cannot reliably load openid server-side yet, then update the API client and page to pass it explicitly from auth state.
3. Normalize `getPaymentParams()` typings to the real backend response.

**Verification:**
- A patient can re-initiate payment from the pending appointment page without 422/400 caused by missing `openid`.

### Task 2.2: Fix patient retry-payment UX

**Files:**
- Modify: `apps/patient-miniapp/src/pages/appointment/index.tsx`
- Modify: `apps/patient-miniapp/src/packageBooking/pages/booking/result.tsx`
- Modify: `packages/shared/src/types/appointment.ts`

**Steps:**
1. Ensure pending appointments actually carry the payment fields required by the list/detail pages.
2. Fix result-page retry navigation so it uses an identifier resolvable by the detail page.
3. Add success, failure, and cancel handling with clear patient messaging.

**Verification:**
- Pending appointment list and detail pages can both trigger payment retry successfully.

## Phase 3: Expose payment fields in appointment APIs

### Task 3.1: Extend appointment response schema

**Files:**
- Modify: `apps/server/app/schemas/appointment.py`
- Modify: `apps/server/app/modules/appointments/router_query.py`
- Modify: `packages/shared/src/types/appointment.ts`
- Modify: `apps/admin/src/pages/appointment/list.tsx`
- Modify: `apps/admin/src/pages/appointment/detail.tsx`
- Modify: `apps/patient-miniapp/src/pages/appointment/index.tsx`
- Test: `apps/server/tests/integration/test_appointments_router_endpoints.py`

**Steps:**
1. Add payment fields to `AppointmentResponse`:
   - `payment_amount`
   - `payment_time` or `paid_at`
   - `payment_transaction_id`
   - `refund_status`
   - `refunded_amount`
2. Decide on one API field naming scheme and keep the shared package aligned.
3. Ensure appointment list, detail, and export queries preload and serialize the same fields.

**Verification:**
- Admin and patient UIs can render payment/refund state from real backend data.

## Phase 4: Secure payment endpoints

### Task 4.1: Add auth and ownership guards to payment APIs

**Files:**
- Modify: `apps/server/app/modules/payments/router.py`
- Modify: `apps/server/app/modules/payments/service.py`
- Modify: `apps/server/app/api/deps.py` if helper reuse is needed
- Test: `apps/server/tests/integration/test_appointments_router_endpoints.py`
- Create/Test: `apps/server/tests/integration/test_payments_router_endpoints.py`

**Steps:**
1. Require authenticated patient on order creation and payment-status query.
2. Verify appointment ownership for patient operations.
3. Require authenticated admin plus `appointment:refund` for any direct admin refund operation.
4. Leave callback endpoints unauthenticated but isolated to signature verification only.

**Verification:**
- Unauthorized users cannot create payment orders, inspect payment state, or trigger refunds.

## Phase 5: Repair refund contract and settlement

### Task 5.1: Standardize refund API contract

**Files:**
- Modify: `apps/server/app/modules/refunds/schemas.py`
- Modify: `packages/api/src/modules/appointment.ts`
- Modify: `apps/admin/src/pages/appointment/detail.tsx`
- Test: `apps/server/tests/integration/test_refunds_router_endpoints.py`

**Steps:**
1. Decide whether package API converts camelCase to snake_case or sends snake_case directly.
2. Make admin refund submission use the exact backend contract.
3. Remove incorrect `* 100` conversion in admin refund request.
4. Align refund list response shape with admin page expectations.

**Verification:**
- Admin can submit a `30.00` yuan refund without validation mismatch or over-refund errors caused by unit confusion.

### Task 5.2: Store the correct merchant order number in refund records

**Files:**
- Modify: `apps/server/app/modules/refunds/service.py`
- Modify: `apps/server/app/modules/payments/service.py`
- Test: `apps/server/tests/unit/test_payment_refund.py`
- Test: `apps/server/tests/integration/test_refunds_router_endpoints.py`

**Steps:**
1. Replace refund record `out_trade_no=appointment.appointment_no` with the canonical merchant order number.
2. Add a shared helper so payment create and refund create derive the same value.
3. Backfill or define fallback behavior for historical rows created with the old value.

**Verification:**
- Refund query and refund create refer to the original WeChat merchant order consistently.

### Task 5.3: Complete refund state machine

**Files:**
- Modify: `apps/server/app/modules/refunds/service.py`
- Modify: `apps/server/app/modules/refunds/router.py`
- Modify: `apps/server/app/models/refund.py` only if extra fields are required
- Test: `apps/server/tests/unit/test_payment_refund.py`
- Test: `apps/server/tests/integration/test_refunds_router_endpoints.py`

**Steps:**
1. Keep `RefundRecord` and appointment refund aggregate fields in one consistent transaction.
2. On refund request:
   - create refund record
   - mark status `pending`
   - submit to WeChat
   - transition to `processing` when accepted
3. On callback:
   - mark `success` or `failed`
   - recompute appointment refund aggregate from successful refund records
4. Ensure repeated callbacks are idempotent.

**Verification:**
- Partial refund and full refund both update appointment aggregates correctly.
- Failed callbacks roll aggregates back safely.

## Phase 6: Harden payment callback and timeout behavior

### Task 6.1: Make payment callback idempotent and audit-friendly

**Files:**
- Modify: `apps/server/app/modules/payments/service.py`
- Modify: `apps/server/app/infrastructure/payments/wechat_pay_service.py`
- Consider Create: `apps/server/app/models/payment_event.py` only if raw event persistence is needed
- Test: `apps/server/tests/integration/test_payments_router_endpoints.py`

**Steps:**
1. Ensure repeated `TRANSACTION.SUCCESS` callbacks do not double-settle.
2. Persist or log enough callback metadata for debugging.
3. Validate callback resolution without relying on tenant context presence.
4. If needed, lock appointment rows during settlement to avoid races with timeout jobs.

**Verification:**
- Duplicate payment callback processes safely.
- One payment success cannot settle the same appointment twice.

### Task 6.2: Review unpaid-expiration logic

**Files:**
- Modify: `apps/server/app/tasks/payment_task.py`
- Modify: related appointment service helpers if needed
- Test: `apps/server/tests/unit/test_payment_timeout.py` (new)

**Steps:**
1. Verify booked slot release uses the correct field (`booked_slots` vs `booked_count`) for current schema.
2. Ensure timeout job does not expire already-paid appointments due to callback races.
3. Add test coverage for timeout + late callback interaction.

**Verification:**
- Expiration releases slots once.
- Late but duplicate events do not corrupt appointment status.

## Phase 7: Align miniapp-platform payment routing with runtime usage

### Task 7.1: Formalize routing precedence in runtime code

**Files:**
- Modify: `apps/server/app/infrastructure/payments/config_resolver.py`
- Modify: `apps/server/app/modules/payments/service.py`
- Modify: `apps/server/app/modules/appointments/service_booking.py`
- Test: `apps/server/tests/unit/test_payment_config_resolver.py` (new)

**Routing order to enforce:**
1. appointment snapshot
2. explicit miniapp instance
3. appointment-linked miniapp instance
4. store payment route
5. miniapp default payment profile
6. tenant default payment profile

**Verification:**
- Runtime resolution matches spec and works for store-specific overrides and instance defaults.

### Task 7.2: Bridge legacy store WeChat config safely

**Files:**
- Modify: `apps/server/app/infrastructure/payments/config_resolver.py`
- Modify: `apps/server/app/modules/stores/router.py` or migration docs only if needed
- Doc: migration note under `docs/server/` or `docs/plans/`

**Steps:**
1. Decide whether legacy `stores.wechat_*` remains fallback-only during transition.
2. If fallback is kept, mark it compatibility-only and log when used.
3. Define a migration path from legacy store config to `PaymentProfile`.

**Verification:**
- New runtime prefers `PaymentProfile` and `PaymentRoute`.
- Legacy fields are not the silent long-term source of truth.

## Phase 8: Testing matrix

### Required Unit Tests

**Files:**
- Extend: `apps/server/tests/unit/test_payment_refund.py`
- Create: `apps/server/tests/unit/test_payment_config_resolver.py`
- Create: `apps/server/tests/unit/test_payment_timeout.py`

**Cases:**
- paid booking returns pending status + payment params
- free booking returns confirmed status
- refund uses canonical out_trade_no
- refund amount validation uses yuan correctly
- payment config resolution precedence
- duplicate callback idempotency
- timeout task does not expire already-settled appointment

### Required Integration Tests

**Files:**
- Extend: `apps/server/tests/integration/test_appointments_router_endpoints.py`
- Create: `apps/server/tests/integration/test_payments_router_endpoints.py`
- Create: `apps/server/tests/integration/test_refunds_router_endpoints.py`

**Cases:**
- create paid appointment
- create free appointment
- patient retry payment
- unauthorized user cannot retry someone else's payment
- payment callback settles pending appointment
- duplicate payment callback is safe
- admin refund submission succeeds
- refund callback updates refund record and appointment aggregates

### Optional E2E / Manual Validation

**Manual checklist:**
- patient creates a paid booking in miniapp
- WeChat payment success returns to booking result page
- patient sees confirmed appointment with payment info
- patient cancels payment and later retries from my appointments
- admin sees payment info on appointment detail
- admin submits partial refund
- callback updates refunded amount and refund status

## Phase 9: Docs and observability

### Task 9.1: Update docs

**Files:**
- Modify: `docs/modules/appointment.md`
- Modify: `docs/api/README.md`
- Modify: payment-related deployment/config docs under `docs/server/`
- Modify: `.env.example` or server config docs if callback/payment config env vars need clarification

**Docs to add:**
- payment lifecycle
- refund lifecycle
- backend amount-unit convention
- callback troubleshooting
- migration note for legacy store WeChat config

### Task 9.2: Add operational logging

**Files:**
- Modify: `apps/server/app/modules/payments/service.py`
- Modify: `apps/server/app/modules/refunds/service.py`
- Modify: `apps/server/app/core/logging.py` only if structure changes are needed

**Events to log:**
- payment order create requested
- payment order create succeeded
- payment callback accepted
- payment callback duplicate
- refund create requested
- refund create accepted by WeChat
- refund callback accepted
- timeout expiry executed

## Rollout Strategy

### Stage A: Contract-safe backend first

Ship first behind backend compatibility:

- create-appointment response fix
- appointment response payment fields
- auth hardening
- refund contract fix
- canonical out_trade_no fix

### Stage B: Client alignment

Then ship:

- patient retry-payment fix
- patient result-page fix
- admin refund submission fix

### Stage C: Payment callback and timeout hardening

Then ship:

- idempotency improvements
- race-condition protections
- operational logging

### Stage D: Routing and migration cleanup

Then ship:

- runtime routing precedence polish
- legacy store-config fallback policy

## Suggested Commit Sequence

1. `spec: add payment closure openspec change`
2. `fix: normalize appointment create payment response`
3. `fix: generate real payment params for paid bookings`
4. `fix: expose payment fields on appointment responses`
5. `fix: secure payment endpoints and retry flow`
6. `fix: standardize refund request contract`
7. `fix: use canonical merchant order number for refunds`
8. `test: add payment callback and refund integration coverage`
9. `docs: document payment and refund lifecycle`

## Exit Criteria

The payment project is complete when all of the following are true:

1. Paid bookings can be created and paid successfully from the patient miniapp.
2. Payment success settles the appointment to `CONFIRMED`.
3. Payment cancellation or failure leaves the appointment in retryable `PENDING`.
4. Payment retry works from patient appointment pages without missing-openid failures.
5. Appointment APIs expose correct payment and refund state for patient/admin UIs.
6. Admin can submit partial and full refunds with correct yuan semantics.
7. Refund processing uses the original merchant order number consistently.
8. Payment/refund endpoints enforce auth and ownership correctly.
9. Duplicate callbacks and timeout races do not corrupt state.
10. Unit and integration tests cover the closed loop.

## Recommended Next Step

Before any implementation, turn this plan into an approved OpenSpec change and keep the first coding slice intentionally small:

1. payment create-response contract
2. retry-payment contract
3. refund request contract
4. payment field exposure on appointment responses
