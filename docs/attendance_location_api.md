# Attendance Location Tracking API

## Visual Documentation Platform
The system now includes two integrated documentation tools for admins and developers:
- `Swagger UI` for interactive OpenAPI documentation
- `Mermaid` for visual workflow diagrams

Admin-only documentation routes:
- `/api/docs/` -> visual documentation page with workflow diagram and interactive Swagger UI reference
- `/api/schema/` -> raw OpenAPI 3 schema in JSON format

This setup does not require any external API key because the application serves its own OpenAPI schema locally and both Swagger UI and Mermaid render the documentation in the browser.

## Recommended Tools
### Integrated now
- `Swagger UI`
  - Best for endpoint documentation, methods, request bodies, response examples, validation rules, and structured API review.
- `Mermaid`
  - Best for visual process flow diagrams directly in the documentation page.

### Good alternatives
- `ReDoc`
  - Useful for schema-heavy browsing when endpoint reading is the main focus.
- `Postman`
  - Useful for collections, collaboration, and manual API testing.

## Visual System Flow
The visual documentation page shows this process:
1. Employee performs Morning In, Morning Out, Afternoon In, and Afternoon Out.
2. The browser captures employee geolocation.
3. The frontend sends the request to the backend attendance API.
4. The backend validates authentication, request data, coordinates, and attendance order.
5. The system stores attendance and location data in the database.
6. The Admin Panel displays the saved attendance and location monitoring data.

## Feature Overview
This feature records employee attendance together with location data for every attendance action. Each successful attendance action stores:
- the attendance step taken
- the exact timestamp saved on the daily attendance record
- the GPS latitude and longitude captured from the browser
- an optional readable address supplied by the client
- a location log entry linked to both the employee and the daily attendance record

The browser flow is location-first. Before an employee can record `Morning In`, `Morning Out`, `Afternoon In`, or `Afternoon Out`, the front end requests geolocation using `navigator.geolocation` and sends the location to the backend over `fetch` with CSRF protection.

## Attendance Process Flow
1. Employee opens the Attendance page.
2. The page shows `My Attendance Today`, `Today's Attendance Records`, `Recent Location Logs`, and `My History`.
3. The employee clicks the single action button for the next valid step.
4. `static/js/attendance.js` asks the browser for the current geolocation.
5. The browser sends a JSON `POST` request to the attendance API with `latitude`, `longitude`, and optional `address`.
6. The backend validates authentication, method, JSON payload, and coordinate ranges.
7. The backend loads or creates today's attendance record and detects the next valid step in strict order.
8. The backend saves the correct attendance timestamp on the daily attendance record.
9. The backend creates an `AttendanceLocation` log entry for that exact step.
10. The API returns JSON success data and the page reloads.
11. Admin users monitor the saved location output from the daily Location page or the history API.

## Strict Attendance Order
The backend enforces this order and blocks duplicates or skipped steps:
1. `Morning In`
2. `Morning Out`
3. `Afternoon In`
4. `Afternoon Out`

If all four steps are already recorded, the API returns an error and no new location log is created.

## Endpoints
### 1. Record attendance with location
- Method: `POST`
- Path: `/api/attendance/record/`
- Auth: Required session login
- Allowed users: Employee accounts only
- Content-Type: `application/json`

#### Request Body
```json
{
  "latitude": 14.5995,
  "longitude": 120.9842,
  "address": "Manila, Philippines"
}
```

#### Success Response
Status: `201 Created`
```json
{
  "message": "Morning In recorded successfully.",
  "attendance": {
    "date": "2026-03-11",
    "attendance_type": "morning_in",
    "attendance_type_label": "Morning In",
    "recorded_at": "2026-03-11T08:01:22.123456+08:00",
    "status": "Undertime",
    "total_hours": 0
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
    "recorded_at": "2026-03-11T08:01:22.123456+08:00"
  }
}
```

### 2. Get attendance location history
- Method: `GET`
- Path: `/api/attendance/location-history/`
- Auth: Required session login
- Employee behavior: returns only the logged-in employee's logs
- Admin behavior: can return all logs and can filter by employee ID

#### Optional Query Parameters
- `employee_id=EMP-0001` for admin filtering
- `date=YYYY-MM-DD` for date filtering

#### Success Response
Status: `200 OK`
```json
{
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
      "recorded_at": "2026-03-11T08:01:22.123456+08:00"
    }
  ]
}
```

## Validation Rules
- Session-authenticated login is required.
- Admin users are blocked from recording attendance through the employee attendance API.
- `latitude` and `longitude` are required and must be numeric.
- Latitude must be between `-90` and `90`.
- Longitude must be between `-180` and `180`.
- `address` must be at most 255 characters.
- Only the next valid attendance step is allowed.

## Database Design
### `EmployeeAttendance.Attendance`
Stores the daily attendance timestamps.
- `employee`
- `date`
- `morning_in`
- `morning_out`
- `afternoon_in`
- `afternoon_out`

### `EmployeeAttendance.AttendanceLocation`
Stores one location log per attendance action.
- `attendance`
- `employee`
- `attendance_type`
- `latitude`
- `longitude`
- `address`
- `recorded_at`

## End-to-End Recording Example
1. Employee clicks `Morning In` on the attendance page.
2. Browser captures GPS coordinates.
3. Browser posts JSON to `/api/attendance/record/`.
4. Server loads or creates today's attendance row.
5. Server saves the current timestamp to the next allowed step.
6. Server creates an `AttendanceLocation` row with the same step and captured location.
7. The Location page and history API expose the saved result for admin monitoring.
