// ============================================================================
// Top navigation — the Studio / Tracker / Analytics / Admin mode switcher.
// Deliberately dumb: it only knows how to show/hide sections and flags a
// mode change to whoever is listening. Feature modules decide what to do
// when their section becomes active (app.js wires that up).
// ============================================================================

const sectionIds = {
    studio: "section-studio",
    tracker: "section-tracker",
    analytics: "section-analytics",
    ai: "section-ai",
    interview: "section-interview",
    community: "section-community",
    admin: "section-admin",
};
const sections = {};
const listeners = [];
let currentMode = null;

export function onModeChange(fn) {
    listeners.push(fn);
}

export function switchMode(mode) {
    if (!mode || !sections[mode]) return;
    currentMode = mode;
    document.querySelectorAll(".mode-btn").forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
    Object.keys(sections).forEach((k) => {
        sections[k].classList.toggle("hidden", k !== mode);
    });
    listeners.forEach((fn) => fn(mode));
}

export function getCurrentMode() {
    return currentMode;
}

/** Hide every app section (used when the session ends — signing out must not
 *  leave whatever tab was open, e.g. the code console, visible behind the gate). */
export function hideAllSections() {
    currentMode = null;
    document.querySelectorAll(".mode-btn").forEach((b) => b.classList.remove("active"));
    Object.keys(sections).forEach((k) => {
        if (sections[k]) sections[k].classList.add("hidden");
    });
}

export function initNav() {
    Object.keys(sectionIds).forEach((k) => {
        sections[k] = document.getElementById(sectionIds[k]);
    });

    const switcher = document.querySelector(".main-mode-switcher");
    if (switcher) {
        switcher.addEventListener("click", (e) => {
            const btn = e.target.closest(".mode-btn");
            if (btn && btn.dataset.mode) switchMode(btn.dataset.mode);
        });
    }
}
