"""EMMS tests module."""

import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Attendance, AttendanceLocation, Employee


class AttendanceLocationApiTests(TestCase):
    """API tests covering the employee attendance recording and history flow."""
    def setUp(self):
        """Create a logged-in employee used by the attendance API test scenarios."""
        self.password = "testpass123"
        self.user = User.objects.create_user(username="employee", password=self.password)
        self.employee = Employee.objects.create(
            user=self.user,
            employee_id="EMP-0001",
            name="Jane Doe",
            department="HR",
            status=Employee.STATUS_ACTIVE,
        )
        self.client = Client()
        self.client.login(username="employee", password=self.password)

    def test_record_api_creates_attendance_and_location_log_for_first_step(self):
        response = self.client.post(
            reverse("attendance_record_api"),
            data=json.dumps(
                {
                    "latitude": 14.5995,
                    "longitude": 120.9842,
                    "address": "Manila, Philippines",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["attendance"]["attendance_type"], AttendanceLocation.TYPE_MORNING_IN)
        self.assertEqual(payload["attendance"]["attendance_type_label"], "Morning In")

        attendance = Attendance.objects.get(employee=self.employee, date=timezone.localdate())
        self.assertIsNotNone(attendance.morning_in)
        self.assertIsNone(attendance.morning_out)

        log = AttendanceLocation.objects.get(attendance=attendance)
        self.assertEqual(log.attendance_type, AttendanceLocation.TYPE_MORNING_IN)
        self.assertEqual(log.address, "Manila, Philippines")
        self.assertEqual(log.latitude, Decimal("14.5995"))
        self.assertEqual(log.longitude, Decimal("120.9842"))

    def test_record_api_enforces_strict_attendance_order(self):
        today = timezone.localdate()
        Attendance.objects.create(
            employee=self.employee,
            date=today,
            morning_in=timezone.now(),
            morning_out=timezone.now(),
            afternoon_in=timezone.now(),
            afternoon_out=timezone.now(),
        )

        response = self.client.post(
            reverse("attendance_record_api"),
            data=json.dumps({"latitude": 14.5, "longitude": 121.0}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Attendance for today is already complete.")

    def test_record_api_validates_coordinates(self):
        response = self.client.post(
            reverse("attendance_record_api"),
            data=json.dumps({"latitude": "abc", "longitude": 121.0}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            "Latitude and longitude must be numeric values.",
        )

    def test_location_history_api_returns_only_current_employee_logs(self):
        attendance = Attendance.objects.create(
            employee=self.employee,
            date=timezone.localdate(),
            morning_in=timezone.now(),
        )
        AttendanceLocation.objects.create(
            attendance=attendance,
            employee=self.employee,
            attendance_type=AttendanceLocation.TYPE_MORNING_IN,
            latitude=Decimal("14.599500"),
            longitude=Decimal("120.984200"),
            address="HQ",
        )

        other_user = User.objects.create_user(username="other", password=self.password)
        other_employee = Employee.objects.create(
            user=other_user,
            employee_id="EMP-0002",
            name="John Doe",
            department="IT",
            status=Employee.STATUS_ACTIVE,
        )
        other_attendance = Attendance.objects.create(
            employee=other_employee,
            date=timezone.localdate(),
            morning_in=timezone.now(),
        )
        AttendanceLocation.objects.create(
            attendance=other_attendance,
            employee=other_employee,
            attendance_type=AttendanceLocation.TYPE_MORNING_IN,
            latitude=Decimal("15.000000"),
            longitude=Decimal("121.000000"),
            address="Branch",
        )

        response = self.client.get(reverse("attendance_location_history_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["employee_id"], self.employee.employee_id)


class AttendanceLocationAdminHistoryTests(TestCase):
    """Admin-side tests for reviewing attendance location history filters."""
    def setUp(self):
        """Create a logged-in employee used by the attendance API test scenarios."""
        self.password = "adminpass123"
        self.admin = User.objects.create_superuser(username="admin", password=self.password, email="admin@example.com")
        self.employee_user = User.objects.create_user(username="staff", password="staffpass123")
        self.employee = Employee.objects.create(
            user=self.employee_user,
            employee_id="EMP-0003",
            name="Staff User",
            department="Ops",
            status=Employee.STATUS_ACTIVE,
        )
        attendance = Attendance.objects.create(
            employee=self.employee,
            date=timezone.localdate(),
            morning_in=timezone.now(),
        )
        AttendanceLocation.objects.create(
            attendance=attendance,
            employee=self.employee,
            attendance_type=AttendanceLocation.TYPE_MORNING_IN,
            latitude=Decimal("14.123456"),
            longitude=Decimal("121.123456"),
            address="Operations Hub",
        )
        self.client = Client()
        self.client.login(username="admin", password=self.password)

    def test_admin_can_filter_location_history_by_employee_id(self):
        response = self.client.get(
            reverse("attendance_location_history_api"),
            {"employee_id": self.employee.employee_id},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["employee_name"], self.employee.name)





