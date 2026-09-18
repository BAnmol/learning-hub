// ============================================================================
// Admin Command Center — RBAC user directory, KPIs, and the registration feed.
// Every request here also requires the admin role server-side (@admin_required);
// this module just avoids calling it for non-admins in the first place.
// ============================================================================
import { apiJson, escapeHtml } from "./utils.js?v=8.0";
import { getUser } from "./auth.js?v=8.0";

let btnRefreshAdmin, adminUserSearch, adminRoleFilter, adminUsersTbody, adminFeedList, adminUserCountBadge;
let cached = false;

function cacheDom() {
    btnRefreshAdmin = document.getElementById("btn-refresh-admin");
    adminUserSearch = document.getElementById("admin-user-search");
    adminRoleFilter = document.getElementById("admin-role-filter");
    adminUsersTbody = document.getElementById("admin-users-tbody");
    adminFeedList = document.getElementById("admin-feed-list");
    adminUserCountBadge = document.getElementById("admin-user-count-badge");

    if (btnRefreshAdmin) {
        btnRefreshAdmin.addEventListener("click", () => {
            btnRefreshAdmin.innerHTML = '<i class="fa-solid fa-rotate fa-spin"></i> Refreshing...';
            loadAdminDashboard().finally(() => {
                setTimeout(() => {
                    btnRefreshAdmin.innerHTML = '<i class="fa-solid fa-rotate"></i> Refresh Data';
                }, 400);
            });
        });
    }

    if (adminUserSearch) {
        let debounceTimer;
        adminUserSearch.addEventListener("input", () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(loadAdminUsers, 300);
        });
    }

    if (adminRoleFilter) {
        adminRoleFilter.addEventListener("change", loadAdminUsers);
    }

    cached = true;
}

export async function loadAdminDashboard() {
    if (!cached) cacheDom();
    const user = getUser();
    if (!user || user.role !== "admin") return;
    await Promise.all([loadAdminStats(), loadAdminUsers()]);
}

async function loadAdminStats() {
    try {
        const data = await apiJson("/api/admin/stats");
        if (data.success && data.stats) {
            const s = data.stats;
            document.getElementById("kpi-total-users").textContent = s.total_users || 0;
            document.getElementById("kpi-registered-today").textContent = `+${s.registered_today || 0} joined today`;
            document.getElementById("kpi-total-admins").textContent = s.total_admins || 0;
            document.getElementById("kpi-global-submissions").textContent = s.global_submissions || 0;
            document.getElementById("kpi-global-solved").textContent = `${s.global_solved || 0} solved problems`;
            document.getElementById("kpi-active-today").textContent = s.active_today || 0;

            renderAdminRecentFeed(s.recent_users || []);
        }
    } catch (err) {
        console.error("Failed to load admin stats:", err);
    }
}

async function loadAdminUsers() {
    const search = adminUserSearch?.value.trim() || "";
    const role = adminRoleFilter?.value.trim() || "";

    try {
        const data = await apiJson(`/api/admin/users?search=${encodeURIComponent(search)}&role=${encodeURIComponent(role)}`);
        if (data.success && data.users) {
            renderAdminUsersTable(data.users);
            if (adminUserCountBadge) {
                adminUserCountBadge.textContent = `${data.total_count} Users`;
            }
        }
    } catch (err) {
        console.error("Failed to load admin users:", err);
    }
}

function renderAdminUsersTable(users) {
    if (!adminUsersTbody) return;
    adminUsersTbody.innerHTML = "";

    if (!users || users.length === 0) {
        adminUsersTbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; color: var(--text-muted); padding: 30px;">
                    <i class="fa-solid fa-users-slash" style="font-size: 24px; margin-bottom: 8px; display: block;"></i>
                    No registered users found matching the search criteria.
                </td>
            </tr>
        `;
        return;
    }

    users.forEach((u) => {
        const tr = document.createElement("tr");
        const isAdmin = u.role === "admin";
        const isActive = u.is_active === 1;
        const initial = (u.username.charAt(0) || "U").toUpperCase();

        let platformBadges = "";
        if (u.leetcode_user) platformBadges += `<span class="handle-mini-tag" title="LeetCode: ${escapeHtml(u.leetcode_user)}"><i class="fa-solid fa-code"></i> ${escapeHtml(u.leetcode_user)}</span>`;
        if (u.codechef_user) platformBadges += `<span class="handle-mini-tag" title="CodeChef: ${escapeHtml(u.codechef_user)}"><i class="fa-solid fa-utensils"></i> ${escapeHtml(u.codechef_user)}</span>`;
        if (u.codeforces_user) platformBadges += `<span class="handle-mini-tag" title="Codeforces: ${escapeHtml(u.codeforces_user)}"><i class="fa-solid fa-chart-column"></i> ${escapeHtml(u.codeforces_user)}</span>`;

        tr.innerHTML = `
            <td>
                <div class="user-cell">
                    <div class="user-cell-avatar" style="${isAdmin ? 'background: var(--accent-purple);' : ''}">${initial}</div>
                    <div class="user-cell-meta">
                        <span class="user-cell-name">${escapeHtml(u.username)}</span>
                        <div class="user-handles-tags">${platformBadges || '<span class="text-muted" style="font-size: 0.65rem;">No handles connected</span>'}</div>
                    </div>
                </div>
            </td>
            <td><span style="font-family: var(--font-mono); font-size: 0.82rem;">${escapeHtml(u.email)}</span></td>
            <td>
                <span class="role-badge-pill ${isAdmin ? 'role-admin-pill' : 'role-user-pill'}">
                    <i class="fa-solid ${isAdmin ? 'fa-shield-halved' : 'fa-user'}"></i> ${u.role.toUpperCase()}
                </span>
            </td>
            <td style="color: var(--text-secondary); font-size: 0.8rem;">
                ${escapeHtml(u.created_at || "N/A")}
            </td>
            <td style="color: var(--text-muted); font-size: 0.8rem;">
                ${u.last_login ? escapeHtml(u.last_login) : '<em>Never</em>'}
            </td>
            <td>
                <strong style="color: var(--easy-color);">${u.total_solved || 0}</strong> solved /
                <span style="color: var(--text-secondary);">${u.total_submissions || 0} subs</span>
                ${u.current_streak > 0 ? `<span style="color: var(--danger); margin-left: 6px;"><i class="fa-solid fa-fire"></i> ${u.current_streak}d</span>` : ''}
            </td>
            <td>
                <span class="status-badge-pill ${isActive ? 'status-active' : 'status-suspended'}">
                    ${isActive ? 'Active' : 'Suspended'}
                </span>
            </td>
            <td>
                <div class="actions-btn-group">
                    <button class="btn-action-sm btn-toggle-role" data-user-id="${u.id}" data-role="${isAdmin ? 'user' : 'admin'}" title="Toggle Admin/User role">
                        ${isAdmin ? '<i class="fa-solid fa-user-minus"></i> Demote' : '<i class="fa-solid fa-user-shield"></i> Make Admin'}
                    </button>
                    <button class="btn-action-sm btn-toggle-status" data-user-id="${u.id}" title="Toggle account status">
                        ${isActive ? '<i class="fa-solid fa-ban" style="color:var(--danger);"></i>' : '<i class="fa-solid fa-check" style="color:var(--success);"></i>'}
                    </button>
                </div>
            </td>
        `;

        adminUsersTbody.appendChild(tr);
    });

    adminUsersTbody.querySelectorAll(".btn-toggle-role").forEach((btn) => {
        btn.addEventListener("click", async () => {
            await updateAdminUserRole(btn.dataset.userId, btn.dataset.role);
        });
    });

    adminUsersTbody.querySelectorAll(".btn-toggle-status").forEach((btn) => {
        btn.addEventListener("click", async () => {
            await toggleAdminUserStatus(btn.dataset.userId);
        });
    });
}

function renderAdminRecentFeed(recentUsers) {
    if (!adminFeedList) return;
    adminFeedList.innerHTML = "";

    if (!recentUsers || recentUsers.length === 0) {
        adminFeedList.innerHTML = '<div style="color: var(--text-muted); font-size: 0.8rem; text-align: center; padding: 20px;">No recent activity.</div>';
        return;
    }

    recentUsers.forEach((u) => {
        const initial = (u.username.charAt(0) || "U").toUpperCase();
        const isAdmin = u.role === "admin";
        const item = document.createElement("div");
        item.className = "feed-item";
        item.innerHTML = `
            <div class="feed-avatar" style="${isAdmin ? 'background: var(--accent-purple);' : ''}">${initial}</div>
            <div class="feed-content">
                <span class="feed-name">${escapeHtml(u.username)} <span class="role-badge-pill ${isAdmin ? 'role-admin-pill' : 'role-user-pill'}" style="font-size: 0.6rem; padding: 1px 5px;">${u.role.toUpperCase()}</span></span>
                <span class="feed-meta"><i class="fa-regular fa-envelope"></i> ${escapeHtml(u.email)}</span>
                <span class="feed-meta"><i class="fa-regular fa-calendar-plus"></i> Registered: ${escapeHtml(u.created_at || 'Just now')}</span>
            </div>
        `;
        adminFeedList.appendChild(item);
    });
}

async function updateAdminUserRole(userId, newRole) {
    try {
        const data = await apiJson(`/api/admin/user/${userId}/role`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ role: newRole }),
        });
        if (data.success) {
            await loadAdminDashboard();
        } else {
            alert(data.error || "Failed to update role");
        }
    } catch (err) {
        console.error("Error updating role:", err);
    }
}

async function toggleAdminUserStatus(userId) {
    try {
        const data = await apiJson(`/api/admin/user/${userId}/status`, { method: "POST" });
        if (data.success) {
            await loadAdminDashboard();
        } else {
            alert(data.error || "Failed to toggle status");
        }
    } catch (err) {
        console.error("Error toggling status:", err);
    }
}
