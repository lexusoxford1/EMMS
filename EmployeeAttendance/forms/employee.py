"""Employee-related form definitions."""

from django import forms
from django.contrib.auth.models import User

from EmployeeAttendance.models import Employee


class EmployeeForm(forms.ModelForm):
    """Create an employee record and its linked Django user in one step."""

    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Employee
        fields = ["name", "department", "status", "username", "password"]

    def __init__(self, *args, **kwargs):
        """Swap the default status widget for an explicit select input."""
        super().__init__(*args, **kwargs)
        self.fields["status"].widget = forms.Select(choices=Employee.STATUS_CHOICES)

    def save(self, commit=True):
        """Create both the employee row and its linked Django auth user."""
        employee = super().save(commit=False)
        employee.employee_id = Employee.generate_employee_id()

        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            password=self.cleaned_data["password"],
            is_active=employee.status == Employee.STATUS_ACTIVE,
        )
        employee.user = user

        if commit:
            user.save()
            employee.save()

        return employee


