"""Swagger/OpenAPI documentation views."""

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

from EmployeeAttendance.services.api_docs import DOCS_YAML_PATH, build_api_schema
from EmployeeAttendance.utils.auth import is_admin


@login_required
@user_passes_test(is_admin)
def api_schema_view(request):
    """Serve the JSON schema that powers the in-app Swagger page."""
    return JsonResponse(build_api_schema(request), json_dumps_params={"indent": 2})


@login_required
@user_passes_test(is_admin)
def api_schema_yaml_view(request):
    """Return the checked-in OpenAPI YAML so reviewers can inspect the raw contract."""
    if not DOCS_YAML_PATH.exists():
        return HttpResponse("OpenAPI YAML file not found.", status=404, content_type="text/plain")

    return HttpResponse(DOCS_YAML_PATH.read_text(encoding="utf-8"), content_type="application/yaml")


@login_required
@user_passes_test(is_admin)
def api_docs_view(request):
    """Render the API docs page with host-aware links for local browsing."""
    context = {
        "schema_url": request.build_absolute_uri("/api/schema/"),
        "yaml_url": request.build_absolute_uri("/api/schema/yaml/"),
        "record_endpoint": request.build_absolute_uri("/api/attendance/record/"),
        "history_endpoint": request.build_absolute_uri("/api/attendance/location-history/"),
    }
    return render(request, "api_docs.html", context)


