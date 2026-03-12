from django.urls import path

from . import views

urlpatterns = [
    # Authentication and dashboard.
    path("", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),

    # Employee management.
    path("employees/", views.employee_list, name="employee_list"),
    path("employees/add/", views.employee_add, name="employee_add"),
    path("employees/<int:pk>/toggle-status/", views.employee_toggle_status, name="employee_toggle_status"),

    # Attendance UI and APIs.
    path("attendance/", views.attendance_view, name="attendance"),
    path("attendance/filter/", views.filter_attendance_api, name="filter_attendance"),
    path("api/attendance/record/", views.attendance_record_api, name="attendance_record_api"),
    path("api/attendance/location-history/", views.attendance_location_history_api, name="attendance_location_history_api"),

    # Documentation.
    path("api/schema/", views.api_schema_view, name="api_schema_view"),
    path("api/schema/yaml/", views.api_schema_yaml_view, name="api_schema_yaml_view"),
    path("api/docs/", views.api_docs_view, name="api_docs_view"),

    # Leave management.
    path("leaves/", views.leave_list, name="leave_list"),
    path("leaves/add/", views.leave_add, name="leave_add"),
    path("leaves/<int:pk>/approve/", views.leave_approve, name="leave_approve"),
    path("leaves/<int:pk>/reject/", views.leave_reject, name="leave_reject"),

    # Reports and admin monitoring.
    path("reports/", views.report_view, name="report_view"),
    path("locations/", views.location_tracking_view, name="location_tracking_view"),
    path("reports/excel/", views.export_excel, name="export_excel"),
    path("reports/pdf/", views.export_pdf, name="export_pdf"),
]
