// Script: attendance. This file handles geolocation capture and attendance API submission.
(function () {
    // Read Django's CSRF cookie so the fetch request is accepted by the server.
    function getCookie(name) {
        var cookieValue = null;
        if (!document.cookie) {
            return cookieValue;
        }

        var cookies = document.cookie.split(";");
        for (var i = 0; i < cookies.length; i += 1) {
            var cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === name + "=") {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
        return cookieValue;
    }

    // Reuse the same status element for success and error feedback.
    function setStatus(message, isError) {
        var statusNode = document.querySelector("[data-attendance-status]");
        if (!statusNode) {
            return;
        }
        statusNode.textContent = message;
        statusNode.style.color = isError ? "#8f2626" : "#176b4d";
    }

    // Wrap the browser geolocation API in a promise so the submit flow stays readable.
    function requestCurrentPosition() {
        return new Promise(function (resolve, reject) {
            if (!navigator.geolocation) {
                reject(new Error("Geolocation is not supported by this browser."));
                return;
            }

            navigator.geolocation.getCurrentPosition(
                function (position) {
                    resolve({
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        address: "",
                    });
                },
                function (error) {
                    reject(new Error(error.message || "Unable to capture your location."));
                },
                {
                    enableHighAccuracy: true,
                    timeout: 15000,
                    maximumAge: 0,
                }
            );
        });
    }

    // Drive the full attendance submission workflow from the page form.
    function initializeAttendanceRecorder() {
        var form = document.querySelector("[data-attendance-form]");
        if (!form) {
            return;
        }

        var button = form.querySelector("button[type='submit']");
        form.addEventListener("submit", function (event) {
            event.preventDefault();

            if (!button || button.disabled) {
                return;
            }

            button.disabled = true;
            setStatus("Capturing your location...", false);

            requestCurrentPosition()
                .then(function (payload) {
                    return fetch(form.dataset.apiUrl, {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": getCookie("csrftoken"),
                        },
                        body: JSON.stringify(payload),
                    });
                })
                .then(function (response) {
                    return response.json().then(function (data) {
                        if (!response.ok) {
                            throw new Error(data.error || "Attendance recording failed.");
                        }
                        return data;
                    });
                })
                .then(function (data) {
                    setStatus(data.message + " Reloading...", false);
                    window.location.reload();
                })
                .catch(function (error) {
                    setStatus(error.message, true);
                    button.disabled = false;
                });
        });
    }

    document.addEventListener("DOMContentLoaded", initializeAttendanceRecorder);
})();
