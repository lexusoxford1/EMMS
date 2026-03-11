from django.urls import path
from . import views

urlpatterns = [
    path("", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),

    path("employees/", views.employee_list, name="employee_list"),
    path("employees/add/", views.employee_add, name="employee_add"),
    path("employees/<int:pk>/toggle-status/", views.employee_toggle_status, name="employee_toggle_status"),

    path("attendance/", views.attendance_view, name="attendance"),
    path('attendance/filter/', views.filter_attendance_api, name='filter_attendance'),

    path("leaves/", views.leave_list, name="leave_list"),
    path("leaves/add/", views.leave_add, name="leave_add"),
    path("leaves/<int:pk>/approve/", views.leave_approve, name="leave_approve"),
    path("leaves/<int:pk>/reject/", views.leave_reject, name="leave_reject"),

    path("reports/", views.report_view, name="report_view"),
    path("reports/excel/", views.export_excel, name="export_excel"),
    path("reports/pdf/", views.export_pdf, name="export_pdf"),
]

