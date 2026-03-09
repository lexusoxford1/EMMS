from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    employee_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    department = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.employee_id} - {self.name}"


class Attendance(models.Model):
    REQUIRED_HOURS = 8

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.localdate)

    morning_in = models.DateTimeField(null=True, blank=True)
    morning_out = models.DateTimeField(null=True, blank=True)
    afternoon_in = models.DateTimeField(null=True, blank=True)
    afternoon_out = models.DateTimeField(null=True, blank=True)

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
