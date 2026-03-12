"""Dashboard aggregation helpers."""

from datetime import timedelta

from django.utils import timezone

from EmployeeAttendance.models import Attendance, Employee, LeaveRequest


def build_dashboard_context(user):
    """Assemble admin and employee dashboard metrics in one place."""
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
        if attendance.is_undertime:
            undertime_count += 1
        elif attendance.is_overtime:
            overtime_count += 1
        else:
            completed_count += 1

    total_hours_today = round(total_hours_today, 2)
    avg_hours_today = round(total_hours_today / present_today, 2) if present_today else 0
    attendance_rate_today = round((present_today / employee_count) * 100, 1) if employee_count else 0

    divisor = present_today or 1
    undertime_percent = round((undertime_count / divisor) * 100, 1) if present_today else 0
    completed_percent = round((completed_count / divisor) * 100, 1) if present_today else 0
    overtime_percent = round((overtime_count / divisor) * 100, 1) if present_today else 0

    undertime_alerts = sorted(
        [record for record in today_records if record.is_undertime],
        key=lambda item: item.total_hours,
    )[:5]
    overtime_alerts = sorted(
        [record for record in today_records if record.is_overtime],
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
            if day_record.is_undertime:
                day_undertime += 1
            elif day_record.is_overtime:
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
        row = department_map.setdefault(
            department_name,
            {
                "department": department_name,
                "present": 0,
                "total_hours": 0,
                "undertime": 0,
                "completed": 0,
                "overtime": 0,
            },
        )

        row["present"] += 1
        row["total_hours"] += attendance.total_hours
        if attendance.is_undertime:
            row["undertime"] += 1
        elif attendance.is_overtime:
            row["overtime"] += 1
        else:
            row["completed"] += 1

    department_rows = []
    for row in department_map.values():
        row["total_hours"] = round(row["total_hours"], 2)
        row["avg_hours"] = round(row["total_hours"] / row["present"], 2) if row["present"] else 0
        row["completion_rate"] = round((row["completed"] / row["present"]) * 100, 1) if row["present"] else 0
        department_rows.append(row)
    department_rows.sort(key=lambda item: item["present"], reverse=True)

    employee = None
    if not user.is_superuser:
        employee = Employee.objects.filter(user=user).first()

    my_total_days = 0
    my_total_hours = 0
    my_avg_hours = 0
    my_undertime_days = 0
    my_completed_days = 0
    my_overtime_days = 0
    my_completion_rate = 0
    my_best_day = None
    my_last7_trend = []

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
            if record.is_undertime:
                my_undertime_days += 1
            elif record.is_overtime:
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
            elif day_hours >= Attendance.OVERTIME_HOURS:
                day_status = "Overtime"
            else:
                day_status = "Completed"

            my_last7_trend.append({"date": day, "hours": day_hours, "status": day_status})

    return {
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
