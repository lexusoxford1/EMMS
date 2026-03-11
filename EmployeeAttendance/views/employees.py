"""Employee management views."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from EmployeeAttendance.forms import EmployeeForm
from EmployeeAttendance.models import Employee
from EmployeeAttendance.utils.auth import is_admin


@login_required
@user_passes_test(is_admin)
def employee_list(request):
    employee_id_query = request.GET.get("employee_id", "").strip()
    employees = Employee.objects.select_related("user").order_by("employee_id")

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
    form = EmployeeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Employee added successfully")
        return redirect("employee_list")

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
