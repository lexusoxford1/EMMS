"""Report and export views."""

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from EmployeeAttendance.services.reports import (
    attach_invalid_month_message,
    build_excel_report_response,
    build_pdf_report_response,
    get_report_attendances,
)
from EmployeeAttendance.utils.auth import is_admin


@login_required
@user_passes_test(is_admin)
def report_view(request):
    """Render the report table and surface month-format validation feedback."""
    month = request.GET.get("month")
    attendances, invalid_month = get_report_attendances(month)
    attach_invalid_month_message(request, invalid_month)
    return render(request, "report.html", {"attendances": attendances})


@login_required
@user_passes_test(is_admin)
def export_excel(request):
    """Export the filtered attendance rows as an Excel workbook."""
    attendances, _ = get_report_attendances(request.GET.get("month"))
    return build_excel_report_response(attendances)


@login_required
@user_passes_test(is_admin)
def export_pdf(request):
    """Export the filtered attendance rows as a styled PDF report."""
    month = request.GET.get("month")
    attendances, _ = get_report_attendances(month)
    return build_pdf_report_response(attendances, month)


