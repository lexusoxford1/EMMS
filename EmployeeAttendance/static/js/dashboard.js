(function () {
    function readJsonScript(id) {
        var node = document.getElementById(id);
        if (!node) {
            return null;
        }

        try {
            return JSON.parse(node.textContent);
        } catch (error) {
            return null;
        }
    }

    function drawVerticalBarChart(canvasId, labels, values, color) {
        var canvas = document.getElementById(canvasId);
        if (!canvas || !labels || !labels.length) {
            return;
        }

        var ctx = canvas.getContext("2d");
        var w = canvas.width;
        var h = canvas.height;
        var pad = { top: 16, right: 16, bottom: 46, left: 36 };
        var chartW = w - pad.left - pad.right;
        var chartH = h - pad.top - pad.bottom;
        var maxVal = Math.max.apply(null, values.concat([1]));

        ctx.clearRect(0, 0, w, h);
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, w, h);

        ctx.strokeStyle = "#d9e4dc";
        ctx.beginPath();
        ctx.moveTo(pad.left, pad.top);
        ctx.lineTo(pad.left, h - pad.bottom);
        ctx.lineTo(w - pad.right, h - pad.bottom);
        ctx.stroke();

        var bars = labels.length;
        var slot = chartW / bars;
        var barW = Math.max(18, slot * 0.56);

        ctx.fillStyle = color || "#176b4d";
        ctx.font = "12px Segoe UI";
        ctx.textAlign = "center";

        for (var i = 0; i < bars; i += 1) {
            var value = Number(values[i] || 0);
            var barH = (value / maxVal) * (chartH - 8);
            var x = pad.left + i * slot + (slot - barW) / 2;
            var y = h - pad.bottom - barH;

            ctx.fillRect(x, y, barW, barH);
            ctx.fillStyle = "#1d2a22";
            ctx.fillText(String(value), x + barW / 2, y - 5);
            ctx.fillStyle = "#4f6157";
            ctx.fillText(labels[i], x + barW / 2, h - pad.bottom + 16);
            ctx.fillStyle = color || "#176b4d";
        }
    }

    function drawPieChart(canvasId, labels, values, colors) {
        var canvas = document.getElementById(canvasId);
        if (!canvas || !labels || !labels.length) {
            return;
        }

        var ctx = canvas.getContext("2d");
        var w = canvas.width;
        var h = canvas.height;
        var total = values.reduce(function (sum, item) {
            return sum + Number(item || 0);
        }, 0);
        var cx = w * 0.32;
        var cy = h * 0.5;
        var r = Math.min(w, h) * 0.3;

        ctx.clearRect(0, 0, w, h);
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, w, h);

        if (!total) {
            ctx.fillStyle = "#5a6a61";
            ctx.font = "14px Segoe UI";
            ctx.fillText("No data", cx - 22, cy);
            return;
        }

        var start = -Math.PI / 2;
        for (var i = 0; i < values.length; i += 1) {
            var value = Number(values[i] || 0);
            var angle = (value / total) * Math.PI * 2;
            var end = start + angle;

            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.arc(cx, cy, r, start, end);
            ctx.closePath();
            ctx.fillStyle = colors[i % colors.length];
            ctx.fill();

            start = end;
        }

        ctx.font = "12px Segoe UI";
        var lx = w * 0.62;
        var ly = 42;
        for (var j = 0; j < labels.length; j += 1) {
            var legendValue = Number(values[j] || 0);
            var pct = total ? ((legendValue / total) * 100).toFixed(1) : "0.0";
            ctx.fillStyle = colors[j % colors.length];
            ctx.fillRect(lx, ly - 9, 12, 12);
            ctx.fillStyle = "#1d2a22";
            ctx.fillText(labels[j] + " (" + legendValue + ", " + pct + "%)", lx + 18, ly);
            ly += 24;
        }
    }

    function initializeDashboardCharts() {
        var page = document.querySelector("[data-dashboard-page]");
        if (!page) {
            return;
        }

        var isAdmin = page.dataset.dashboardRole === "admin";
        if (isAdmin) {
            drawVerticalBarChart(
                "adminBarChart",
                readJsonScript("admin-trend-labels") || [],
                readJsonScript("admin-trend-totals") || [],
                "#1b7d59"
            );
            drawPieChart(
                "adminPieChart",
                ["Undertime", "Completed", "Overtime"],
                readJsonScript("admin-status-mix") || [],
                ["#d35f5f", "#2e8b57", "#2c7bb6"]
            );
            return;
        }

        drawVerticalBarChart(
            "employeeBarChart",
            readJsonScript("employee-trend-labels") || [],
            readJsonScript("employee-trend-hours") || [],
            "#176b4d"
        );
        drawPieChart(
            "employeePieChart",
            ["Undertime", "Completed", "Overtime"],
            readJsonScript("employee-status-mix") || [],
            ["#d35f5f", "#2e8b57", "#2c7bb6"]
        );
    }

    document.addEventListener("DOMContentLoaded", initializeDashboardCharts);
})();
