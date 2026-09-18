// ============================================================================
// Auth module — owns session state, the sign-in/register modal, and the
// full-page gate shown to signed-out visitors. Every other feature module is
// login-only, so this module is the single gatekeeper: nothing else renders
// data until it confirms a session and fires the "authed" callback.
// ============================================================================
import { apiJson } from "./utils.js?v=8.0";
import { hideAllSections } from "./nav.js?v=8.0";

const state = { user: null };
const listeners = [];

export function getUser() {
    return state.user;
}

export function isLoggedIn() {
    return !!state.user;
}

/** Subscribe to auth state changes. Called immediately with current state on every change (including the first check). */
export function onAuthChange(fn) {
    listeners.push(fn);
}

function notify() {
    listeners.forEach((fn) => fn(state.user));
}

export async function checkAuthStatus() {
    try {
        const data = await apiJson("/api/auth/me");
        state.user = (data.success && data.authenticated && data.user) ? data.user : null;
    } catch (err) {
        state.user = null;
    }
    renderAuthUI();
    notify();
}

function renderAuthUI() {
    const authGuestView = document.getElementById("auth-guest-view");
    const authUserView = document.getElementById("auth-user-view");
    const userNameDisplay = document.getElementById("user-name-display");
    const userRoleDisplay = document.getElementById("user-role-display");
    const userAvatarInitial = document.getElementById("user-avatar-initial");
    const modeAdminBtn = document.getElementById("mode-admin");
    const authGate = document.getElementById("auth-gate");
    const modeSwitcher = document.querySelector(".main-mode-switcher");

    if (state.user) {
        authGuestView.style.display = "none";
        authUserView.style.display = "flex";
        userNameDisplay.textContent = state.user.username;
        userAvatarInitial.textContent = (state.user.username.charAt(0) || "U").toUpperCase();

        const isAdmin = state.user.role === "admin";
        userRoleDisplay.textContent = state.user.role.toUpperCase();
        userRoleDisplay.classList.toggle("admin-role", isAdmin);
        if (modeAdminBtn) modeAdminBtn.style.display = isAdmin ? "flex" : "none";

        if (authGate) authGate.classList.add("hidden");
        if (modeSwitcher) modeSwitcher.classList.remove("hidden");
    } else {
        authGuestView.style.display = "flex";
        authUserView.style.display = "none";
        if (modeAdminBtn) modeAdminBtn.style.display = "none";

        if (authGate) authGate.classList.remove("hidden");
        if (modeSwitcher) modeSwitcher.classList.add("hidden");

        // Whatever tab was open (Studio's code console included) must not
        // stay visible behind the gate once the session is gone.
        hideAllSections();
    }
}

// ----------------------------------------------------------------------
// Modal (sign in / register)
// ----------------------------------------------------------------------

function showAuthAlert(msg, type = "error") {
    const authAlert = document.getElementById("auth-alert");
    authAlert.textContent = msg;
    authAlert.className = `auth-alert alert-${type}`;
    authAlert.style.display = "block";
}

function hideAuthAlert() {
    const authAlert = document.getElementById("auth-alert");
    authAlert.style.display = "none";
    authAlert.textContent = "";
}

function openAuthModal(defaultTab = "login") {
    hideAuthAlert();
    document.getElementById("auth-modal").style.display = "flex";
    switchAuthTab(defaultTab);
}

function closeAuthModal() {
    document.getElementById("auth-modal").style.display = "none";
    hideAuthAlert();
}

function switchAuthTab(tab) {
    hideAuthAlert();
    document.getElementById("tab-btn-login").classList.toggle("active", tab === "login");
    document.getElementById("tab-btn-register").classList.toggle("active", tab === "register");
    document.getElementById("form-login").style.display = (tab === "login" ? "flex" : "none");
    document.getElementById("form-register").style.display = (tab === "register" ? "flex" : "none");
}

export function setupAuthUI() {
    const authModal = document.getElementById("auth-modal");
    const formLogin = document.getElementById("form-login");
    const formRegister = document.getElementById("form-register");
    const btnDemoAdminFill = document.getElementById("btn-demo-admin-fill");
    const btnLogout = document.getElementById("btn-logout");

    document.getElementById("btn-close-auth")?.addEventListener("click", closeAuthModal);
    document.getElementById("tab-btn-login")?.addEventListener("click", () => switchAuthTab("login"));
    document.getElementById("tab-btn-register")?.addEventListener("click", () => switchAuthTab("register"));

    // Every entry point that should open the modal (navbar + full-page gate).
    document.addEventListener("click", (e) => {
        if (e.target.closest("#btn-open-auth-login") || e.target.closest("#btn-gate-login")) {
            openAuthModal("login");
        } else if (e.target.closest("#btn-open-auth-register") || e.target.closest("#btn-gate-register")) {
            openAuthModal("register");
        }
    });

    if (authModal) {
        authModal.addEventListener("click", (e) => {
            if (e.target === authModal) closeAuthModal();
        });
    }

    document.querySelectorAll(".btn-toggle-pw").forEach((btn) => {
        btn.addEventListener("click", () => {
            const input = btn.closest(".input-password-wrapper").querySelector("input");
            if (input.type === "password") {
                input.type = "text";
                btn.innerHTML = '<i class="fa-regular fa-eye-slash"></i>';
            } else {
                input.type = "password";
                btn.innerHTML = '<i class="fa-regular fa-eye"></i>';
            }
        });
    });

    if (btnDemoAdminFill) {
        btnDemoAdminFill.addEventListener("click", () => {
            document.getElementById("auth-login-identifier").value = "admin";
            document.getElementById("auth-login-password").value = "admin123";
        });
    }

    if (formLogin) {
        formLogin.addEventListener("submit", async (e) => {
            e.preventDefault();
            hideAuthAlert();
            const identifier = document.getElementById("auth-login-identifier").value.trim();
            const password = document.getElementById("auth-login-password").value;

            if (!identifier || !password) {
                showAuthAlert("Please fill in both fields.", "error");
                return;
            }

            const submitBtn = document.getElementById("btn-submit-login");
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Authenticating...';

            try {
                const data = await apiJson("/api/auth/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ identifier, password }),
                });

                if (data.success && data.user) {
                    state.user = data.user;
                    renderAuthUI();
                    notify();
                    showAuthAlert(`Welcome back, ${data.user.username}!`, "success");
                    setTimeout(closeAuthModal, 600);
                } else {
                    showAuthAlert(data.error || "Authentication failed.", "error");
                }
            } catch (err) {
                showAuthAlert("Network error during sign in.", "error");
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fa-solid fa-arrow-right-to-bracket"></i> Authenticate & Enter Studio';
            }
        });
    }

    if (formRegister) {
        formRegister.addEventListener("submit", async (e) => {
            e.preventDefault();
            hideAuthAlert();
            const username = document.getElementById("auth-reg-username").value.trim();
            const email = document.getElementById("auth-reg-email").value.trim();
            const password = document.getElementById("auth-reg-password").value;
            const leetcode_user = document.getElementById("auth-reg-leetcode").value.trim();
            const codechef_user = document.getElementById("auth-reg-codechef").value.trim();
            const codeforces_user = document.getElementById("auth-reg-codeforces").value.trim();

            if (!username || !email || !password) {
                showAuthAlert("Username, Email, and Password are required.", "error");
                return;
            }

            const submitBtn = document.getElementById("btn-submit-register");
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Creating Account...';

            try {
                const data = await apiJson("/api/auth/register", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username, email, password, leetcode_user, codechef_user, codeforces_user }),
                });

                if (data.success && data.user) {
                    state.user = data.user;
                    renderAuthUI();
                    notify();
                    showAuthAlert("Account created successfully!", "success");
                    setTimeout(closeAuthModal, 600);
                } else {
                    showAuthAlert(data.error || "Registration failed.", "error");
                }
            } catch (err) {
                showAuthAlert("Network error during registration.", "error");
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fa-solid fa-user-check"></i> Register Account & Start Coding';
            }
        });
    }

    if (btnLogout) {
        btnLogout.addEventListener("click", async () => {
            try {
                await apiJson("/api/auth/logout", { method: "POST" });
            } catch (err) {
                console.error("Logout error:", err);
            } finally {
                state.user = null;
                renderAuthUI();
                notify();
            }
        });
    }

    // A 401 from any feature module (e.g. session expired mid-use) re-checks
    // auth, which will flip the gate back on.
    document.addEventListener("app:auth-required", () => {
        if (state.user) checkAuthStatus();
    });
}
