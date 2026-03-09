from django.contrib import admin
from .models import Employee, Attendance, LeaveRequest

admin.site.register(Employee)
admin.site.register(Attendance)
admin.site.register(LeaveRequest)