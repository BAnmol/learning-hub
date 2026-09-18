// ============================================================================
// App entry point. Every feature lives in its own module under ./modules/ —
// this file only wires them together: auth gates everything else, nav
// dispatches "which section is active" to the module that owns it.
// ============================================================================
import { checkAuthStatus, setupAuthUI, onAuthChange, isLoggedIn } from "./modules/auth.js?v=8.0";
import { initNav, onModeChange, switchMode } from "./modules/nav.js?v=8.0";
import { initStudio, onShow as studioOnShow } from "./modules/studio.js?v=8.0";
import { loadTrackerStats } from "./modules/tracker.js?v=8.0";
import { initAnalytics, onShow as analyticsOnShow } from "./modules/analytics.js?v=8.0";
import { onShow as aiOnShow } from "./modules/ai.js?v=8.0";
import { loadAdminDashboard } from "./modules/admin.js?v=8.0";
import { initInterview, onShow as interviewOnShow, stopActiveTimers as stopInterviewTimers } from "./modules/interview.js?v=8.0";
import { initNotion, refreshNotionStatus } from "./modules/notion.js?v=8.0";
import { initCommunity, onShow as communityOnShow, refreshUnreadBadge as refreshCommunityUnreadBadge, stopAllPolling as stopCommunityPolling } from "./modules/community.js?v=8.0";

const ALLOWED_MODES = ["studio", "tracker", "analytics", "ai", "interview", "community", "admin"];

function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try {
        localStorage.setItem("dsa_nexus_theme", theme);
    } catch (_) {}

    // Feature modules with their own theme-sensitive widgets (e.g. the
    // CodeMirror code editors in Studio and Mock Interview) listen for this
    // to re-theme themselves — they don't get automatically recreated when
    // the site theme is toggled.
    window.dispatchEvent(new CustomEvent("dsa-theme-change", { detail: { theme } }));

    document.querySelectorAll(".theme-toggle-btn").forEach((btn) => {
        const icon = btn.querySelector("i");
        if (theme === "light") {
            if (icon) icon.className = "fa-solid fa-moon";
            btn.setAttribute("title", "Switch to Cool Dark Mode");
            btn.setAttribute("aria-label", "Switch to Cool Dark Mode");
        } else {
            if (icon) icon.className = "fa-solid fa-sun";
            btn.setAttribute("title", "Switch to Classic Light Mode");
            btn.setAttribute("aria-label", "Switch to Classic Light Mode");
        }
    });
}

function initTheme() {
    const savedTheme = localStorage.getItem("dsa_nexus_theme") || "dark";
    applyTheme(savedTheme);

    document.querySelectorAll(".theme-toggle-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            const current = document.documentElement.getAttribute("data-theme") || "dark";
            const next = current === "dark" ? "light" : "dark";
            applyTheme(next);
        });
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    setupAuthUI();
    initNav();
    initAnalytics();
    initInterview();
    initNotion();
    initCommunity();

    onModeChange((mode) => {
        if (mode === "studio") studioOnShow();
        else if (mode === "tracker") loadTrackerStats();
        else if (mode === "analytics") analyticsOnShow();
        else if (mode === "ai") aiOnShow();
        else if (mode === "interview") interviewOnShow();
        else if (mode === "community") communityOnShow();
        else if (mode === "admin") loadAdminDashboard();
    });


    let studioBooted = false;
    onAuthChange(async (user) => {
        if (!user) {
            // Tear down timers that don't already stop themselves via onModeChange
            // (they're designed to keep running across tab switches, just not
            // past logout, where they'd otherwise keep firing now-401'd requests).
            stopInterviewTimers();
            stopCommunityPolling();
            return;
        }

        refreshNotionStatus();
        refreshCommunityUnreadBadge();

        if (!studioBooted) {
            studioBooted = true;
            await initStudio();
        }

        const initHash = window.location.hash.replace("#", "");
        switchMode(ALLOWED_MODES.includes(initHash) ? initHash : "studio");
    });

    // Footer quick links: jump straight there if signed in, otherwise open
    // the sign-in modal — never silently reveal a section pre-auth.
    document.querySelectorAll(".footer-links [data-mode]").forEach((link) => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            if (isLoggedIn()) {
                switchMode(link.dataset.mode);
                window.scrollTo({ top: 0, behavior: "smooth" });
            } else {
                document.getElementById("btn-gate-login")?.click();
            }
        });
    });

    checkAuthStatus();
});
