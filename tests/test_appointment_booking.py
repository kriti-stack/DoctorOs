from datetime import datetime
import unittest

from appointment_booking import AppointmentBookingSystem


class AppointmentBookingSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.system = AppointmentBookingSystem()
        self.cardiologist = self.system.add_doctor("Dr. Green", "Cardiology")
        self.dermatologist = self.system.add_doctor("Dr. Lee", "Dermatology")

    def test_books_appointment_for_existing_doctor(self) -> None:
        appointment = self.system.book_appointment(
            doctor_id=self.cardiologist.id,
            patient_name="Alice",
            start_time=datetime(2026, 9, 21, 10, 0),
            end_time=datetime(2026, 9, 21, 10, 30),
        )

        self.assertEqual(appointment.id, 1)
        self.assertEqual(appointment.doctor_id, self.cardiologist.id)
        self.assertEqual(len(self.system.list_appointments(doctor_id=self.cardiologist.id)), 1)

    def test_rejects_overlapping_appointment_for_same_doctor(self) -> None:
        self.system.book_appointment(
            doctor_id=self.cardiologist.id,
            patient_name="Alice",
            start_time=datetime(2026, 9, 21, 10, 0),
            end_time=datetime(2026, 9, 21, 10, 30),
        )

        with self.assertRaisesRegex(ValueError, "not available"):
            self.system.book_appointment(
                doctor_id=self.cardiologist.id,
                patient_name="Bob",
                start_time=datetime(2026, 9, 21, 10, 15),
                end_time=datetime(2026, 9, 21, 10, 45),
            )

    def test_allows_same_time_slot_for_different_doctors(self) -> None:
        self.system.book_appointment(
            doctor_id=self.cardiologist.id,
            patient_name="Alice",
            start_time=datetime(2026, 9, 21, 10, 0),
            end_time=datetime(2026, 9, 21, 10, 30),
        )
        appointment = self.system.book_appointment(
            doctor_id=self.dermatologist.id,
            patient_name="Bob",
            start_time=datetime(2026, 9, 21, 10, 0),
            end_time=datetime(2026, 9, 21, 10, 30),
        )

        self.assertEqual(appointment.id, 2)
        self.assertEqual(len(self.system.list_appointments()), 2)

    def test_lists_doctors_by_specialty(self) -> None:
        doctors = self.system.list_doctors(specialty="cardiology")

        self.assertEqual([doctor.id for doctor in doctors], [self.cardiologist.id])


if __name__ == "__main__":
    unittest.main()
