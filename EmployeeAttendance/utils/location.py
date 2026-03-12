"""Location payload parsing and serialization helpers."""

import json
from decimal import Decimal, InvalidOperation

from django.http import JsonResponse


def parse_location_payload(request):
    """Validate the JSON payload sent by the browser geolocation workflow."""
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({"error": "Invalid JSON payload."}, status=400)

    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    address = (payload.get("address") or "").strip()

    if latitude in (None, "") or longitude in (None, ""):
        return None, JsonResponse({"error": "Latitude and longitude are required."}, status=400)

    try:
        latitude = Decimal(str(latitude))
        longitude = Decimal(str(longitude))
    except (InvalidOperation, ValueError):
        return None, JsonResponse({"error": "Latitude and longitude must be numeric values."}, status=400)

    if latitude < Decimal("-90") or latitude > Decimal("90"):
        return None, JsonResponse({"error": "Latitude must be between -90 and 90."}, status=400)

    if longitude < Decimal("-180") or longitude > Decimal("180"):
        return None, JsonResponse({"error": "Longitude must be between -180 and 180."}, status=400)

    if len(address) > 255:
        return None, JsonResponse({"error": "Address must be 255 characters or fewer."}, status=400)

    return {
        "latitude": latitude,
        "longitude": longitude,
        "address": address,
    }, None

def serialize_location_log(log):
    """Keep API and map payloads consistent wherever location logs are exposed."""
    return {
        "id": log.id,
        "employee_id": log.employee.employee_id,
        "employee_name": log.employee.name,
        "attendance_date": str(log.attendance.date),
        "attendance_type": log.attendance_type,
        "attendance_type_label": log.get_attendance_type_display(),
        "latitude": float(log.latitude),
        "longitude": float(log.longitude),
        "address": log.address,
        "recorded_at": log.recorded_at.isoformat(),
    }
