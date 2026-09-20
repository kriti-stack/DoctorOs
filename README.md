# DoctorOs
Appointment booking system for doctors

## Production architecture foundation

This repository now includes a backend-first implementation foundation for a scalable doctor appointment platform:

- Multi-role model: **PATIENT**, **DOCTOR**, **ADMIN**
- Doctor profile + availability + breaks + leave support
- Slot generation from working windows and appointment duration
- Concurrency-safe booking flow with **slot hold** and hold expiry
- Payment-verified confirmation flow (backend verification required)
- Appointment lifecycle support (confirm, cancel, reschedule, complete/no-show)
- Access checks for patient medical documents and doctor authorization
- Notification event fan-out architecture (EMAIL, SMS, IN_APP)

## Database schema

Relational schema is defined in:

- `/home/runner/work/DoctorOs/DoctorOs/db/schema.sql`

Schema includes core entities and constraints:

- Users, Patients, Doctors, Specialties, Clinics
- DoctorClinic, DoctorAvailability, DoctorLeave
- AppointmentSlot, Appointment, Payment
- Prescription, MedicalDocument, Notification, AuditLog
- Unique constraints and indexes for fast lookup and duplicate booking prevention

## Run tests
```bash
python -m unittest discover -s tests
```

## Core API shape (reference)

- `POST /api/auth/login`
- `GET /api/doctors`
- `GET /api/doctors/{id}`
- `GET /api/doctors/{id}/availability`
- `GET /api/doctors/{id}/slots`
- `POST /api/appointments`
- `PUT /api/appointments/{id}/reschedule`
- `POST /api/appointments/{id}/cancel`
- `POST /api/payments`
- `POST /api/payments/webhook`
