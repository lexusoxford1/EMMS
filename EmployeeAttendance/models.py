import re

from django.contrib.auth.models import User
from django.db import models, transaction
from django.utils import timezone


class Employee(models.Model):
    STATUS_ACTIVE = "Active"
    STATUS_NON_ACTIVE = "Non-Active"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_NON_ACTIVE, "Non-Active"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    employee_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    department = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    @classmethod
    def generate_employee_id(cls):
        prefix = "EMP"
        pattern = re.compile(r"^EMP-(\d+)$")
        max_number = 0

        for existing_id in cls.objects.values_list("employee_id", flat=True):
            match = pattern.match(existing_id or "")
            if match:
                max_number = max(max_number, int(match.group(1)))

        return f"{prefix}-{max_number + 1:04d}"

    def __str__(self):
        return f"{self.employee_id} - {self.name}"


class Attendance(models.Model):
    REQUIRED_HOURS = 8
    STEP_SEQUENCE = [
        ("morning_in", "Morning In"),
        ("morning_out", "Morning Out"),
        ("afternoon_in", "Afternoon In"),
        ("afternoon_out", "Afternoon Out"),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.localdate)

    morning_in = models.DateTimeField(null=True, blank=True)
    morning_out = models.DateTimeField(null=True, blank=True)
    afternoon_in = models.DateTimeField(null=True, blank=True)
    afternoon_out = models.DateTimeField(null=True, blank=True)

    @classmethod
    def next_step_for_record(cls, record):
        for field_name, label in cls.STEP_SEQUENCE:
            if not getattr(record, field_name):
                return field_name, label
        return None, None

    @property
    def morning_hours(self):
        if self.morning_in and self.morning_out:
            duration = self.morning_out - self.morning_in
            return round(duration.total_seconds() / 3600, 2)
        return 0

    @property
    def afternoon_hours(self):
        if self.afternoon_in and self.afternoon_out:
            duration = self.afternoon_out - self.afternoon_in
            return round(duration.total_seconds() / 3600, 2)
        return 0

    @property
    def total_hours(self):
        return self.morning_hours + self.afternoon_hours

    @property
    def attendance_status(self):
        if self.total_hours < self.REQUIRED_HOURS:
            return "Undertime"
        if self.total_hours > self.REQUIRED_HOURS:
            return "Overtime"
        return "Completed"

    def __str__(self):
        return f"{self.employee.name} - {self.date}"


class AttendanceLocation(models.Model):
    TYPE_MORNING_IN = "morning_in"
    TYPE_MORNING_OUT = "morning_out"
    TYPE_AFTERNOON_IN = "afternoon_in"
    TYPE_AFTERNOON_OUT = "afternoon_out"
    ATTENDANCE_TYPE_CHOICES = [
        (TYPE_MORNING_IN, "Morning In"),
        (TYPE_MORNING_OUT, "Morning Out"),
        (TYPE_AFTERNOON_IN, "Afternoon In"),
        (TYPE_AFTERNOON_OUT, "Afternoon Out"),
    ]

    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name="location_logs")
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendance_locations")
    attendance_type = models.CharField(max_length=20, choices=ATTENDANCE_TYPE_CHOICES)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    address = models.CharField(max_length=255, blank=True)
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"{self.employee.employee_id} - {self.get_attendance_type_display()} - {self.recorded_at:%Y-%m-%d %H:%M:%S}"


class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.name} - {self.leave_date} - {self.status}"
