"""Leave request form definitions."""

from django import forms

from EmployeeAttendance.models import LeaveRequest


class LeaveRequestForm(forms.ModelForm):
    """Collect the leave date and employee-provided reason for a leave request."""
    class Meta:
        model = LeaveRequest
        fields = ["leave_date", "reason"]
        widgets = {
            "leave_date": forms.DateInput(attrs={"type": "date"}),
            "reason": forms.Textarea(attrs={"rows": 3}),
        }


