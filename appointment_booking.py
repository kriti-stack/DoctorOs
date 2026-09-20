from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from threading import RLock


class UserRole(StrEnum):
    PATIENT = "PATIENT"
    DOCTOR = "DOCTOR"
    ADMIN = "ADMIN"


class AppointmentStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    HOLD = "HOLD"
    BOOKED = "BOOKED"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"
    RESCHEDULED = "RESCHEDULED"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    PARTIAL_REFUND = "PARTIAL_REFUND"


@dataclass(frozen=True)
class User:
    id: int
    role: UserRole
    name: str
    email: str | None = None
    mobile: str | None = None


@dataclass(frozen=True)
class DoctorProfile:
    doctor_user_id: int
    specialty: str
    location: str
    experience_years: int
    gender: str
    consultation_fee: float
    languages: tuple[str, ...]


@dataclass(frozen=True)
class DoctorAvailability:
    doctor_user_id: int
    day_of_week: int
    start_time: time
    end_time: time
    appointment_minutes: int
    consultation_type: str
    clinic_name: str | None = None


@dataclass(frozen=True)
class DoctorBreak:
    doctor_user_id: int
    day_of_week: int
    start_time: time
    end_time: time


@dataclass(frozen=True)
class AppointmentSlot:
    id: int
    doctor_user_id: int
    slot_date: date
    start_time: datetime
    end_time: datetime
    consultation_type: str
    clinic_name: str | None
    status: AppointmentStatus
    hold_expires_at: datetime | None = None
    held_by_patient_user_id: int | None = None


@dataclass(frozen=True)
class Appointment:
    id: int
    appointment_number: str
    patient_user_id: int
    doctor_user_id: int
    slot_id: int
    clinic_name: str | None
    start_time: datetime
    end_time: datetime
    appointment_type: str
    status: AppointmentStatus
    payment_status: PaymentStatus
    consultation_fee: float
    notes: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Payment:
    id: int
    appointment_id: int
    payment_reference: str
    amount: float
    status: PaymentStatus
    created_at: datetime


@dataclass(frozen=True)
class Prescription:
    id: int
    appointment_id: int
    doctor_user_id: int
    patient_user_id: int
    diagnosis: str
    notes: str
    follow_up_date: date | None
    created_at: datetime


class AppointmentBookingSystem:
    def __init__(self) -> None:
        self._lock = RLock()
        self._next_user_id = 1
        self._next_slot_id = 1
        self._next_appointment_id = 1
        self._next_payment_id = 1
        self._next_prescription_id = 1

        self._users: dict[int, User] = {}
        self._doctor_profiles: dict[int, DoctorProfile] = {}
        self._availability_by_doctor: dict[int, list[DoctorAvailability]] = {}
        self._breaks_by_doctor: dict[int, list[DoctorBreak]] = {}
        self._leaves_by_doctor: dict[int, set[date]] = {}
        self._slots: dict[int, AppointmentSlot] = {}
        self._appointments: dict[int, Appointment] = {}
        self._payments: dict[int, Payment] = {}
        self._payment_reference_index: set[str] = set()
        self._prescriptions: dict[int, Prescription] = {}
        self._documents_by_patient: dict[int, list[str]] = {}
        self._notifications: list[dict[str, str]] = []

    def register_user(
        self,
        role: UserRole,
        name: str,
        email: str | None = None,
        mobile: str | None = None,
    ) -> User:
        if not name.strip():
            raise ValueError("Name is required.")
        if not (email or mobile):
            raise ValueError("Email or mobile is required.")
        user = User(
            id=self._next_user_id,
            role=role,
            name=name.strip(),
            email=email.strip() if email else None,
            mobile=mobile.strip() if mobile else None,
        )
        self._users[user.id] = user
        self._next_user_id += 1
        return user

    def create_doctor_profile(
        self,
        doctor_user_id: int,
        specialty: str,
        location: str,
        experience_years: int,
        gender: str,
        consultation_fee: float,
        languages: list[str],
    ) -> DoctorProfile:
        self._require_role(doctor_user_id, UserRole.DOCTOR)
        if experience_years < 0:
            raise ValueError("Experience cannot be negative.")
        if consultation_fee < 0:
            raise ValueError("Consultation fee cannot be negative.")
        if not specialty.strip() or not location.strip():
            raise ValueError("Specialty and location are required.")
        profile = DoctorProfile(
            doctor_user_id=doctor_user_id,
            specialty=specialty.strip(),
            location=location.strip(),
            experience_years=experience_years,
            gender=gender.strip(),
            consultation_fee=float(consultation_fee),
            languages=tuple(language.strip() for language in languages if language.strip()),
        )
        self._doctor_profiles[doctor_user_id] = profile
        return profile

    def add_doctor_availability(
        self,
        doctor_user_id: int,
        day_of_week: int,
        start_time: time,
        end_time: time,
        appointment_minutes: int,
        consultation_type: str,
        clinic_name: str | None = None,
    ) -> None:
        self._require_role(doctor_user_id, UserRole.DOCTOR)
        if start_time >= end_time:
            raise ValueError("Availability start time must be before end time.")
        if appointment_minutes <= 0:
            raise ValueError("Appointment duration must be positive.")
        if day_of_week < 0 or day_of_week > 6:
            raise ValueError("day_of_week must be between 0 and 6.")
        self._availability_by_doctor.setdefault(doctor_user_id, []).append(
            DoctorAvailability(
                doctor_user_id=doctor_user_id,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time,
                appointment_minutes=appointment_minutes,
                consultation_type=consultation_type.strip().upper(),
                clinic_name=clinic_name.strip() if clinic_name else None,
            )
        )

    def add_doctor_break(
        self,
        doctor_user_id: int,
        day_of_week: int,
        start_time: time,
        end_time: time,
    ) -> None:
        self._require_role(doctor_user_id, UserRole.DOCTOR)
        if start_time >= end_time:
            raise ValueError("Break start time must be before end time.")
        self._breaks_by_doctor.setdefault(doctor_user_id, []).append(
            DoctorBreak(
                doctor_user_id=doctor_user_id,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time,
            )
        )

    def add_doctor_leave(self, doctor_user_id: int, leave_date: date) -> None:
        self._require_role(doctor_user_id, UserRole.DOCTOR)
        self._leaves_by_doctor.setdefault(doctor_user_id, set()).add(leave_date)

    def generate_slots(self, doctor_user_id: int, slot_date: date) -> list[AppointmentSlot]:
        self._require_role(doctor_user_id, UserRole.DOCTOR)
        if slot_date in self._leaves_by_doctor.get(doctor_user_id, set()):
            return []

        day_of_week = slot_date.weekday()
        availabilities = [
            availability
            for availability in self._availability_by_doctor.get(doctor_user_id, [])
            if availability.day_of_week == day_of_week
        ]
        breaks = [
            item
            for item in self._breaks_by_doctor.get(doctor_user_id, [])
            if item.day_of_week == day_of_week
        ]
        created_slots: list[AppointmentSlot] = []

        with self._lock:
            for availability in availabilities:
                cursor = datetime.combine(slot_date, availability.start_time)
                end_at = datetime.combine(slot_date, availability.end_time)
                slot_duration = timedelta(minutes=availability.appointment_minutes)
                while cursor + slot_duration <= end_at:
                    candidate_end = cursor + slot_duration
                    if self._is_within_break(cursor, candidate_end, slot_date, breaks):
                        cursor = candidate_end
                        continue
                    if self._slot_exists(doctor_user_id, cursor, candidate_end, availability.consultation_type):
                        cursor = candidate_end
                        continue
                    slot = AppointmentSlot(
                        id=self._next_slot_id,
                        doctor_user_id=doctor_user_id,
                        slot_date=slot_date,
                        start_time=cursor,
                        end_time=candidate_end,
                        consultation_type=availability.consultation_type,
                        clinic_name=availability.clinic_name,
                        status=AppointmentStatus.AVAILABLE,
                    )
                    self._slots[slot.id] = slot
                    created_slots.append(slot)
                    self._next_slot_id += 1
                    cursor = candidate_end

        return created_slots

    def list_available_slots(
        self,
        doctor_user_id: int,
        slot_date: date,
        consultation_type: str | None = None,
        now: datetime | None = None,
    ) -> list[AppointmentSlot]:
        now = now or datetime.utcnow()
        self.release_expired_holds(now=now)
        available_slots = [
            slot
            for slot in self._slots.values()
            if slot.doctor_user_id == doctor_user_id
            and slot.slot_date == slot_date
            and slot.status == AppointmentStatus.AVAILABLE
        ]
        if consultation_type:
            normalized = consultation_type.strip().upper()
            available_slots = [slot for slot in available_slots if slot.consultation_type == normalized]
        return sorted(available_slots, key=lambda slot: slot.start_time)

    def search_doctors(
        self,
        name: str | None = None,
        specialty: str | None = None,
        location: str | None = None,
        experience_min: int | None = None,
        gender: str | None = None,
        fee_max: float | None = None,
        language: str | None = None,
    ) -> list[DoctorProfile]:
        profiles = list(self._doctor_profiles.values())
        if name:
            name_filter = name.strip().lower()
            profiles = [
                profile
                for profile in profiles
                if name_filter in self._users[profile.doctor_user_id].name.lower()
            ]
        if specialty:
            specialty_filter = specialty.strip().lower()
            profiles = [profile for profile in profiles if profile.specialty.lower() == specialty_filter]
        if location:
            location_filter = location.strip().lower()
            profiles = [profile for profile in profiles if location_filter in profile.location.lower()]
        if experience_min is not None:
            profiles = [profile for profile in profiles if profile.experience_years >= experience_min]
        if gender:
            gender_filter = gender.strip().lower()
            profiles = [profile for profile in profiles if profile.gender.lower() == gender_filter]
        if fee_max is not None:
            profiles = [profile for profile in profiles if profile.consultation_fee <= fee_max]
        if language:
            language_filter = language.strip().lower()
            profiles = [
                profile
                for profile in profiles
                if any(spoken.lower() == language_filter for spoken in profile.languages)
            ]
        return profiles

    def hold_slot(
        self,
        patient_user_id: int,
        slot_id: int,
        hold_minutes: int = 10,
        now: datetime | None = None,
    ) -> AppointmentSlot:
        self._require_role(patient_user_id, UserRole.PATIENT)
        now = now or datetime.utcnow()
        with self._lock:
            self.release_expired_holds(now=now)
            slot = self._get_slot(slot_id)
            if slot.status != AppointmentStatus.AVAILABLE:
                raise ValueError("Slot is not available.")
            updated = AppointmentSlot(
                **{
                    **slot.__dict__,
                    "status": AppointmentStatus.HOLD,
                    "held_by_patient_user_id": patient_user_id,
                    "hold_expires_at": now + timedelta(minutes=hold_minutes),
                }
            )
            self._slots[slot_id] = updated
            return updated

    def confirm_payment_and_book(
        self,
        patient_user_id: int,
        slot_id: int,
        payment_reference: str,
        amount: float,
        payment_succeeded: bool,
        now: datetime | None = None,
    ) -> Appointment | None:
        self._require_role(patient_user_id, UserRole.PATIENT)
        if amount < 0:
            raise ValueError("Payment amount cannot be negative.")
        now = now or datetime.utcnow()
        with self._lock:
            self.release_expired_holds(now=now)
            slot = self._get_slot(slot_id)
            if slot.status != AppointmentStatus.HOLD or slot.held_by_patient_user_id != patient_user_id:
                raise ValueError("Slot is not held by this patient.")
            if payment_reference in self._payment_reference_index:
                raise ValueError("Duplicate payment reference.")

            if not payment_succeeded:
                self._slots[slot_id] = AppointmentSlot(
                    **{
                        **slot.__dict__,
                        "status": AppointmentStatus.AVAILABLE,
                        "held_by_patient_user_id": None,
                        "hold_expires_at": None,
                    }
                )
                self._store_payment(
                    appointment_id=0,
                    payment_reference=payment_reference,
                    amount=amount,
                    status=PaymentStatus.FAILED,
                    created_at=now,
                )
                self._emit_notification(
                    patient_user_id,
                    "PAYMENT_FAILED",
                    "Payment failed and the slot has been released.",
                )
                return None

            profile = self._doctor_profiles.get(slot.doctor_user_id)
            if profile is None:
                raise ValueError("Doctor profile is missing.")
            appointment = Appointment(
                id=self._next_appointment_id,
                appointment_number=self._generate_appointment_number(now),
                patient_user_id=patient_user_id,
                doctor_user_id=slot.doctor_user_id,
                slot_id=slot.id,
                clinic_name=slot.clinic_name,
                start_time=slot.start_time,
                end_time=slot.end_time,
                appointment_type=slot.consultation_type,
                status=AppointmentStatus.CONFIRMED,
                payment_status=PaymentStatus.SUCCESS,
                consultation_fee=profile.consultation_fee,
                notes=None,
                created_at=now,
                updated_at=now,
            )
            self._appointments[appointment.id] = appointment
            self._next_appointment_id += 1
            self._store_payment(
                appointment_id=appointment.id,
                payment_reference=payment_reference,
                amount=amount,
                status=PaymentStatus.SUCCESS,
                created_at=now,
            )
            self._slots[slot.id] = AppointmentSlot(
                **{
                    **slot.__dict__,
                    "status": AppointmentStatus.BOOKED,
                    "held_by_patient_user_id": None,
                    "hold_expires_at": None,
                }
            )
            self._emit_notification(patient_user_id, "PAYMENT_SUCCESS", "Payment verified successfully.")
            self._emit_notification(patient_user_id, "APPOINTMENT_CONFIRMED", "Appointment confirmed.")
            return appointment

    def cancel_appointment(self, patient_user_id: int, appointment_id: int, now: datetime | None = None) -> Appointment:
        self._require_role(patient_user_id, UserRole.PATIENT)
        now = now or datetime.utcnow()
        with self._lock:
            appointment = self._get_appointment(appointment_id)
            if appointment.patient_user_id != patient_user_id:
                raise PermissionError("Cannot cancel another patient's appointment.")
            if appointment.status in {AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW}:
                raise ValueError("Appointment cannot be cancelled in its current status.")
            updated = Appointment(**{**appointment.__dict__, "status": AppointmentStatus.CANCELLED, "updated_at": now})
            self._appointments[appointment_id] = updated
            slot = self._get_slot(appointment.slot_id)
            self._slots[slot.id] = AppointmentSlot(
                **{
                    **slot.__dict__,
                    "status": AppointmentStatus.AVAILABLE,
                    "held_by_patient_user_id": None,
                    "hold_expires_at": None,
                }
            )
            self._emit_notification(patient_user_id, "APPOINTMENT_CANCELLED", "Appointment cancelled.")
            return updated

    def reschedule_appointment(
        self,
        patient_user_id: int,
        appointment_id: int,
        new_slot_id: int,
        now: datetime | None = None,
    ) -> Appointment:
        self._require_role(patient_user_id, UserRole.PATIENT)
        now = now or datetime.utcnow()
        with self._lock:
            appointment = self._get_appointment(appointment_id)
            if appointment.patient_user_id != patient_user_id:
                raise PermissionError("Cannot reschedule another patient's appointment.")
            new_slot = self._get_slot(new_slot_id)
            if new_slot.status != AppointmentStatus.AVAILABLE:
                raise ValueError("Requested slot is not available.")

            old_slot = self._get_slot(appointment.slot_id)
            self._slots[old_slot.id] = AppointmentSlot(
                **{
                    **old_slot.__dict__,
                    "status": AppointmentStatus.AVAILABLE,
                    "held_by_patient_user_id": None,
                    "hold_expires_at": None,
                }
            )
            self._slots[new_slot.id] = AppointmentSlot(
                **{
                    **new_slot.__dict__,
                    "status": AppointmentStatus.BOOKED,
                    "held_by_patient_user_id": None,
                    "hold_expires_at": None,
                }
            )
            updated = Appointment(
                **{
                    **appointment.__dict__,
                    "slot_id": new_slot.id,
                    "start_time": new_slot.start_time,
                    "end_time": new_slot.end_time,
                    "clinic_name": new_slot.clinic_name,
                    "appointment_type": new_slot.consultation_type,
                    "status": AppointmentStatus.RESCHEDULED,
                    "updated_at": now,
                }
            )
            self._appointments[appointment_id] = updated
            self._emit_notification(patient_user_id, "APPOINTMENT_RESCHEDULED", "Appointment rescheduled.")
            return updated

    def mark_appointment_status(
        self,
        doctor_user_id: int,
        appointment_id: int,
        status: AppointmentStatus,
        now: datetime | None = None,
    ) -> Appointment:
        self._require_role(doctor_user_id, UserRole.DOCTOR)
        if status not in {AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW}:
            raise ValueError("Doctors can only mark COMPLETED/CANCELLED/NO_SHOW.")
        now = now or datetime.utcnow()
        with self._lock:
            appointment = self._get_appointment(appointment_id)
            if appointment.doctor_user_id != doctor_user_id:
                raise PermissionError("Cannot update another doctor's appointment.")
            updated = Appointment(**{**appointment.__dict__, "status": status, "updated_at": now})
            self._appointments[appointment.id] = updated
            return updated

    def list_patient_appointments(self, patient_user_id: int) -> list[Appointment]:
        self._require_role(patient_user_id, UserRole.PATIENT)
        return sorted(
            [appointment for appointment in self._appointments.values() if appointment.patient_user_id == patient_user_id],
            key=lambda appointment: appointment.start_time,
        )

    def list_doctor_appointments(self, doctor_user_id: int) -> list[Appointment]:
        self._require_role(doctor_user_id, UserRole.DOCTOR)
        return sorted(
            [appointment for appointment in self._appointments.values() if appointment.doctor_user_id == doctor_user_id],
            key=lambda appointment: appointment.start_time,
        )

    def list_all_appointments(self, admin_user_id: int) -> list[Appointment]:
        self._require_role(admin_user_id, UserRole.ADMIN)
        return sorted(self._appointments.values(), key=lambda appointment: appointment.start_time)

    def upload_medical_document(self, patient_user_id: int, document_name: str) -> None:
        self._require_role(patient_user_id, UserRole.PATIENT)
        if not document_name.strip():
            raise ValueError("Document name is required.")
        self._documents_by_patient.setdefault(patient_user_id, []).append(document_name.strip())

    def list_medical_documents(self, patient_user_id: int, requested_by_user_id: int) -> list[str]:
        requester = self._users.get(requested_by_user_id)
        if requester is None:
            raise ValueError("Requesting user does not exist.")
        if requester.role == UserRole.PATIENT and requester.id != patient_user_id:
            raise PermissionError("Patients can only access their own documents.")
        if requester.role == UserRole.DOCTOR:
            if not any(
                appointment.patient_user_id == patient_user_id and appointment.doctor_user_id == requester.id
                for appointment in self._appointments.values()
            ):
                raise PermissionError("Doctor is not authorized to access this patient's documents.")
        return list(self._documents_by_patient.get(patient_user_id, []))

    def add_prescription(
        self,
        doctor_user_id: int,
        appointment_id: int,
        diagnosis: str,
        notes: str,
        follow_up_date: date | None = None,
        now: datetime | None = None,
    ) -> Prescription:
        self._require_role(doctor_user_id, UserRole.DOCTOR)
        now = now or datetime.utcnow()
        appointment = self._get_appointment(appointment_id)
        if appointment.doctor_user_id != doctor_user_id:
            raise PermissionError("Doctor is not assigned to this appointment.")
        prescription = Prescription(
            id=self._next_prescription_id,
            appointment_id=appointment_id,
            doctor_user_id=doctor_user_id,
            patient_user_id=appointment.patient_user_id,
            diagnosis=diagnosis.strip(),
            notes=notes.strip(),
            follow_up_date=follow_up_date,
            created_at=now,
        )
        self._prescriptions[prescription.id] = prescription
        self._next_prescription_id += 1
        self._emit_notification(appointment.patient_user_id, "PRESCRIPTION_UPLOADED", "Prescription uploaded.")
        return prescription

    def list_patient_prescriptions(self, patient_user_id: int) -> list[Prescription]:
        self._require_role(patient_user_id, UserRole.PATIENT)
        return [item for item in self._prescriptions.values() if item.patient_user_id == patient_user_id]

    def release_expired_holds(self, now: datetime | None = None) -> None:
        now = now or datetime.utcnow()
        with self._lock:
            for slot_id, slot in list(self._slots.items()):
                if slot.status != AppointmentStatus.HOLD or slot.hold_expires_at is None:
                    continue
                if slot.hold_expires_at <= now:
                    self._slots[slot_id] = AppointmentSlot(
                        **{
                            **slot.__dict__,
                            "status": AppointmentStatus.AVAILABLE,
                            "held_by_patient_user_id": None,
                            "hold_expires_at": None,
                        }
                    )

    def _is_within_break(
        self,
        slot_start: datetime,
        slot_end: datetime,
        slot_date: date,
        breaks: list[DoctorBreak],
    ) -> bool:
        for break_window in breaks:
            break_start = datetime.combine(slot_date, break_window.start_time)
            break_end = datetime.combine(slot_date, break_window.end_time)
            if slot_start < break_end and slot_end > break_start:
                return True
        return False

    def _slot_exists(
        self,
        doctor_user_id: int,
        start_time: datetime,
        end_time: datetime,
        consultation_type: str,
    ) -> bool:
        for slot in self._slots.values():
            if slot.doctor_user_id != doctor_user_id:
                continue
            if slot.start_time == start_time and slot.end_time == end_time and slot.consultation_type == consultation_type:
                return True
        return False

    def _store_payment(
        self,
        appointment_id: int,
        payment_reference: str,
        amount: float,
        status: PaymentStatus,
        created_at: datetime,
    ) -> Payment:
        payment = Payment(
            id=self._next_payment_id,
            appointment_id=appointment_id,
            payment_reference=payment_reference.strip(),
            amount=amount,
            status=status,
            created_at=created_at,
        )
        self._payments[payment.id] = payment
        self._payment_reference_index.add(payment.payment_reference)
        self._next_payment_id += 1
        return payment

    def _generate_appointment_number(self, now: datetime) -> str:
        return f"APT-{now.strftime('%Y%m%d')}-{self._next_appointment_id:06d}"

    def _emit_notification(self, user_id: int, event: str, message: str) -> None:
        for channel in ("EMAIL", "SMS", "IN_APP"):
            self._notifications.append(
                {
                    "user_id": str(user_id),
                    "event": event,
                    "channel": channel,
                    "message": message,
                }
            )

    def _require_role(self, user_id: int, expected: UserRole) -> None:
        user = self._users.get(user_id)
        if user is None:
            raise ValueError("User does not exist.")
        if user.role != expected:
            raise PermissionError(f"{expected.value} access required.")

    def _get_slot(self, slot_id: int) -> AppointmentSlot:
        slot = self._slots.get(slot_id)
        if slot is None:
            raise ValueError("Slot does not exist.")
        return slot

    def _get_appointment(self, appointment_id: int) -> Appointment:
        appointment = self._appointments.get(appointment_id)
        if appointment is None:
            raise ValueError("Appointment does not exist.")
        return appointment
