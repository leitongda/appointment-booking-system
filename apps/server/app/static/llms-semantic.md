# Hospital Booking System - API Semantic Description

> This document provides semantic descriptions of the Hospital Booking System API, including business context, usage patterns, and endpoint relationships.

## System Overview

The Hospital Booking System is a multi-tenant SaaS platform for hospital appointment scheduling. It supports multiple stores, departments, and doctors with flexible scheduling.

### Core Business Entities

| Entity | Description | Key Relationships |
|--------|-------------|-------------------|
| **Tenant** | Organization/Hospital | Has multiple stores |
| **Store** | Physical location/Branch | Has departments, doctors |
| **Department** | Medical department | Belongs to stores, has doctors |
| **Doctor** | Medical professional | Belongs to department, has schedules |
| **Patient** | End user | Books appointments, has medical cards |
| **Appointment** | Booking record | Links patient, doctor, schedule |
| **Schedule** | Time slot availability | Defines doctor availability |

### Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Authentication Methods                     │
├─────────────────────────────────────────────────────────────┤
│  1. Phone + SMS Code  ──→  /auth/login                      │
│  2. Phone + Password  ──→  /auth/login                      │
│  3. WeChat Mini Program ──→  /auth/wechat/login              │
│  4. WeChat + Phone Bind ──→  /auth/wechat/bind-phone        │
└─────────────────────────────────────────────────────────────┘
```

## Business Workflows

### 1. Appointment Booking Workflow

**Business Goal:** Patient books an appointment with a doctor

**Semantic Steps:**
1. **Discovery** - Patient browses available departments and doctors
2. **Selection** - Patient selects a doctor and views available time slots
3. **Booking** - Patient creates an appointment
4. **Confirmation** - System confirms booking and sends notification

**API Sequence:**
```
GET  /departments/tree          → Get department hierarchy
GET  /doctors/by-department/{id} → List doctors in department
GET  /doctors/public/{id}        → View doctor details
GET  /schedules/available/{id}   → Get available time slots
GET  /booking-notices/public     → View booking policies
POST /appointments               → Create appointment
```

**Key Business Rules:**
- Duplicate booking check (same patient, same doctor, same time)
- Booking notice acknowledgment required
- Schedule availability validation

### 2. Patient Check-in Workflow

**Business Goal:** Patient checks in at the hospital/store

**Semantic Steps:**
1. **Arrival** - Patient arrives at store
2. **Identification** - Patient scans QR code or provides appointment number
3. **Check-in** - System records patient arrival
4. **Queue** - Patient joins the waiting queue

**API Sequence:**
```
GET  /stores/{id}/checkin-qrcode     → Get QR code for store
GET  /appointments/today-pending      → List today's appointments
GET  /appointments/by-no/{no}         → Find appointment by number
PUT  /appointments/{id}/sign-in       → Check in
GET  /appointments/queue              → View queue status
```

### 3. Doctor Calling Workflow

**Business Goal:** Doctor calls patients for consultation

**Semantic Steps:**
1. **Queue View** - Doctor sees waiting patients
2. **Calling** - Doctor calls next patient
3. **Consultation** - Patient visits doctor
4. **Completion** - Doctor marks visit complete

**API Sequence:**
```
GET  /doctor-portal/queue              → Get waiting queue
GET  /doctor-portal/queue/info         → Get queue statistics
PUT  /appointments/{id}/call           → Call patient
PUT  /appointments/{id}/complete       → Complete visit
PUT  /appointments/{id}/pass           → Mark as passed
PUT  /appointments/{id}/recall         → Recall patient
```

### 4. Schedule Management Workflow

**Business Goal:** Admin manages doctor schedules

**Semantic Steps:**
1. **Template Creation** - Create schedule templates
2. **Schedule Generation** - Generate schedules from templates
3. **Adjustment** - Modify individual schedules
4. **Suspension** - Handle doctor unavailability

**API Sequence:**
```
GET  /shift-types                      → Get shift type definitions
POST /schedule-templates               → Create template
POST /schedule-templates/generate      → Generate schedules
GET  /schedules                        → List schedules
POST /schedules/batch-suspend          → Batch suspend
POST /schedule-suspensions             → Create suspension
```

## Endpoint Categories by Business Domain

### User Management Domain

**Purpose:** User authentication, profile management, patient management

**Key Endpoints:**
- `/auth/*` - Authentication (login, register, WeChat integration)
- `/users/*` - User profile management
- `/users/patients/*` - Patient (family member) management

**Business Context:**
- Supports multiple authentication methods for different user types
- Patients can manage family members (for elderly/children)
- Medical card integration for hospital systems

### Medical Resources Domain

**Purpose:** Manage doctors, departments, stores, and consultation fees

**Key Endpoints:**
- `/doctors/*` - Doctor CRUD and public queries
- `/departments/*` - Department hierarchy management
- `/stores/*` - Store/branch management
- `/consultation-fees/*` - Fee configuration

**Business Context:**
- Multi-store architecture supports hospital chains
- Department hierarchy enables flexible organization
- Public endpoints for patient-facing queries

### Booking Domain

**Purpose:** Core appointment and scheduling functionality

**Key Endpoints:**
- `/appointments/*` - Appointment lifecycle management
- `/schedules/*` - Schedule CRUD and queries
- `/schedule-templates/*` - Template-based scheduling
- `/shift-types/*` - Shift type definitions

**Business Context:**
- Template-based scheduling reduces admin workload
- Batch operations for efficient management
- Rule-based booking constraints

### Clinical Service Domain

**Purpose:** Clinical operations and doctor portal

**Key Endpoints:**
- `/doctor-portal/*` - Doctor-specific operations
- `/medical-records/*` - Patient medical records
- `/appointments/{id}/call|complete|pass` - Queue management

**Business Context:**
- Doctor portal for queue management
- Medical records integration
- Real-time queue status updates

### Content & Notification Domain

**Purpose:** Content management and user notifications

**Key Endpoints:**
- `/news/*` - News articles
- `/notices/*` - System notices
- `/banners/*` - Banner management
- `/messages/*` - User messages

**Business Context:**
- Multi-channel notification support
- Content scheduling and publishing
- User feedback collection

### Analytics Domain

**Purpose:** Business intelligence and reporting

**Key Endpoints:**
- `/statistics/appointments` - Appointment statistics
- `/statistics/revenue` - Revenue analysis
- `/statistics/departments` - Department performance
- `/statistics/doctors` - Doctor performance

**Business Context:**
- Real-time dashboard data
- Trend analysis and forecasting
- Performance benchmarking

### System Management Domain

**Purpose:** System configuration and administration

**Key Endpoints:**
- `/permissions/*` - Permission management
- `/roles/*` - Role-based access control
- `/settings/*` - System settings
- `/audit-logs/*` - Audit trail

**Business Context:**
- Multi-tenant configuration
- Fine-grained permission control
- Compliance and audit support

## Data Flow Patterns

### Appointment Creation Flow

```
Patient App                    Backend                     Database
    │                            │                            │
    ├─ GET /schedules/available ─►│                            │
    │                            ├─ Query available slots ────►│
    │                            │◄── Return slots ───────────┤
    │◄── Return available times ─┤                            │
    │                            │                            │
    ├─ POST /appointments ──────►│                            │
    │                            ├─ Validate business rules ──►│
    │                            ├─ Create appointment ───────►│
    │                            │◄── Return appointment ──────┤
    │◄── Return confirmation ────┤                            │
```

### Real-time Queue Update Flow

```
Doctor Portal                  Backend                     WebSocket
    │                            │                            │
    ├─ GET /queue ──────────────►│                            │
    │                            ├─ Subscribe to queue ───────►│
    │◄── Return queue ───────────┤                            │
    │                            │                            │
    │                            │◄── Patient check-in event ─┤
    │◄── Queue update push ──────┤                            │
    │                            │                            │
    ├─ PUT /call ───────────────►│                            │
    │                            ├─ Update queue status ──────►│
    │                            ├─ Broadcast update ─────────►│
    │◄── Confirmation ───────────┤                            │
```

## Error Handling Patterns

### Common Error Responses

| Code | Meaning | Typical Cause |
|------|---------|---------------|
| 0 | Success | Operation completed |
| 400 | Bad Request | Invalid parameters |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate booking |
| 422 | Validation Error | Business rule violation |
| 500 | Server Error | Internal error |

### Business Error Codes

| Code | Meaning | Recovery Action |
|------|---------|-----------------|
| 1001 | Schedule not available | Select different time |
| 1002 | Duplicate appointment | Cancel existing first |
| 1003 | Booking limit reached | Wait for next period |
| 1004 | Doctor unavailable | Select different doctor |

## Integration Points

### WeChat Mini Program Integration

- Login via WeChat OAuth
- Phone number binding
- Template message notifications
- Payment integration (future)

### Hospital HIS Integration

- Patient data synchronization
- Medical record exchange
- Queue status updates

### Payment Gateway Integration

- Online payment for appointments
- Refund processing
- Payment status tracking
