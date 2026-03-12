"""EMMS apps module."""

from django.apps import AppConfig


class EmployeeAttendanceConfig(AppConfig):
    """Application metadata used by Django when the EmployeeAttendance app loads."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "EmployeeAttendance"
    verbose_name = "Employee Attendance"



