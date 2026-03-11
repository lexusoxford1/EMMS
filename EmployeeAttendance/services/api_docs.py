"""Helpers for serving local OpenAPI documentation assets."""

from pathlib import Path

from django.conf import settings


DOCS_YAML_PATH = Path(settings.BASE_DIR) / "docs" / "emms-attendance-api.yaml"


def build_api_schema(request):
    """Build the lightweight JSON schema served by the in-app docs page."""
    base_url = request.build_absolute_uri("/").rstrip("/")

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "EMMS Attendance Location API",
            "version": "1.0.0",
            "description": (
                "API documentation for the Employee Management and Monitoring System attendance "
                "location tracking flow. This documentation is rendered through locally served "
                "OpenAPI assets, so it demonstrates the API design without requiring an external API key."
            ),
        },
        "servers": [
            {
                "url": base_url,
                "description": "Current Django application host",
            }
        ],
        "tags": [
            {
                "name": "Attendance",
                "description": "Employee attendance recording with strict step validation and GPS capture.",
            },
            {
                "name": "Location History",
                "description": "Role-based access to recorded attendance location logs.",
            },
        ],
        "paths": {
            "/api/attendance/record/": {
                "post": {
                    "tags": ["Attendance"],
                    "summary": "Record the next valid attendance step with location",
                    "security": [{"cookieAuth": []}],
                    "description": (
                        "Frontend flow: the browser captures geolocation with navigator.geolocation, "
                        "then sends latitude, longitude, and optional address to this endpoint. "
                        "The backend validates the request, determines the next valid step in the "
                        "sequence Morning In -> Morning Out -> Afternoon In -> Afternoon Out, saves "
                        "the attendance timestamp, and creates a linked AttendanceLocation record. "
                        "Authentication is required, and admin accounts are blocked from using this endpoint."
                    ),
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/AttendanceRecordRequest"},
                                "examples": {
                                    "employeeLocation": {
                                        "summary": "Employee geolocation payload",
                                        "value": {
                                            "latitude": 14.5995,
                                            "longitude": 120.9842,
                                            "address": "Manila, Philippines",
                                        },
                                    }
                                },
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Attendance step recorded and location log saved.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/AttendanceRecordSuccessResponse"},
                                    "examples": {
                                        "morningInSuccess": {
                                            "summary": "Successful Morning In response",
                                            "value": {
                                                "message": "Morning In recorded successfully.",
                                                "attendance": {
                                                    "date": "2026-03-11",
                                                    "attendance_type": "morning_in",
                                                    "attendance_type_label": "Morning In",
                                                    "recorded_at": "2026-03-11T08:01:22+08:00",
                                                    "status": "Undertime",
                                                    "total_hours": 0,
                                                },
                                                "location": {
                                                    "id": 15,
                                                    "employee_id": "EMP-0001",
                                                    "employee_name": "Jane Doe",
                                                    "attendance_date": "2026-03-11",
                                                    "attendance_type": "morning_in",
                                                    "attendance_type_label": "Morning In",
                                                    "latitude": 14.5995,
                                                    "longitude": 120.9842,
                                                    "address": "Manila, Philippines",
                                                    "recorded_at": "2026-03-11T08:01:22+08:00",
                                                },
                                            },
                                        }
                                    },
                                }
                            },
                        },
                        "400": {
                            "description": "Validation failed or the attendance step is not allowed.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                                    "examples": {
                                        "invalidCoordinates": {
                                            "summary": "Missing coordinates",
                                            "value": {"error": "Latitude and longitude are required."},
                                        },
                                        "alreadyComplete": {
                                            "summary": "Attendance already complete",
                                            "value": {"error": "Attendance for today is already complete."},
                                        },
                                    },
                                }
                            },
                        },
                        "403": {
                            "description": "The authenticated user is not allowed to record attendance.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                                    "examples": {
                                        "adminBlocked": {
                                            "summary": "Admin account blocked",
                                            "value": {"error": "Admin accounts cannot record attendance."},
                                        }
                                    },
                                }
                            },
                        },
                    },
                }
            },
            "/api/attendance/location-history/": {
                "get": {
                    "tags": ["Location History"],
                    "summary": "Get attendance location logs",
                    "security": [{"cookieAuth": []}],
                    "description": (
                        "Returns recorded attendance locations. Employees only receive their own logs. "
                        "Admins can review broader data and optionally filter by employee ID and date. "
                        "Session authentication is required for access."
                    ),
                    "parameters": [
                        {
                            "name": "employee_id",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string", "example": "EMP-0001"},
                            "description": "Admin-only filter for a specific employee ID.",
                        },
                        {
                            "name": "date",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string", "format": "date", "example": "2026-03-11"},
                            "description": "Optional date filter in YYYY-MM-DD format.",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Location history returned successfully.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/LocationHistoryResponse"},
                                    "examples": {
                                        "historySuccess": {
                                            "summary": "Location history response",
                                            "value": {
                                                "count": 1,
                                                "results": [
                                                    {
                                                        "id": 15,
                                                        "employee_id": "EMP-0001",
                                                        "employee_name": "Jane Doe",
                                                        "attendance_date": "2026-03-11",
                                                        "attendance_type": "morning_in",
                                                        "attendance_type_label": "Morning In",
                                                        "latitude": 14.5995,
                                                        "longitude": 120.9842,
                                                        "address": "Manila, Philippines",
                                                        "recorded_at": "2026-03-11T08:01:22+08:00",
                                                    }
                                                ],
                                            },
                                        }
                                    },
                                }
                            },
                        },
                        "400": {
                            "description": "Invalid query parameter value.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                                    "examples": {
                                        "invalidDate": {
                                            "summary": "Bad date filter",
                                            "value": {"error": "date must be in YYYY-MM-DD format."},
                                        }
                                    },
                                }
                            },
                        },
                    },
                }
            },
        },
        "components": {
            "schemas": {
                "AttendanceRecordRequest": {
                    "type": "object",
                    "required": ["latitude", "longitude"],
                    "properties": {
                        "latitude": {
                            "type": "number",
                            "format": "float",
                            "minimum": -90,
                            "maximum": 90,
                            "description": "GPS latitude captured from the browser.",
                        },
                        "longitude": {
                            "type": "number",
                            "format": "float",
                            "minimum": -180,
                            "maximum": 180,
                            "description": "GPS longitude captured from the browser.",
                        },
                        "address": {
                            "type": "string",
                            "maxLength": 255,
                            "description": "Optional readable address sent by the client if available.",
                        },
                    },
                },
                "AttendanceSummary": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "format": "date"},
                        "attendance_type": {
                            "type": "string",
                            "enum": ["morning_in", "morning_out", "afternoon_in", "afternoon_out"],
                        },
                        "attendance_type_label": {"type": "string"},
                        "recorded_at": {"type": "string", "format": "date-time"},
                        "status": {"type": "string"},
                        "total_hours": {"type": "number"},
                    },
                },
                "LocationLog": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "employee_id": {"type": "string"},
                        "employee_name": {"type": "string"},
                        "attendance_date": {"type": "string", "format": "date"},
                        "attendance_type": {
                            "type": "string",
                            "enum": ["morning_in", "morning_out", "afternoon_in", "afternoon_out"],
                        },
                        "attendance_type_label": {"type": "string"},
                        "latitude": {"type": "number", "format": "float"},
                        "longitude": {"type": "number", "format": "float"},
                        "address": {"type": "string"},
                        "recorded_at": {"type": "string", "format": "date-time"},
                    },
                },
                "AttendanceRecordSuccessResponse": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "attendance": {"$ref": "#/components/schemas/AttendanceSummary"},
                        "location": {"$ref": "#/components/schemas/LocationLog"},
                    },
                },
                "LocationHistoryResponse": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer"},
                        "results": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/LocationLog"},
                        },
                    },
                },
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string"},
                    },
                },
            }
        },
        "x-emms-process-flow": [
            "Employee opens the Attendance page and clicks the next step button.",
            "attendance.js requests browser geolocation and sends latitude, longitude, and optional address using fetch with CSRF.",
            "Django validates authentication, JSON structure, coordinate ranges, and the strict attendance order.",
            "The Attendance record is updated with the correct timestamp for the next step.",
            "An AttendanceLocation row is created and linked to both the employee and the attendance record.",
            "Admin users monitor the resulting logs on the Locations page and through the location history API.",
        ],
        "x-emms-validation-rules": [
            "Session authentication is required.",
            "Admin accounts cannot use the record attendance endpoint.",
            "Latitude must be between -90 and 90.",
            "Longitude must be between -180 and 180.",
            "Address is optional and limited to 255 characters.",
            "Attendance steps must follow Morning In, Morning Out, Afternoon In, Afternoon Out.",
        ],
    }
