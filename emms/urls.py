"""Root URL configuration that mounts Django admin and the EmployeeAttendance app."""

from django.contrib import admin
from django.urls import path, include

# Route the built-in Django admin separately from the main application URLs.
urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("EmployeeAttendance.urls")),
]




