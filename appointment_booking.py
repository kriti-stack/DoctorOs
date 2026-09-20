from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Doctor:
    id: int
    name: str
    specialty: str


@dataclass(frozen=True)
class Appointment:
    id: int
    doctor_id: int
    patient_name: str
    start_time: datetime
    end_time: datetime


class AppointmentBookingSystem:
    def __init__(self) -> None:
        self._next_doctor_id = 1
        self._next_appointment_id = 1
        self._doctors: dict[int, Doctor] = {}
        self._appointments: list[Appointment] = []

    def add_doctor(self, name: str, specialty: str) -> Doctor:
        if not name.strip():
            raise ValueError("Doctor name is required.")
        if not specialty.strip():
            raise ValueError("Doctor specialty is required.")

        doctor = Doctor(id=self._next_doctor_id, name=name.strip(), specialty=specialty.strip())
        self._doctors[doctor.id] = doctor
        self._next_doctor_id += 1
        return doctor

    def list_doctors(self, specialty: str | None = None) -> list[Doctor]:
        doctors = list(self._doctors.values())
        if specialty is None:
            return doctors
        specialty_filter = specialty.strip().lower()
        return [doctor for doctor in doctors if doctor.specialty.lower() == specialty_filter]

    def book_appointment(
        self,
        doctor_id: int,
        patient_name: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Appointment:
        if doctor_id not in self._doctors:
            raise ValueError("Doctor does not exist.")
        if not patient_name.strip():
            raise ValueError("Patient name is required.")
        if start_time >= end_time:
            raise ValueError("Appointment start time must be before end time.")

        for existing in self._appointments:
            if existing.doctor_id != doctor_id:
                continue
            if start_time < existing.end_time and end_time > existing.start_time:
                raise ValueError("Doctor is not available for the requested time slot.")

        appointment = Appointment(
            id=self._next_appointment_id,
            doctor_id=doctor_id,
            patient_name=patient_name.strip(),
            start_time=start_time,
            end_time=end_time,
        )
        self._appointments.append(appointment)
        self._next_appointment_id += 1
        return appointment

    def list_appointments(self, doctor_id: int | None = None, on_date: date | None = None) -> list[Appointment]:
        appointments = self._appointments
        if doctor_id is not None:
            appointments = [appointment for appointment in appointments if appointment.doctor_id == doctor_id]
        if on_date is not None:
            appointments = [appointment for appointment in appointments if appointment.start_time.date() == on_date]
        return appointments
