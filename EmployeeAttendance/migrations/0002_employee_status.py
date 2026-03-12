"""Database migration for the EmployeeAttendance app."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("EmployeeAttendance", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="status",
            field=models.CharField(
                choices=[("Active", "Active"), ("Non-Active", "Non-Active")],
                default="Active",
                max_length=20,
            ),
        ),
    ]

