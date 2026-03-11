from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.core.paginator import Paginator
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from .forms import EmployeeForm, LeaveRequestForm
from .models import Attendance, Employee, LeaveRequest

def is_admin(user):
    return user.is_superuser

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
    logout(request)
    return redirect("login")


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
        "my_total_days": my_total_days,
        "my_total_hours": my_total_hours,
        "my_avg_hours": my_avg_hours,
        "my_undertime_days": my_undertime_days,
        "my_completed_days": my_completed_days,
        "my_overtime_days": my_overtime_days,
        "my_completion_rate": my_completion_rate,
        "my_best_day": my_best_day,
        "my_last7_trend": my_last7_trend,
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
            "is_admin_view": True,
        }
        return render(request, "attendance.html", context)

    employee = get_object_or_404(Employee, user=request.user)
    today = timezone.localdate()

    record, created = Attendance.objects.get_or_create(
        employee=employee,
        date=today
    )

    if request.method == "POST":
        now = timezone.now()

        if not record.morning_in:
            record.morning_in = now
            messages.success(request, "Morning time in recorded")
        elif not record.morning_out:
            record.morning_out = now
            messages.success(request, "Morning time out recorded")
        elif not record.afternoon_in:
            record.afternoon_in = now
            messages.success(request, "Afternoon time in recorded")
        elif not record.afternoon_out:
            record.afternoon_out = now
            messages.success(request, "Afternoon time out recorded")
        else:
            messages.warning(request, "Attendance for today is already complete")

        record.save()
        return redirect("attendance")

    today_records = Attendance.objects.filter(date=today).select_related("employee").order_by("employee__name")
    
    all_history = Attendance.objects.filter(employee=employee).order_by("-date")
    
    paginator = Paginator(all_history, 10)
    page_number = request.GET.get('page', 1)
    my_history = paginator.get_page(page_number)
    
    today_week = today - timedelta(days=today.weekday())
    week_records = Attendance.objects.filter(
        employee=employee,
        date__gte=today_week,
        date__lte=today
    )
    
    month_records = Attendance.objects.filter(
        employee=employee,
        date__year=today.year,
        date__month=today.month
    )
    
    def get_working_days_count(year, month):
        import calendar
        from datetime import date
        
        num_days = calendar.monthrange(year, month)[1]
        working_days = 0
        
        for day in range(1, num_days + 1):
            check_date = date(year, month, day)
            if check_date.weekday() < 5: 
                working_days += 1
        
        return working_days
    
    month_overtime = 0
    month_undertime = 0
    month_present = 0
    
    for record in month_records:
        if record.morning_in or record.afternoon_in:
            month_present += 1
        
        if hasattr(record, 'total_hours'):
            if record.total_hours > 8:  
                month_overtime += 1
            elif record.total_hours < 8 and record.total_hours > 0:
                month_undertime += 1
    
    context = {
        "record": record,
        "today_records": today_records,
        "my_history": my_history,
        "is_admin_view": False,
        "week_present": week_records.filter(
            morning_in__isnull=False
        ).count(),
        "week_total": 5,  
        "month_present": month_present,
        "month_total": get_working_days_count(today.year, today.month),
        "month_overtime": month_overtime,
        "late_count": month_undertime,
    }
    return render(request, "attendance.html", context)


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

    for a in attendances:
        ws.append([
            str(a.date),
            a.employee.employee_id,
            a.employee.name,
            a.employee.department,
            a.morning_in.strftime("%Y-%m-%d %H:%M:%S") if a.morning_in else "",
            a.morning_out.strftime("%Y-%m-%d %H:%M:%S") if a.morning_out else "",
            a.afternoon_in.strftime("%Y-%m-%d %H:%M:%S") if a.afternoon_in else "",
            a.afternoon_out.strftime("%Y-%m-%d %H:%M:%S") if a.afternoon_out else "",
            a.total_hours,
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

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    y = height - 40
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Monthly Attendance Report")
    y -= 30

    p.setFont("Helvetica", 10)
    for a in attendances:
        line = (
            f"{a.date} | {a.employee.employee_id} | {a.employee.name} | "
            f"AM In: {a.morning_in.strftime('%H:%M') if a.morning_in else '-'} | "
            f"AM Out: {a.morning_out.strftime('%H:%M') if a.morning_out else '-'} | "
            f"PM In: {a.afternoon_in.strftime('%H:%M') if a.afternoon_in else '-'} | "
            f"PM Out: {a.afternoon_out.strftime('%H:%M') if a.afternoon_out else '-'} | "
            f"Hours: {a.total_hours}"
        )
        p.drawString(50, y, line)
        y -= 20

        if y < 50:
            p.showPage()
            y = height - 40
            p.setFont("Helvetica", 10)

    p.save()
    return response

@login_required
def filter_attendance_api(request):
    if request.method == 'GET' and not request.user.is_superuser:
        try:
            employee = Employee.objects.get(user=request.user)
            
            search = request.GET.get('search', '')
            month = request.GET.get('month', '')
            status = request.GET.get('status', '')
            
            records = Attendance.objects.filter(employee=employee)
            
            if search:
                records = records.filter(date__icontains=search)
            
            if month:
                records = records.filter(date__month=month)
            
            records = records.order_by('-date')[:100]  # Limit for performance
            
            data = []
            for record in records:
                if record.total_hours > 8:
                    record_status = 'Overtime'
                elif record.total_hours < 8 and record.total_hours > 0:
                    record_status = 'Undertime'
                elif record.total_hours == 8:
                    record_status = 'Completed'
                else:
                    record_status = 'Incomplete'
                
                if status and status != 'All Status' and status != '':
                    if status != record_status:
                        continue
                
                data.append({
                    'date': record.date.strftime('%Y-%m-%d'),
                    'morning_in': record.morning_in.strftime('%I:%M %p') if record.morning_in else '-',
                    'morning_out': record.morning_out.strftime('%I:%M %p') if record.morning_out else '-',
                    'afternoon_in': record.afternoon_in.strftime('%I:%M %p') if record.afternoon_in else '-',
                    'afternoon_out': record.afternoon_out.strftime('%I:%M %p') if record.afternoon_out else '-',
                    'total_hours': str(record.total_hours),
                    'status': record_status,
                })
            
            return JsonResponse({'success': True, 'records': data})
            
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employee not found'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})