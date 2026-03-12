"""Attendance UI and API views."""

from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from EmployeeAttendance.models import Attendance, AttendanceLocation, Employee
from EmployeeAttendance.utils.location import parse_location_payload, serialize_location_log


@login_required
def attendance_view(request):
    """Render the attendance workspace and preload today's context for the current user."""
    today = timezone.localdate()
    today_records = Attendance.objects.filter(date=today).select_related("employee").order_by("employee__name")

    if request.user.is_superuser:
        context = {
            "record": None,
            "today_records": today_records,
            "my_history": [],
            "my_location_logs": [],
            "is_admin_view": True,
        }
        return render(request, "attendance.html", context)

    employee = get_object_or_404(Employee, user=request.user)
    record, _ = Attendance.objects.get_or_create(employee=employee, date=today)

    if request.method == "POST":
        messages.error(request, "Attendance must now be recorded through the location-tracking API.")
        return redirect("attendance")

    context = {
        "record": record,
        "today_records": today_records,
        "my_history": Attendance.objects.filter(employee=employee).order_by("-date"),
        "my_location_logs": AttendanceLocation.objects.filter(employee=employee).select_related("attendance")[:10],
        "is_admin_view": False,
        "next_step_label": Attendance.next_step_for_record(record)[1] or "Completed",
    }
    return render(request, "attendance.html", context)


@login_required
@require_http_methods(["POST"])
def attendance_record_api(request):
    """Record the next attendance step together with the employee's captured location."""
    if request.user.is_superuser:
        return JsonResponse({"error": "Admin accounts cannot record attendance."}, status=403)

    # Parse and validate the browser payload before touching attendance records.
    payload, error_response = parse_location_payload(request)
    if error_response:
        return error_response

    employee = get_object_or_404(Employee, user=request.user)
    today = timezone.localdate()

    # Lock the row so duplicate clicks cannot skip or reorder attendance steps.
    with transaction.atomic():
        record, _ = Attendance.objects.select_for_update().get_or_create(employee=employee, date=today)
        field_name, label = Attendance.next_step_for_record(record)

        if not field_name:
            return JsonResponse({"error": "Attendance for today is already complete."}, status=400)

        recorded_at = timezone.now()
        setattr(record, field_name, recorded_at)
        record.save(update_fields=[field_name])

        location_log = AttendanceLocation.objects.create(
            attendance=record,
            employee=employee,
            attendance_type=field_name,
            latitude=payload["latitude"],
            longitude=payload["longitude"],
            address=payload["address"],
            recorded_at=recorded_at,
        )

    return JsonResponse(
        {
            "message": f"{label} recorded successfully.",
            "attendance": {
                "date": str(record.date),
                "attendance_type": field_name,
                "attendance_type_label": label,
                "recorded_at": recorded_at.isoformat(),
                "status": record.attendance_status,
                "total_hours": record.total_hours,
            },
            "location": serialize_location_log(location_log),
        },
        status=201,
    )


@login_required
@require_http_methods(["GET"])
def attendance_location_history_api(request):
    """Return location history, narrowing the dataset based on the caller's role."""
    logs = AttendanceLocation.objects.select_related("employee", "attendance")

    if request.user.is_superuser:
        employee_id = request.GET.get("employee_id", "").strip()
        if employee_id:
            logs = logs.filter(employee__employee_id__iexact=employee_id)
    else:
        employee = get_object_or_404(Employee, user=request.user)
        logs = logs.filter(employee=employee)

    date_filter = request.GET.get("date", "").strip()
    if date_filter:
        try:
            parsed_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({"error": "date must be in YYYY-MM-DD format."}, status=400)
        logs = logs.filter(attendance__date=parsed_date)

    data = [serialize_location_log(log) for log in logs[:100]]
    return JsonResponse({"count": len(data), "results": data})


@login_required
@require_http_methods(["GET"])
def filter_attendance_api(request):
    """Provide lightweight filtering for the employee attendance history table."""
    if request.user.is_superuser:
        return JsonResponse({"success": False, "error": "Admin accounts cannot use this endpoint."}, status=403)

    employee = get_object_or_404(Employee, user=request.user)
    search = request.GET.get("search", "").strip()
    month = request.GET.get("month", "").strip()
    status = request.GET.get("status", "").strip()

    records = Attendance.objects.filter(employee=employee).order_by("-date")
    if search:
        records = records.filter(date__icontains=search)

    if month:
        try:
            month_number = int(month)
        except ValueError:
            return JsonResponse({"success": False, "error": "Month filter must be numeric."}, status=400)
        records = records.filter(date__month=month_number)

    data = []
    for record in records[:100]:
        record_status = record.attendance_status if record.total_hours else "Incomplete"
        if status and status != record_status:
            continue

        data.append(
            {
                "date": record.date.strftime("%Y-%m-%d"),
                "morning_in": record.morning_in.strftime("%I:%M %p") if record.morning_in else "-",
                "morning_out": record.morning_out.strftime("%I:%M %p") if record.morning_out else "-",
                "afternoon_in": record.afternoon_in.strftime("%I:%M %p") if record.afternoon_in else "-",
                "afternoon_out": record.afternoon_out.strftime("%I:%M %p") if record.afternoon_out else "-",
                "total_hours": str(record.total_hours),
                "status": record_status,
            }
        )

    return JsonResponse({"success": True, "records": data})


