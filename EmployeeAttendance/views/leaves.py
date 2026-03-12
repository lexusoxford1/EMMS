"""Leave management views."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from EmployeeAttendance.forms import LeaveRequestForm
from EmployeeAttendance.models import Employee, LeaveRequest
from EmployeeAttendance.utils.auth import is_admin


@login_required
def leave_list(request):
    """Show leave requests, scoped to the current employee unless the caller is an admin."""
    if request.user.is_superuser:
        leaves = LeaveRequest.objects.all().order_by("-created_at")
    else:
        employee = get_object_or_404(Employee, user=request.user)
        leaves = LeaveRequest.objects.filter(employee=employee).order_by("-created_at")

    return render(request, "leave_list.html", {"leaves": leaves})


@login_required
def leave_add(request):
    """Create a leave request on behalf of the signed-in employee."""
    employee = get_object_or_404(Employee, user=request.user)
    form = LeaveRequestForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        leave = form.save(commit=False)
        leave.employee = employee
        leave.save()
        messages.success(request, "Leave request submitted successfully")
        return redirect("leave_list")

    return render(request, "leave_form.html", {"form": form})


@login_required
@user_passes_test(is_admin)
def leave_approve(request, pk):
    """Mark a leave request as approved from the admin workflow."""
    leave = get_object_or_404(LeaveRequest, pk=pk)
    leave.status = "Approved"
    leave.save()
    messages.success(request, "Leave request approved")
    return redirect("leave_list")


@login_required
@user_passes_test(is_admin)
def leave_reject(request, pk):
    """Mark a leave request as rejected from the admin workflow."""
    leave = get_object_or_404(LeaveRequest, pk=pk)
    leave.status = "Rejected"
    leave.save()
    messages.success(request, "Leave request rejected")
    return redirect("leave_list")


