// Script: location_tracking. This file renders Google Maps markers from server-provided JSON.
(function () {
    // Build the map only when both the DOM container and Google Maps API are ready.
    function initializeGoogleLocationMap() {
        var dataNode = document.getElementById("location-map-points");
        var mapNode = document.getElementById("attendanceLocationMap");

        if (!dataNode || !mapNode || typeof google === "undefined" || !google.maps) {
            return;
        }

        var points;
        try {
            points = JSON.parse(dataNode.textContent);
        } catch (error) {
            return;
        }

        if (!points.length) {
            return;
        }

        var firstPoint = points[0];
        var map = new google.maps.Map(mapNode, {
            center: { lat: firstPoint.latitude, lng: firstPoint.longitude },
            zoom: 15,
            mapTypeControl: false,
            streetViewControl: false,
            fullscreenControl: true,
        });

        var bounds = new google.maps.LatLngBounds();
        var infoWindow = new google.maps.InfoWindow();

        points.forEach(function (point) {
            var position = { lat: point.latitude, lng: point.longitude };
            var marker = new google.maps.Marker({
                position: position,
                map: map,
                title: point.employee_name + " - " + point.attendance_type,
            });

            marker.addListener("click", function () {
                infoWindow.setContent(
                    [
                        "<strong>" + point.employee_name + "</strong>",
                        point.employee_id,
                        point.attendance_type + " - " + point.attendance_date,
                        point.address || "No address provided",
                    ].join("<br>")
                );
                infoWindow.open(map, marker);
            });

            bounds.extend(position);
        });

        if (points.length > 1) {
            map.fitBounds(bounds, 48);
        }
    }

    // Expose the initializer so the Google Maps callback can invoke it.
    window.initAttendanceLocationMap = initializeGoogleLocationMap;

    document.addEventListener("DOMContentLoaded", function () {
        if (typeof google !== "undefined" && google.maps) {
            initializeGoogleLocationMap();
        }
    });
})();
