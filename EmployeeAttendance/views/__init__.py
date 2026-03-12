"""Public view exports for the EmployeeAttendance app."""

from .attendance import attendance_location_history_api, attendance_record_api, attendance_view, filter_attendance_api
from .auth import login_view, logout_view
from .dashboard import dashboard
from .docs import api_docs_view, api_schema_view, api_schema_yaml_view
from .employees import employee_add, employee_list, employee_toggle_status
from .leaves import leave_add, leave_approve, leave_list, leave_reject
from .locations import location_tracking_view
from .reports import export_excel, export_pdf, report_view

__all__ = [
    "api_docs_view",
    "api_schema_view",
    "api_schema_yaml_view",
    "attendance_location_history_api",
    "attendance_record_api",
    "attendance_view",
    "dashboard",
    "employee_add",
    "employee_list",
    "employee_toggle_status",
    "export_excel",
    "export_pdf",
    "filter_attendance_api",
    "leave_add",
    "leave_approve",
    "leave_list",
    "leave_reject",
    "location_tracking_view",
    "login_view",
    "logout_view",
    "report_view",
]
