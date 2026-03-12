"""Reporting and export helpers."""

from django.contrib import messages
from django.http import HttpResponse

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from EmployeeAttendance.models import Attendance


REPORT_COLUMNS = [
    "Date",
    "Employee ID",
    "Name",
    "Department",
    "Morning In",
    "Morning Out",
    "Afternoon In",
    "Afternoon Out",
    "Total Hours",
]


def get_report_attendances(month):
    """Return attendances filtered by the optional YYYY-MM month string."""
    attendances = Attendance.objects.select_related("employee").order_by("-date")
    invalid_month = False

    if month:
        try:
            year, month_number = map(int, month.split("-"))
        except ValueError:
            invalid_month = True
        else:
            attendances = attendances.filter(date__year=year, date__month=month_number)

    return attendances, invalid_month


def attach_invalid_month_message(request, invalid_month):
    """Attach a friendly validation message when the month filter cannot be parsed."""
    if invalid_month:
        messages.error(request, "Invalid month format")


def build_excel_report_response(attendances):
    """Generate the Excel export that mirrors the on-screen report table."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Attendance Report"
    worksheet.append(REPORT_COLUMNS)

    for attendance in attendances:
        worksheet.append(
            [
                str(attendance.date),
                attendance.employee.employee_id,
                attendance.employee.name,
                attendance.employee.department,
                attendance.morning_in.strftime("%Y-%m-%d %H:%M:%S") if attendance.morning_in else "",
                attendance.morning_out.strftime("%Y-%m-%d %H:%M:%S") if attendance.morning_out else "",
                attendance.afternoon_in.strftime("%Y-%m-%d %H:%M:%S") if attendance.afternoon_in else "",
                attendance.afternoon_out.strftime("%Y-%m-%d %H:%M:%S") if attendance.afternoon_out else "",
                attendance.total_hours,
            ]
        )

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="attendance_report.xlsx"'
    workbook.save(response)
    return response


def build_pdf_report_response(attendances, month):
    """Generate the styled PDF export used by the reports page."""
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="attendance_report.pdf"'

    document = SimpleDocTemplate(
        response,
        pagesize=landscape(letter),
        leftMargin=0.45 * inch,
        rightMargin=0.45 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.45 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    title_style.fontName = "Helvetica-Bold"
    title_style.fontSize = 18
    title_style.leading = 22
    title_style.textColor = colors.HexColor("#143d2f")
    title_style.alignment = 0

    meta_style = styles["BodyText"]
    meta_style.fontName = "Helvetica"
    meta_style.fontSize = 9
    meta_style.leading = 12
    meta_style.textColor = colors.HexColor("#52635a")

    # Build the table body first so export metadata and row counts stay consistent.
    table_data = [REPORT_COLUMNS]
    for attendance in attendances:
        table_data.append(
            [
                str(attendance.date),
                attendance.employee.employee_id,
                attendance.employee.name,
                attendance.employee.department,
                attendance.morning_in.strftime("%Y-%m-%d %H:%M:%S") if attendance.morning_in else "-",
                attendance.morning_out.strftime("%Y-%m-%d %H:%M:%S") if attendance.morning_out else "-",
                attendance.afternoon_in.strftime("%Y-%m-%d %H:%M:%S") if attendance.afternoon_in else "-",
                attendance.afternoon_out.strftime("%Y-%m-%d %H:%M:%S") if attendance.afternoon_out else "-",
                str(attendance.total_hours),
            ]
        )

    column_widths = [
        0.75 * inch,
        0.95 * inch,
        1.15 * inch,
        1.05 * inch,
        1.18 * inch,
        1.18 * inch,
        1.18 * inch,
        1.18 * inch,
        0.65 * inch,
    ]
    scale = document.width / sum(column_widths)
    column_widths = [width * scale for width in column_widths]

    report_table = Table(table_data, colWidths=column_widths, repeatRows=1)
    report_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#176b4d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEADING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f7fbf8"), colors.white]),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#1e2d25")),
                ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#d4e1d8")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("ALIGN", (-1, 1), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 1), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ]
        )
    )

    meta_bits = []
    if month:
        meta_bits.append(f"Month filter: {month}")
    meta_bits.append(f"Rows: {len(table_data) - 1}")

    story = [
        Paragraph("Attendance Report", title_style),
        Spacer(1, 0.12 * inch),
        Paragraph(" | ".join(meta_bits), meta_style),
        Spacer(1, 0.2 * inch),
        report_table,
    ]
    document.build(story)
    return response


