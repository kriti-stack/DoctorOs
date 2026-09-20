from datetime import date, datetime, time, timedelta
from threading import Barrier, Thread
import unittest

from appointment_booking import AppointmentBookingSystem, AppointmentStatus, UserRole


class AppointmentBookingSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.system = AppointmentBookingSystem()
        self.patient_one = self.system.register_user(UserRole.PATIENT, "Alice", email="alice@test.com")
        self.patient_two = self.system.register_user(UserRole.PATIENT, "Bob", email="bob@test.com")
        self.admin = self.system.register_user(UserRole.ADMIN, "Admin", email="admin@test.com")
        self.doctor = self.system.register_user(UserRole.DOCTOR, "Dr. Green", email="dr.green@test.com")
        self.system.create_doctor_profile(
            doctor_user_id=self.doctor.id,
            specialty="Cardiology",
            location="New York",
            experience_years=10,
            gender="Female",
            consultation_fee=120.0,
            languages=["English", "Hindi"],
        )
        self.system.add_doctor_availability(
            doctor_user_id=self.doctor.id,
            day_of_week=0,
            start_time=time(10, 0),
            end_time=time(12, 0),
            appointment_minutes=30,
            consultation_type="OFFLINE",
            clinic_name="Main Clinic",
        )
        self.system.add_doctor_break(
            doctor_user_id=self.doctor.id,
            day_of_week=0,
            start_time=time(11, 0),
            end_time=time(11, 30),
        )

    def test_generates_slots_from_availability_excluding_breaks(self) -> None:
        generated = self.system.generate_slots(self.doctor.id, date(2026, 9, 21))

        self.assertEqual(len(generated), 3)
        self.assertEqual([slot.start_time.time().strftime("%H:%M") for slot in generated], ["10:00", "10:30", "11:30"])

    def test_concurrent_hold_allows_only_single_patient(self) -> None:
        slot = self.system.generate_slots(self.doctor.id, date(2026, 9, 21))[0]
        barrier = Barrier(2)
        outcomes: list[tuple[int, str]] = []

        def contender(patient_id: int) -> None:
            barrier.wait()
            try:
                self.system.hold_slot(patient_id, slot.id, hold_minutes=10, now=datetime(2026, 9, 20, 10, 0))
                outcomes.append((patient_id, "HELD"))
            except ValueError:
                outcomes.append((patient_id, "REJECTED"))

        threads = [
            Thread(target=contender, args=(self.patient_one.id,)),
            Thread(target=contender, args=(self.patient_two.id,)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(sorted(result for _, result in outcomes), ["HELD", "REJECTED"])

    def test_payment_failure_releases_hold(self) -> None:
        slot = self.system.generate_slots(self.doctor.id, date(2026, 9, 21))[0]
        held = self.system.hold_slot(self.patient_one.id, slot.id, now=datetime(2026, 9, 20, 10, 0))
        self.assertEqual(held.status, AppointmentStatus.HOLD)

        booked = self.system.confirm_payment_and_book(
            patient_user_id=self.patient_one.id,
            slot_id=slot.id,
            payment_reference="PAY-FAIL-1",
            amount=120.0,
            payment_succeeded=False,
            now=datetime(2026, 9, 20, 10, 1),
        )
        self.assertIsNone(booked)

        available_slots = self.system.list_available_slots(
            doctor_user_id=self.doctor.id,
            slot_date=date(2026, 9, 21),
            now=datetime(2026, 9, 20, 10, 2),
        )
        self.assertIn(slot.id, [item.id for item in available_slots])

    def test_successful_payment_confirms_appointment_and_blocks_slot(self) -> None:
        slot = self.system.generate_slots(self.doctor.id, date(2026, 9, 21))[0]
        self.system.hold_slot(self.patient_one.id, slot.id, now=datetime(2026, 9, 20, 10, 0))
        appointment = self.system.confirm_payment_and_book(
            patient_user_id=self.patient_one.id,
            slot_id=slot.id,
            payment_reference="PAY-SUCCESS-1",
            amount=120.0,
            payment_succeeded=True,
            now=datetime(2026, 9, 20, 10, 1),
        )

        self.assertIsNotNone(appointment)
        self.assertEqual(appointment.status, AppointmentStatus.CONFIRMED)
        self.assertTrue(appointment.appointment_number.startswith("APT-20260920-"))
        self.assertEqual(self.system.list_all_appointments(self.admin.id)[0].id, appointment.id)
        with self.assertRaisesRegex(ValueError, "not available"):
            self.system.hold_slot(self.patient_two.id, slot.id, now=datetime(2026, 9, 20, 10, 2))

    def test_expired_hold_is_released(self) -> None:
        slot = self.system.generate_slots(self.doctor.id, date(2026, 9, 21))[0]
        self.system.hold_slot(self.patient_one.id, slot.id, hold_minutes=1, now=datetime(2026, 9, 20, 10, 0))
        self.system.release_expired_holds(now=datetime(2026, 9, 20, 10, 2))

        held_again = self.system.hold_slot(self.patient_two.id, slot.id, now=datetime(2026, 9, 20, 10, 3))
        self.assertEqual(held_again.held_by_patient_user_id, self.patient_two.id)

    def test_doctor_search_filters(self) -> None:
        results = self.system.search_doctors(
            specialty="Cardiology",
            location="new york",
            experience_min=5,
            fee_max=200,
            language="hindi",
            gender="female",
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].doctor_user_id, self.doctor.id)

    def test_patient_cannot_view_other_patient_documents(self) -> None:
        self.system.upload_medical_document(self.patient_one.id, "blood-report.pdf")

        with self.assertRaisesRegex(PermissionError, "own documents"):
            self.system.list_medical_documents(self.patient_one.id, requested_by_user_id=self.patient_two.id)

    def test_doctor_can_view_documents_only_for_assigned_patient(self) -> None:
        slot = self.system.generate_slots(self.doctor.id, date(2026, 9, 21))[0]
        self.system.hold_slot(self.patient_one.id, slot.id, now=datetime(2026, 9, 20, 10, 0))
        self.system.confirm_payment_and_book(
            patient_user_id=self.patient_one.id,
            slot_id=slot.id,
            payment_reference="PAY-SUCCESS-2",
            amount=120.0,
            payment_succeeded=True,
            now=datetime(2026, 9, 20, 10, 1),
        )
        self.system.upload_medical_document(self.patient_one.id, "xray.pdf")

        docs = self.system.list_medical_documents(self.patient_one.id, requested_by_user_id=self.doctor.id)
        self.assertEqual(docs, ["xray.pdf"])

    def test_reschedule_updates_slot_and_status(self) -> None:
        slots = self.system.generate_slots(self.doctor.id, date(2026, 9, 21))
        first_slot, second_slot = slots[0], slots[1]
        self.system.hold_slot(self.patient_one.id, first_slot.id, now=datetime(2026, 9, 20, 10, 0))
        appointment = self.system.confirm_payment_and_book(
            patient_user_id=self.patient_one.id,
            slot_id=first_slot.id,
            payment_reference="PAY-SUCCESS-3",
            amount=120.0,
            payment_succeeded=True,
            now=datetime(2026, 9, 20, 10, 1),
        )

        updated = self.system.reschedule_appointment(
            patient_user_id=self.patient_one.id,
            appointment_id=appointment.id,
            new_slot_id=second_slot.id,
            now=datetime(2026, 9, 20, 11, 0),
        )
        self.assertEqual(updated.status, AppointmentStatus.RESCHEDULED)
        self.assertEqual(updated.slot_id, second_slot.id)

    def test_hold_must_belong_to_patient_when_confirming(self) -> None:
        slot = self.system.generate_slots(self.doctor.id, date(2026, 9, 21))[0]
        self.system.hold_slot(self.patient_one.id, slot.id, now=datetime(2026, 9, 20, 10, 0))

        with self.assertRaisesRegex(ValueError, "held by this patient"):
            self.system.confirm_payment_and_book(
                patient_user_id=self.patient_two.id,
                slot_id=slot.id,
                payment_reference="PAY-SUCCESS-4",
                amount=120.0,
                payment_succeeded=True,
                now=datetime(2026, 9, 20, 10, 1),
            )


if __name__ == "__main__":
    unittest.main()
