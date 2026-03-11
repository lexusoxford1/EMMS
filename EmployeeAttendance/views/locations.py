"""Admin location-monitoring views."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils import timezone

from EmployeeAttendance.models import AttendanceLocation
from EmployeeAttendance.utils.auth import is_admin


@login_required
@user_passes_test(is_admin)
def location_tracking_view(request):
    employee_id = request.GET.get("employee_id", "").strip()
    attendance_type = request.GET.get("attendance_type", "").strip()
    today = timezone.localdate()

    logs = AttendanceLocation.objects.select_related("employee", "attendance").filter(attendance__date=today)
    if employee_id:
        logs = logs.filter(employee__employee_id__icontains=employee_id)

    valid_attendance_types = {choice[0] for choice in AttendanceLocation.ATTENDANCE_TYPE_CHOICES}
    if attendance_type:
        if attendance_type in valid_attendance_types:
            logs = logs.filter(attendance_type=attendance_type)
        else:
            messages.error(request, "Invalid attendance type filter.")
            attendance_type = ""

    logs = list(logs.order_by("-recorded_at")[:100])
    map_points = [
        {
            "employee_id": log.employee.employee_id,
            "employee_name": log.employee.name,
            "attendance_type": log.get_attendance_type_display(),
            "attendance_date": str(log.attendance.date),
            "recorded_at": log.recorded_at.isoformat(),
            "latitude": float(log.latitude),
            "longitude": float(log.longitude),
            "address": log.address,
        }
        for log in logs
    ]

    context = {
        "location_logs": logs,
        "location_map_points": map_points,
        "employee_id_query": employee_id,
        "attendance_type_query": attendance_type,
        "attendance_type_choices": AttendanceLocation.ATTENDANCE_TYPE_CHOICES,
        "monitoring_date": today,
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
    }
    return render(request, "location_tracking.html", context)
