from django.contrib import admin

from EmployeeAttendance.models import Attendance, AttendanceLocation, Employee, LeaveRequest


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "name", "department", "status")
    list_filter = ("status", "department")
    search_fields = ("employee_id", "name", "department")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "attendance_status", "total_hours")
    list_filter = ("date",)
    search_fields = ("employee__employee_id", "employee__name")


@admin.register(AttendanceLocation)
class AttendanceLocationAdmin(admin.ModelAdmin):
    list_display = ("employee", "attendance_type", "recorded_at", "latitude", "longitude")
    list_filter = ("attendance_type", "recorded_at")
    search_fields = ("employee__employee_id", "employee__name", "address")


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_date", "status", "created_at")
    list_filter = ("status", "leave_date")
    search_fields = ("employee__employee_id", "employee__name", "reason")
