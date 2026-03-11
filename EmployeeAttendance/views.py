import json
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db import OperationalError, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .forms import EmployeeForm, LeaveRequestForm
from .models import Attendance, AttendanceLocation, Employee, LeaveRequest


def is_admin(user):
    return user.is_superuser


def _parse_location_payload(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({"error": "Invalid JSON payload."}, status=400)

    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    address = (payload.get("address") or "").strip()

    if latitude in (None, "") or longitude in (None, ""):
        return None, JsonResponse({"error": "Latitude and longitude are required."}, status=400)

    try:
        latitude = Decimal(str(latitude))
        longitude = Decimal(str(longitude))
    except (InvalidOperation, ValueError):
        return None, JsonResponse({"error": "Latitude and longitude must be numeric values."}, status=400)

    if latitude < Decimal("-90") or latitude > Decimal("90"):
        return None, JsonResponse({"error": "Latitude must be between -90 and 90."}, status=400)

    if longitude < Decimal("-180") or longitude > Decimal("180"):
        return None, JsonResponse({"error": "Longitude must be between -180 and 180."}, status=400)

    if len(address) > 255:
        return None, JsonResponse({"error": "Address must be 255 characters or fewer."}, status=400)

    return {
        "latitude": latitude,
        "longitude": longitude,
        "address": address,
    }, None


def _serialize_location_log(log):
    return {
        "id": log.id,
        "employee_id": log.employee.employee_id,
        "employee_name": log.employee.name,
        "attendance_date": str(log.attendance.date),
        "attendance_type": log.attendance_type,
        "attendance_type_label": log.get_attendance_type_display(),
        "latitude": float(log.latitude),
        "longitude": float(log.longitude),
        "address": log.address,
        "recorded_at": log.recorded_at.isoformat(),
    }



DOCS_YAML_PATH = Path(settings.BASE_DIR) / "docs" / "emms-attendance-api.yaml"
def _build_api_schema(request):
    base_url = request.build_absolute_uri("/").rstrip("/")

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "EMMS Attendance Location API",
            "version": "1.0.0",
            "description": (
                "API documentation for the Employee Management and Monitoring System attendance "
                "location tracking flow. This documentation is rendered through ReDoc using a "
                "locally served OpenAPI schema, so it demonstrates the full API design without "
                "requiring any external API key."
            ),
        },
        "servers": [
            {
                "url": base_url,
                "description": "Current Django application host",
            }
        ],
        "tags": [
            {
                "name": "Attendance",
                "description": "Employee attendance recording with strict step validation and GPS capture.",
            },
            {
                "name": "Location History",
                "description": "Role-based access to recorded attendance location logs.",
            },
        ],
        "paths": {
            "/api/attendance/record/": {
                "post": {
                    "tags": ["Attendance"],
                    "summary": "Record the next valid attendance step with location",
                    "security": [{"cookieAuth": []}],
                    "description": (
                        "Frontend flow: the browser captures geolocation with navigator.geolocation, "
                        "then sends latitude, longitude, and optional address to this endpoint. "
                        "The backend validates the request, determines the next valid step in the "
                        "sequence Morning In -> Morning Out -> Afternoon In -> Afternoon Out, saves "
                        "the attendance timestamp, and creates a linked AttendanceLocation record. Authentication is required, and admin accounts are blocked from using this endpoint."
                    ),
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/AttendanceRecordRequest"},
                                "examples": {
                                    "employeeLocation": {
                                        "summary": "Employee geolocation payload",
                                        "value": {
                                            "latitude": 14.5995,
                                            "longitude": 120.9842,
                                            "address": "Manila, Philippines",
                                        },
                                    }
                                },
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Attendance step recorded and location log saved.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/AttendanceRecordSuccessResponse"},
                                    "examples": {
                                        "morningInSuccess": {
                                            "summary": "Successful Morning In response",
                                            "value": {
                                                "message": "Morning In recorded successfully.",
                                                "attendance": {
                                                    "date": "2026-03-11",
                                                    "attendance_type": "morning_in",
                                                    "attendance_type_label": "Morning In",
                                                    "recorded_at": "2026-03-11T08:01:22+08:00",
                                                    "status": "Undertime",
                                                    "total_hours": 0,
                                                },
                                                "location": {
                                                    "id": 15,
                                                    "employee_id": "EMP-0001",
                                                    "employee_name": "Jane Doe",
                                                    "attendance_date": "2026-03-11",
                                                    "attendance_type": "morning_in",
                                                    "attendance_type_label": "Morning In",
                                                    "latitude": 14.5995,
                                                    "longitude": 120.9842,
                                                    "address": "Manila, Philippines",
                                                    "recorded_at": "2026-03-11T08:01:22+08:00",
                                                },
                                            },
                                        }
                                    },
                                }
                            },
                        },
                        "400": {
                            "description": "Validation failed or the attendance step is not allowed.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                                    "examples": {
                                        "invalidCoordinates": {
                                            "summary": "Missing coordinates",
                                            "value": {"error": "Latitude and longitude are required."},
                                        },
                                        "alreadyComplete": {
                                            "summary": "Attendance already complete",
                                            "value": {"error": "Attendance for today is already complete."},
                                        },
                                    },
                                }
                            },
                        },
                        "403": {
                            "description": "The authenticated user is not allowed to record attendance.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                                    "examples": {
                                        "adminBlocked": {
                                            "summary": "Admin account blocked",
                                            "value": {"error": "Admin accounts cannot record attendance."},
                                        }
                                    },
                                }
                            },
                        },
                    },
                }
            },
            "/api/attendance/location-history/": {
                "get": {
                    "tags": ["Location History"],
                    "summary": "Get attendance location logs",
                    "security": [{"cookieAuth": []}],
                    "description": (
                        "Returns recorded attendance locations. Employees only receive their own logs. "
                        "Admins can review broader data and optionally filter by employee ID and date. Session authentication is required for access."
                    ),
                    "parameters": [
                        {
                            "name": "employee_id",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string", "example": "EMP-0001"},
                            "description": "Admin-only filter for a specific employee ID.",
                        },
                        {
                            "name": "date",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string", "format": "date", "example": "2026-03-11"},
                            "description": "Optional date filter in YYYY-MM-DD format.",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Location history returned successfully.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/LocationHistoryResponse"},
                                    "examples": {
                                        "historySuccess": {
                                            "summary": "Location history response",
                                            "value": {
                                                "count": 1,
                                                "results": [
                                                    {
                                                        "id": 15,
                                                        "employee_id": "EMP-0001",
                                                        "employee_name": "Jane Doe",
                                                        "attendance_date": "2026-03-11",
                                                        "attendance_type": "morning_in",
                                                        "attendance_type_label": "Morning In",
                                                        "latitude": 14.5995,
                                                        "longitude": 120.9842,
                                                        "address": "Manila, Philippines",
                                                        "recorded_at": "2026-03-11T08:01:22+08:00",
                                                    }
                                                ],
                                            },
                                        }
                                    },
                                }
                            },
                        },
                        "400": {
                            "description": "Invalid query parameter value.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                                    "examples": {
                                        "invalidDate": {
                                            "summary": "Bad date filter",
                                            "value": {"error": "date must be in YYYY-MM-DD format."},
                                        }
                                    },
                                }
                            },
                        },
                    },
                }
            },
        },
        "components": {
            "schemas": {
                "AttendanceRecordRequest": {
                    "type": "object",
                    "required": ["latitude", "longitude"],
                    "properties": {
                        "latitude": {
                            "type": "number",
                            "format": "float",
                            "minimum": -90,
                            "maximum": 90,
                            "description": "GPS latitude captured from the browser.",
                        },
                        "longitude": {
                            "type": "number",
                            "format": "float",
                            "minimum": -180,
                            "maximum": 180,
                            "description": "GPS longitude captured from the browser.",
                        },
                        "address": {
                            "type": "string",
                            "maxLength": 255,
                            "description": "Optional readable address sent by the client if available.",
                        },
                    },
                },
                "AttendanceSummary": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "format": "date"},
                        "attendance_type": {"type": "string", "enum": ["morning_in", "morning_out", "afternoon_in", "afternoon_out"]},
                        "attendance_type_label": {"type": "string"},
                        "recorded_at": {"type": "string", "format": "date-time"},
                        "status": {"type": "string"},
                        "total_hours": {"type": "number"},
                    },
                },
                "LocationLog": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "employee_id": {"type": "string"},
                        "employee_name": {"type": "string"},
                        "attendance_date": {"type": "string", "format": "date"},
                        "attendance_type": {"type": "string", "enum": ["morning_in", "morning_out", "afternoon_in", "afternoon_out"]},
                        "attendance_type_label": {"type": "string"},
                        "latitude": {"type": "number", "format": "float"},
                        "longitude": {"type": "number", "format": "float"},
                        "address": {"type": "string"},
                        "recorded_at": {"type": "string", "format": "date-time"},
                    },
                },
                "AttendanceRecordSuccessResponse": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "attendance": {"$ref": "#/components/schemas/AttendanceSummary"},
                        "location": {"$ref": "#/components/schemas/LocationLog"},
                    },
                },
                "LocationHistoryResponse": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer"},
                        "results": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/LocationLog"},
                        },
                    },
                },
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string"},
                    },
                },
            }
        },
        "x-emms-process-flow": [
            "Employee opens the Attendance page and clicks the next step button.",
            "attendance.js requests browser geolocation and sends latitude, longitude, and optional address using fetch with CSRF.",
            "Django validates authentication, JSON structure, coordinate ranges, and the strict attendance order.",
            "The Attendance record is updated with the correct timestamp for the next step.",
            "An AttendanceLocation row is created and linked to both the employee and the attendance record.",
            "Admin users monitor the resulting logs on the Locations page and through the location history API.",
        ],
        "x-emms-validation-rules": [
            "Session authentication is required.",
            "Admin accounts cannot use the record attendance endpoint.",
            "Latitude must be between -90 and 90.",
            "Longitude must be between -180 and 180.",
            "Address is optional and limited to 255 characters.",
            "Attendance steps must follow Morning In, Morning Out, Afternoon In, Afternoon Out.",
        ],
    }


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            existing_user = User.objects.filter(username=username).first()
            if existing_user and existing_user.check_password(password) and not existing_user.is_active:
                messages.error(request, "Your account is non-active. Please contact your administrator.")
            else:
                messages.error(request, "Invalid username or password")

    return render(request, "login.html")


def logout_view(request):
    try:
        logout(request)
        return redirect("login")
    except OperationalError:
        response = redirect("login")
        response.delete_cookie(settings.SESSION_COOKIE_NAME)
        response.delete_cookie(settings.CSRF_COOKIE_NAME)
        return response


@login_required
def dashboard(request):
    employee_count = Employee.objects.count()
    today = timezone.localdate()
    month_start = today.replace(day=1)

    today_records = list(
        Attendance.objects.filter(date=today)
        .select_related("employee")
        .order_by("employee__name")
    )
    present_today = len(today_records)

    pending_leaves = LeaveRequest.objects.filter(status="Pending").count()
    approved_leaves = LeaveRequest.objects.filter(status="Approved").count()
    rejected_leaves = LeaveRequest.objects.filter(status="Rejected").count()

    month_leaves = LeaveRequest.objects.filter(leave_date__year=today.year, leave_date__month=today.month)
    month_pending_leaves = month_leaves.filter(status="Pending").count()
    month_approved_leaves = month_leaves.filter(status="Approved").count()
    month_rejected_leaves = month_leaves.filter(status="Rejected").count()

    undertime_count = 0
    completed_count = 0
    overtime_count = 0

    total_hours_today = 0
    for attendance in today_records:
        total_hours_today += attendance.total_hours
        if attendance.total_hours < Attendance.REQUIRED_HOURS:
            undertime_count += 1
        elif attendance.total_hours > Attendance.REQUIRED_HOURS:
            overtime_count += 1
        else:
            completed_count += 1

    total_hours_today = round(total_hours_today, 2)
    avg_hours_today = round(total_hours_today / present_today, 2) if present_today else 0
    attendance_rate_today = round((present_today / employee_count) * 100, 1) if employee_count else 0

    divisor = present_today if present_today else 1
    undertime_percent = round((undertime_count / divisor) * 100, 1) if present_today else 0
    completed_percent = round((completed_count / divisor) * 100, 1) if present_today else 0
    overtime_percent = round((overtime_count / divisor) * 100, 1) if present_today else 0

    undertime_alerts = sorted(
        [record for record in today_records if record.total_hours < Attendance.REQUIRED_HOURS],
        key=lambda item: item.total_hours,
    )[:5]
    overtime_alerts = sorted(
        [record for record in today_records if record.total_hours > Attendance.REQUIRED_HOURS],
        key=lambda item: item.total_hours,
        reverse=True,
    )[:5]

    trend_rows = []
    for days_ago in range(6, -1, -1):
        trend_date = today - timedelta(days=days_ago)
        day_records = list(Attendance.objects.filter(date=trend_date))

        day_undertime = 0
        day_completed = 0
        day_overtime = 0
        for day_record in day_records:
            if day_record.total_hours < Attendance.REQUIRED_HOURS:
                day_undertime += 1
            elif day_record.total_hours > Attendance.REQUIRED_HOURS:
                day_overtime += 1
            else:
                day_completed += 1

        trend_rows.append(
            {
                "date": trend_date,
                "undertime": day_undertime,
                "completed": day_completed,
                "overtime": day_overtime,
            }
        )

    department_map = {}
    for attendance in today_records:
        department_name = attendance.employee.department or "Unassigned"
        if department_name not in department_map:
            department_map[department_name] = {
                "department": department_name,
                "present": 0,
                "total_hours": 0,
                "undertime": 0,
                "completed": 0,
                "overtime": 0,
            }

        row = department_map[department_name]
        row["present"] += 1
        row["total_hours"] += attendance.total_hours
        if attendance.total_hours < Attendance.REQUIRED_HOURS:
            row["undertime"] += 1
        elif attendance.total_hours > Attendance.REQUIRED_HOURS:
            row["overtime"] += 1
        else:
            row["completed"] += 1

    department_rows = []
    for row in department_map.values():
        row["total_hours"] = round(row["total_hours"], 2)
        row["avg_hours"] = round(row["total_hours"] / row["present"], 2) if row["present"] else 0
        row["completion_rate"] = round((row["completed"] / row["present"]) * 100, 1) if row["present"] else 0
        department_rows.append(row)
    department_rows = sorted(department_rows, key=lambda item: item["present"], reverse=True)

    employee = None
    my_total_days = 0
    my_total_hours = 0
    my_avg_hours = 0
    my_undertime_days = 0
    my_completed_days = 0
    my_overtime_days = 0
    my_completion_rate = 0
    my_best_day = None
    my_last7_trend = []

    if not request.user.is_superuser:
        try:
            employee = Employee.objects.get(user=request.user)
        except Employee.DoesNotExist:
            employee = None

    if employee:
        my_month_records = list(
            Attendance.objects.filter(
                employee=employee,
                date__year=today.year,
                date__month=today.month,
            ).order_by("-date")
        )

        my_total_days = len(my_month_records)
        my_total_hours = round(sum(record.total_hours for record in my_month_records), 2)
        my_avg_hours = round(my_total_hours / my_total_days, 2) if my_total_days else 0

        for record in my_month_records:
            if record.total_hours < Attendance.REQUIRED_HOURS:
                my_undertime_days += 1
            elif record.total_hours > Attendance.REQUIRED_HOURS:
                my_overtime_days += 1
            else:
                my_completed_days += 1

        my_completion_rate = round((my_completed_days / my_total_days) * 100, 1) if my_total_days else 0
        my_best_day = max(my_month_records, key=lambda item: item.total_hours) if my_month_records else None

        for days_ago in range(6, -1, -1):
            day = today - timedelta(days=days_ago)
            day_record = Attendance.objects.filter(employee=employee, date=day).first()
            day_hours = day_record.total_hours if day_record else 0

            if day_hours < Attendance.REQUIRED_HOURS:
                day_status = "Undertime"
            elif day_hours > Attendance.REQUIRED_HOURS:
                day_status = "Overtime"
            else:
                day_status = "Completed"

            my_last7_trend.append({"date": day, "hours": day_hours, "status": day_status})

    context = {
        "employee_count": employee_count,
        "present_today": present_today,
        "today_attendance": present_today,
        "pending_leaves": pending_leaves,
        "approved_leaves": approved_leaves,
        "rejected_leaves": rejected_leaves,
        "month_start": month_start,
        "month_pending_leaves": month_pending_leaves,
        "month_approved_leaves": month_approved_leaves,
        "month_rejected_leaves": month_rejected_leaves,
        "undertime_count": undertime_count,
        "completed_count": completed_count,
        "overtime_count": overtime_count,
        "undertime_percent": undertime_percent,
        "completed_percent": completed_percent,
        "overtime_percent": overtime_percent,
        "attendance_rate_today": attendance_rate_today,
        "total_hours_today": total_hours_today,
        "avg_hours_today": avg_hours_today,
        "undertime_alerts": undertime_alerts,
        "overtime_alerts": overtime_alerts,
        "trend_rows": trend_rows,
        "department_rows": department_rows,
        "admin_trend_labels": [row["date"].strftime("%b %d") for row in trend_rows],
        "admin_trend_totals": [row["undertime"] + row["completed"] + row["overtime"] for row in trend_rows],
        "admin_status_mix": [undertime_count, completed_count, overtime_count],
        "my_total_days": my_total_days,
        "my_total_hours": my_total_hours,
        "my_avg_hours": my_avg_hours,
        "my_undertime_days": my_undertime_days,
        "my_completed_days": my_completed_days,
        "my_overtime_days": my_overtime_days,
        "my_completion_rate": my_completion_rate,
        "my_best_day": my_best_day,
        "my_last7_trend": my_last7_trend,
        "employee_trend_labels": [row["date"].strftime("%b %d") for row in my_last7_trend],
        "employee_trend_hours": [row["hours"] for row in my_last7_trend],
        "employee_status_mix": [my_undertime_days, my_completed_days, my_overtime_days],
    }
    return render(request, "dashboard.html", context)


@login_required
@user_passes_test(is_admin)
def employee_list(request):
    employee_id_query = request.GET.get("employee_id", "").strip()

    employees = Employee.objects.select_related("user").all().order_by("employee_id")
    if employee_id_query:
        employees = employees.filter(employee_id__icontains=employee_id_query)

    context = {
        "employees": employees,
        "employee_id_query": employee_id_query,
    }
    return render(request, "employee_list.html", context)


@login_required
@user_passes_test(is_admin)
def employee_add(request):
    if request.method == "POST":
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Employee added successfully")
            return redirect("employee_list")
    else:
        form = EmployeeForm()

    return render(request, "employee_form.html", {"form": form})


@login_required
@user_passes_test(is_admin)
def employee_toggle_status(request, pk):
    if request.method != "POST":
        return redirect("employee_list")

    employee = get_object_or_404(Employee, pk=pk)

    if employee.status == Employee.STATUS_ACTIVE:
        employee.status = Employee.STATUS_NON_ACTIVE
        message = f"{employee.name} is now Non-Active and cannot log in."
    else:
        employee.status = Employee.STATUS_ACTIVE
        message = f"{employee.name} is now Active and can log in."

    employee.save()

    if employee.user:
        employee.user.is_active = employee.status == Employee.STATUS_ACTIVE
        employee.user.save(update_fields=["is_active"])

    messages.success(request, message)
    return redirect("employee_list")


@login_required
def attendance_view(request):
    if request.user.is_superuser:
        today = timezone.localdate()
        today_records = Attendance.objects.filter(date=today).select_related("employee").order_by("employee__name")

        context = {
            "record": None,
            "today_records": today_records,
            "my_history": [],
            "my_location_logs": [],
            "is_admin_view": True,
        }
        return render(request, "attendance.html", context)

    employee = get_object_or_404(Employee, user=request.user)
    today = timezone.localdate()

    record, created = Attendance.objects.get_or_create(
        employee=employee,
        date=today,
    )

    if request.method == "POST":
        messages.error(request, "Attendance must now be recorded through the location-tracking API.")
        return redirect("attendance")

    today_records = Attendance.objects.filter(date=today).select_related("employee").order_by("employee__name")
    my_history = Attendance.objects.filter(employee=employee).order_by("-date")
    my_location_logs = AttendanceLocation.objects.filter(employee=employee).select_related("attendance")[:10]
    next_step_field, next_step_label = Attendance.next_step_for_record(record)

    context = {
        "record": record,
        "today_records": today_records,
        "my_history": my_history,
        "my_location_logs": my_location_logs,
        "is_admin_view": False,
        "next_step_label": next_step_label or "Completed",
    }
    return render(request, "attendance.html", context)


@login_required
@require_http_methods(["POST"])
def attendance_record_api(request):
    if request.user.is_superuser:
        return JsonResponse({"error": "Admin accounts cannot record attendance."}, status=403)

    payload, error_response = _parse_location_payload(request)
    if error_response:
        return error_response

    employee = get_object_or_404(Employee, user=request.user)
    today = timezone.localdate()

    with transaction.atomic():
        record, created = Attendance.objects.select_for_update().get_or_create(employee=employee, date=today)
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
            "location": _serialize_location_log(location_log),
        },
        status=201,
    )


@login_required
@require_http_methods(["GET"])
def attendance_location_history_api(request):
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

    data = [_serialize_location_log(log) for log in logs[:100]]
    return JsonResponse({"count": len(data), "results": data})
@login_required
@require_http_methods(["GET"])
def filter_attendance_api(request):
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

        data.append({
            "date": record.date.strftime("%Y-%m-%d"),
            "morning_in": record.morning_in.strftime("%I:%M %p") if record.morning_in else "-",
            "morning_out": record.morning_out.strftime("%I:%M %p") if record.morning_out else "-",
            "afternoon_in": record.afternoon_in.strftime("%I:%M %p") if record.afternoon_in else "-",
            "afternoon_out": record.afternoon_out.strftime("%I:%M %p") if record.afternoon_out else "-",
            "total_hours": str(record.total_hours),
            "status": record_status,
        })

    return JsonResponse({"success": True, "records": data})

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


@login_required
def leave_list(request):
    if request.user.is_superuser:
        leaves = LeaveRequest.objects.all().order_by("-created_at")
    else:
        employee = get_object_or_404(Employee, user=request.user)
        leaves = LeaveRequest.objects.filter(employee=employee).order_by("-created_at")

    return render(request, "leave_list.html", {"leaves": leaves})


@login_required
def leave_add(request):
    employee = get_object_or_404(Employee, user=request.user)

    if request.method == "POST":
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = employee
            leave.save()
            messages.success(request, "Leave request submitted successfully")
            return redirect("leave_list")
    else:
        form = LeaveRequestForm()

    return render(request, "leave_form.html", {"form": form})


@login_required
@user_passes_test(is_admin)
def leave_approve(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    leave.status = "Approved"
    leave.save()
    messages.success(request, "Leave request approved")
    return redirect("leave_list")


@login_required
@user_passes_test(is_admin)
def leave_reject(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    leave.status = "Rejected"
    leave.save()
    messages.success(request, "Leave request rejected")
    return redirect("leave_list")


@login_required
@user_passes_test(is_admin)
def report_view(request):
    month = request.GET.get("month")
    attendances = Attendance.objects.all().select_related("employee").order_by("-date")

    if month:
        try:
            year, month_num = map(int, month.split("-"))
            attendances = attendances.filter(date__year=year, date__month=month_num)
        except ValueError:
            messages.error(request, "Invalid month format")

    return render(request, "report.html", {"attendances": attendances})


@login_required
@user_passes_test(is_admin)
def export_excel(request):
    month = request.GET.get("month")
    attendances = Attendance.objects.all().select_related("employee").order_by("-date")

    if month:
        try:
            year, month_num = map(int, month.split("-"))
            attendances = attendances.filter(date__year=year, date__month=month_num)
        except ValueError:
            pass

    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance Report"

    ws.append([
        "Date",
        "Employee ID",
        "Name",
        "Department",
        "Morning In",
        "Morning Out",
        "Afternoon In",
        "Afternoon Out",
        "Total Hours"
    ])

    for attendance in attendances:
        ws.append([
            str(attendance.date),
            attendance.employee.employee_id,
            attendance.employee.name,
            attendance.employee.department,
            attendance.morning_in.strftime("%Y-%m-%d %H:%M:%S") if attendance.morning_in else "",
            attendance.morning_out.strftime("%Y-%m-%d %H:%M:%S") if attendance.morning_out else "",
            attendance.afternoon_in.strftime("%Y-%m-%d %H:%M:%S") if attendance.afternoon_in else "",
            attendance.afternoon_out.strftime("%Y-%m-%d %H:%M:%S") if attendance.afternoon_out else "",
            attendance.total_hours,
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="attendance_report.xlsx"'
    wb.save(response)
    return response


@login_required
@user_passes_test(is_admin)
def export_pdf(request):
    month = request.GET.get("month")
    attendances = Attendance.objects.all().select_related("employee").order_by("-date")

    if month:
        try:
            year, month_num = map(int, month.split("-"))
            attendances = attendances.filter(date__year=year, date__month=month_num)
        except ValueError:
            pass

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="attendance_report.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(letter),
        leftMargin=0.45 * inch,
        rightMargin=0.45 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.45 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    title_style.fontName = "Helvetica-Bold"
    title_style.fontSize = 18
    title_style.leading = 22
    title_style.textColor = colors.HexColor("#143d2f")
    title_style.alignment = 0

    meta_style = styles["BodyText"]
    meta_style.fontName = "Helvetica"
    meta_style.fontSize = 9
    meta_style.leading = 12
    meta_style.textColor = colors.HexColor("#52635a")

    table_data = [[
        "Date",
        "Employee ID",
        "Name",
        "Department",
        "Morning In",
        "Morning Out",
        "Afternoon In",
        "Afternoon Out",
        "Total Hours",
    ]]

    for attendance in attendances:
        table_data.append([
            str(attendance.date),
            attendance.employee.employee_id,
            attendance.employee.name,
            attendance.employee.department,
            attendance.morning_in.strftime("%Y-%m-%d %H:%M:%S") if attendance.morning_in else "-",
            attendance.morning_out.strftime("%Y-%m-%d %H:%M:%S") if attendance.morning_out else "-",
            attendance.afternoon_in.strftime("%Y-%m-%d %H:%M:%S") if attendance.afternoon_in else "-",
            attendance.afternoon_out.strftime("%Y-%m-%d %H:%M:%S") if attendance.afternoon_out else "-",
            str(attendance.total_hours),
        ])

    column_widths = [
        0.75 * inch,
        0.95 * inch,
        1.15 * inch,
        1.05 * inch,
        1.18 * inch,
        1.18 * inch,
        1.18 * inch,
        1.18 * inch,
        0.65 * inch,
    ]
    scale = doc.width / sum(column_widths)
    column_widths = [width * scale for width in column_widths]

    report_table = Table(table_data, colWidths=column_widths, repeatRows=1)
    report_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#176b4d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f7fbf8"), colors.white]),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#1e2d25")),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#d4e1d8")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (-1, 1), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
    ]))

    meta_bits = []
    if month:
        meta_bits.append(f"Month filter: {month}")
    meta_bits.append(f"Rows: {len(table_data) - 1}")

    story = [
        Paragraph("Attendance Report", title_style),
        Spacer(1, 0.12 * inch),
        Paragraph(" | ".join(meta_bits), meta_style),
        Spacer(1, 0.2 * inch),
        report_table,
    ]

    doc.build(story)
    return response

@login_required
@user_passes_test(is_admin)
def api_schema_view(request):
    return JsonResponse(_build_api_schema(request), json_dumps_params={"indent": 2})


@login_required
@user_passes_test(is_admin)
def api_schema_yaml_view(request):
    if not DOCS_YAML_PATH.exists():
        return HttpResponse("OpenAPI YAML file not found.", status=404, content_type="text/plain")

    return HttpResponse(DOCS_YAML_PATH.read_text(encoding="utf-8"), content_type="application/yaml")


@login_required
@user_passes_test(is_admin)
def api_docs_view(request):
    context = {
        "schema_url": request.build_absolute_uri("/api/schema/"),
        "yaml_url": request.build_absolute_uri("/api/schema/yaml/"),
        "record_endpoint": request.build_absolute_uri("/api/attendance/record/"),
        "history_endpoint": request.build_absolute_uri("/api/attendance/location-history/"),
    }
    return render(request, "api_docs.html", context)






