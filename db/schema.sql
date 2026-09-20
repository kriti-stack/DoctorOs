-- PostgreSQL schema for DoctorOs appointment booking platform.

CREATE TABLE app_user (
    id BIGSERIAL PRIMARY KEY,
    role VARCHAR(20) NOT NULL CHECK (role IN ('PATIENT', 'DOCTOR', 'ADMIN')),
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(255) UNIQUE,
    mobile VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE patient (
    user_id BIGINT PRIMARY KEY REFERENCES app_user(id),
    date_of_birth DATE,
    gender VARCHAR(20),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE specialty (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE clinic (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    location VARCHAR(255) NOT NULL,
    timezone VARCHAR(64) NOT NULL DEFAULT 'UTC',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE doctor (
    user_id BIGINT PRIMARY KEY REFERENCES app_user(id),
    specialty_id BIGINT NOT NULL REFERENCES specialty(id),
    qualification TEXT,
    experience_years INTEGER NOT NULL DEFAULT 0 CHECK (experience_years >= 0),
    consultation_fee NUMERIC(12,2) NOT NULL CHECK (consultation_fee >= 0),
    manual_confirmation_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE doctor_clinic (
    id BIGSERIAL PRIMARY KEY,
    doctor_user_id BIGINT NOT NULL REFERENCES doctor(user_id),
    clinic_id BIGINT NOT NULL REFERENCES clinic(id),
    is_online_available BOOLEAN NOT NULL DEFAULT TRUE,
    is_offline_available BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (doctor_user_id, clinic_id)
);

CREATE TABLE doctor_availability (
    id BIGSERIAL PRIMARY KEY,
    doctor_user_id BIGINT NOT NULL REFERENCES doctor(user_id),
    clinic_id BIGINT REFERENCES clinic(id),
    day_of_week SMALLINT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    appointment_duration_minutes SMALLINT NOT NULL CHECK (appointment_duration_minutes IN (15, 30, 45, 60)),
    consultation_type VARCHAR(20) NOT NULL CHECK (consultation_type IN ('ONLINE', 'OFFLINE')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (start_time < end_time)
);

CREATE TABLE doctor_leave (
    id BIGSERIAL PRIMARY KEY,
    doctor_user_id BIGINT NOT NULL REFERENCES doctor(user_id),
    leave_start TIMESTAMPTZ NOT NULL,
    leave_end TIMESTAMPTZ NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (leave_start < leave_end)
);

CREATE TABLE appointment_slot (
    id BIGSERIAL PRIMARY KEY,
    doctor_user_id BIGINT NOT NULL REFERENCES doctor(user_id),
    clinic_id BIGINT REFERENCES clinic(id),
    slot_start TIMESTAMPTZ NOT NULL,
    slot_end TIMESTAMPTZ NOT NULL,
    consultation_type VARCHAR(20) NOT NULL CHECK (consultation_type IN ('ONLINE', 'OFFLINE')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('AVAILABLE', 'HOLD', 'BOOKED')),
    hold_until TIMESTAMPTZ,
    hold_by_user_id BIGINT REFERENCES patient(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CHECK (slot_start < slot_end),
    UNIQUE (doctor_user_id, slot_start, slot_end, consultation_type)
);

CREATE TABLE appointment (
    id BIGSERIAL PRIMARY KEY,
    appointment_number VARCHAR(40) NOT NULL UNIQUE,
    slot_id BIGINT NOT NULL REFERENCES appointment_slot(id),
    patient_user_id BIGINT NOT NULL REFERENCES patient(user_id),
    doctor_user_id BIGINT NOT NULL REFERENCES doctor(user_id),
    clinic_id BIGINT REFERENCES clinic(id),
    appointment_status VARCHAR(20) NOT NULL CHECK (
        appointment_status IN (
            'BOOKED', 'CONFIRMED', 'COMPLETED', 'CANCELLED', 'NO_SHOW', 'RESCHEDULED'
        )
    ),
    payment_status VARCHAR(20) NOT NULL CHECK (
        payment_status IN ('PENDING', 'SUCCESS', 'FAILED', 'REFUNDED', 'PARTIAL_REFUND')
    ),
    consultation_fee NUMERIC(12,2) NOT NULL CHECK (consultation_fee >= 0),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE payment (
    id BIGSERIAL PRIMARY KEY,
    appointment_id BIGINT NOT NULL REFERENCES appointment(id),
    provider VARCHAR(50) NOT NULL,
    payment_reference VARCHAR(120) NOT NULL UNIQUE,
    amount NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
    status VARCHAR(20) NOT NULL CHECK (
        status IN ('PENDING', 'SUCCESS', 'FAILED', 'TIMEOUT', 'REFUNDED', 'PARTIAL_REFUND')
    ),
    gateway_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE prescription (
    id BIGSERIAL PRIMARY KEY,
    appointment_id BIGINT NOT NULL REFERENCES appointment(id),
    doctor_user_id BIGINT NOT NULL REFERENCES doctor(user_id),
    patient_user_id BIGINT NOT NULL REFERENCES patient(user_id),
    diagnosis TEXT,
    notes TEXT,
    follow_up_date DATE,
    document_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE medical_document (
    id BIGSERIAL PRIMARY KEY,
    patient_user_id BIGINT NOT NULL REFERENCES patient(user_id),
    file_name VARCHAR(255) NOT NULL,
    file_url TEXT NOT NULL,
    uploaded_by_user_id BIGINT NOT NULL REFERENCES app_user(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE notification (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES app_user(id),
    event_type VARCHAR(40) NOT NULL,
    channel VARCHAR(20) NOT NULL CHECK (channel IN ('EMAIL', 'SMS', 'WHATSAPP', 'IN_APP')),
    message TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    scheduled_for TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    actor_user_id BIGINT REFERENCES app_user(id),
    action VARCHAR(120) NOT NULL,
    entity_type VARCHAR(60) NOT NULL,
    entity_id VARCHAR(60) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_doctor_specialty ON doctor(specialty_id);
CREATE INDEX idx_doctor_location_search ON clinic(location);
CREATE INDEX idx_slot_lookup ON appointment_slot(doctor_user_id, slot_start, status);
CREATE INDEX idx_slot_hold_until ON appointment_slot(hold_until) WHERE status = 'HOLD';
CREATE INDEX idx_appointment_patient ON appointment(patient_user_id, created_at DESC);
CREATE INDEX idx_appointment_doctor ON appointment(doctor_user_id, created_at DESC);
CREATE INDEX idx_payment_status ON payment(status, created_at DESC);
CREATE INDEX idx_notification_user_status ON notification(user_id, status, scheduled_for);
