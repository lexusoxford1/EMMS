"""Authentication views."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import OperationalError
from django.shortcuts import redirect, render


def login_view(request):
    """Authenticate a user and route them to the dashboard when credentials are valid."""
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("dashboard")

        # Distinguish bad credentials from a disabled account so the feedback is actionable.
        existing_user = User.objects.filter(username=username).first()
        if existing_user and existing_user.check_password(password) and not existing_user.is_active:
            messages.error(request, "Your account is non-active. Please contact your administrator.")
        else:
            messages.error(request, "Invalid username or password")

    return render(request, "login.html")


def logout_view(request):
    """Fallback to cookie cleanup if SQLite session deletion fails."""
    try:
        logout(request)
        return redirect("login")
    except OperationalError:
        response = redirect("login")
        response.delete_cookie(settings.SESSION_COOKIE_NAME)
        response.delete_cookie(settings.CSRF_COOKIE_NAME)
        return response


