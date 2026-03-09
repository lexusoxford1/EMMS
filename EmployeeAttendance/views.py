from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

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
            messages.error(request, "Invalid username or password")

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard(request):
    employee_count = Employee.objects.count()
    today_attendance = Attendance.objects.filter(
        created_at__date=timezone.now().date()
    ).count()
    pending_leaves = LeaveRequest.objects.filter(status="Pending").count()

    context = {
        "employee_count": employee_count,
        "today_attendance": today_attendance,
        "pending_leaves": pending_leaves,
    }
    return render(request, "dashboard.html", context)


@login_required
@user_passes_test(is_admin)
def employee_list(request):
    employees = Employee.objects.all().order_by("employee_id")
    return render(request, "employee_list.html", {"employees": employees})


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
def attendance_view(request):
    if request.user.is_superuser:
        today = timezone.now().date()
        today_records = Attendance.objects.filter(
            created_at__date=today
        ).select_related("employee").order_by("-check_in_time")

        context = {
            "today_record": None,
            "today_records": today_records,
            "my_history": [],
            "is_admin_view": True,
        }
        return render(request, "attendance.html", context)

    employee = get_object_or_404(Employee, user=request.user)
    today = timezone.now().date()

    today_record = Attendance.objects.filter(
        employee=employee,
        created_at__date=today
    ).order_by("-created_at").first()

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "checkin":
            if today_record and today_record.check_in_time and not today_record.check_out_time:
                messages.warning(request, "You already checked in today")
            else:
                Attendance.objects.create(
                    employee=employee,
                    check_in_time=timezone.now()
                )
                messages.success(request, "Checked in successfully")
            return redirect("attendance")

        elif action == "checkout":
            if today_record and today_record.check_in_time and not today_record.check_out_time:
                today_record.check_out_time = timezone.now()
                today_record.save()
                messages.success(request, "Checked out successfully")
            else:
                messages.warning(request, "No active check-in found")
            return redirect("attendance")

    today_records = Attendance.objects.filter(
        created_at__date=today
    ).select_related("employee").order_by("-check_in_time")

    my_history = Attendance.objects.filter(employee=employee).order_by("-created_at")

    context = {
        "today_record": today_record,
        "today_records": today_records,
        "my_history": my_history,
        "is_admin_view": False,
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
    attendances = Attendance.objects.all().select_related("employee").order_by("-created_at")

    if month:
        try:
            year, month_num = map(int, month.split("-"))
            attendances = attendances.filter(
                created_at__year=year,
                created_at__month=month_num
            )
        except ValueError:
            messages.error(request, "Invalid month format")

    return render(request, "report.html", {"attendances": attendances})


@login_required
@user_passes_test(is_admin)
def export_excel(request):
    month = request.GET.get("month")
    attendances = Attendance.objects.all().select_related("employee").order_by("-created_at")

    if month:
        try:
            year, month_num = map(int, month.split("-"))
            attendances = attendances.filter(
                created_at__year=year,
                created_at__month=month_num
            )
        except ValueError:
            pass

    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance Report"

    ws.append(["Employee ID", "Name", "Department", "Check In", "Check Out", "Worked Hours"])

    for a in attendances:
        ws.append([
            a.employee.employee_id,
            a.employee.name,
            a.employee.department,
            a.check_in_time.strftime("%Y-%m-%d %H:%M:%S") if a.check_in_time else "",
            a.check_out_time.strftime("%Y-%m-%d %H:%M:%S") if a.check_out_time else "",
            a.worked_hours,
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
    attendances = Attendance.objects.all().select_related("employee").order_by("-created_at")

    if month:
        try:
            year, month_num = map(int, month.split("-"))
            attendances = attendances.filter(
                created_at__year=year,
                created_at__month=month_num
            )
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
            f"{a.employee.employee_id} | {a.employee.name} | "
            f"In: {a.check_in_time.strftime('%Y-%m-%d %H:%M') if a.check_in_time else '-'} | "
            f"Out: {a.check_out_time.strftime('%Y-%m-%d %H:%M') if a.check_out_time else '-'} | "
            f"Hours: {a.worked_hours}"
        )
        p.drawString(50, y, line)
        y -= 20

        if y < 50:
            p.showPage()
            y = height - 40
            p.setFont("Helvetica", 10)

    p.save()
    return response