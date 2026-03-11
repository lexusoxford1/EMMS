from django import forms
from django.contrib.auth.models import User

from .models import Employee, LeaveRequest


class EmployeeForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Employee
        fields = ["name", "department", "status", "username", "password"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].widget = forms.Select(choices=Employee.STATUS_CHOICES)

    def save(self, commit=True):
        employee = super().save(commit=False)
        employee.employee_id = Employee.generate_employee_id()

        username = self.cleaned_data["username"]
        password = self.cleaned_data["password"]
        is_active_user = employee.status == Employee.STATUS_ACTIVE

        user = User.objects.create_user(
            username=username,
            password=password,
            is_active=is_active_user,
        )

        employee.user = user

        if commit:
            user.save()
            employee.save()

        return employee


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ["leave_date", "reason"]
        widgets = {
            "leave_date": forms.DateInput(attrs={"type": "date"}),
            "reason": forms.Textarea(attrs={"rows": 3}),
        }


