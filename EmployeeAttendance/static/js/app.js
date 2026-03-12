(function () {
    function initializeSidebarToggle() {
        var sidebar = document.getElementById("sidebar");
        var toggleBtn = document.getElementById("sidebarToggle");

        if (!sidebar || !toggleBtn) {
            return;
        }

        var mobileQuery = window.matchMedia("(max-width: 960px)");

        function applyDesktopState() {
            var saved = localStorage.getItem("emms_sidebar_collapsed");
            if (saved === "1") {
                sidebar.classList.add("collapsed");
            }
        }

        if (!mobileQuery.matches) {
            applyDesktopState();
        }

        toggleBtn.addEventListener("click", function () {
            if (mobileQuery.matches) {
                sidebar.classList.toggle("open");
                return;
            }

            sidebar.classList.toggle("collapsed");
            localStorage.setItem(
                "emms_sidebar_collapsed",
                sidebar.classList.contains("collapsed") ? "1" : "0"
            );
        });

        window.addEventListener("resize", function () {
            if (!mobileQuery.matches) {
                sidebar.classList.remove("open");
            }
        });
    }

    function initializeScrollTopButton() {
        var button = document.getElementById("scrollTopBtn");
        var mainPanel = document.querySelector(".main-panel, .app-shell");

        if (!button) {
            return;
        }

        function getScrollTop() {
            var documentTop = window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0;
            var panelTop = mainPanel ? mainPanel.scrollTop : 0;
            return Math.max(documentTop, panelTop);
        }

        function toggleVisibility() {
            button.classList.toggle("visible", getScrollTop() > 200);
        }

        function scrollToTop() {
            if (mainPanel && mainPanel.scrollTop > 0) {
                mainPanel.scrollTo({ top: 0, behavior: "smooth" });
            }

            window.scrollTo({
                top: 0,
                behavior: "smooth"
            });
        }

        button.addEventListener("click", scrollToTop);
        window.addEventListener("scroll", toggleVisibility, { passive: true });

        if (mainPanel) {
            mainPanel.addEventListener("scroll", toggleVisibility, { passive: true });
        }

        toggleVisibility();
    }

    document.addEventListener("DOMContentLoaded", function () {
        initializeSidebarToggle();
        initializeScrollTopButton();
    });
})();
