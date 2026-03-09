from django import forms
from django.contrib.auth.models import User
from .models import Employee, LeaveRequest


class EmployeeForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Employee
        fields = ['employee_id', 'name', 'department', 'username', 'password']

    def save(self, commit=True):
        employee = super().save(commit=False)

        username = self.cleaned_data['username']
        password = self.cleaned_data['password']

        user = User.objects.create_user(
            username=username,
            password=password
        )

        employee.user = user

        if commit:
            user.save()
            employee.save()

        return employee


class LeaveRequestForm(forms.ModelForm):

    class Meta:
        model = LeaveRequest
        fields = ['leave_date', 'reason']
        widgets = {
            'leave_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 3})
        }