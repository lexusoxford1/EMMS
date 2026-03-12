"""Dashboard views."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from EmployeeAttendance.services.dashboard import build_dashboard_context


@login_required
def dashboard(request):
    return render(request, "dashboard.html", build_dashboard_context(request.user))
