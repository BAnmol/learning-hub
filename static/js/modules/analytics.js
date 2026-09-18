// ============================================================================
// Multi-Platform Analytics — LeetCode / CodeChef / Codeforces dashboards and
// the Unified Hub. Data only loads once the Analytics tab is actually shown
// (see onShow), not eagerly at boot.
// ============================================================================
import { apiJson, escapeHtml } from "./utils.js?v=8.0";

let platformBtns, searchForm, usernameInput, refreshBtn;
const analyticsViews = {};
let platformUsers = {};
const platformCache = { leetcode: null, codechef: null, codeforces: null };
let activePlatform = "leetcode";
let wired = false;

function cacheDom() {
    platformBtns = document.querySelectorAll(".platform-btn");
    searchForm = document.getElementById("search-form");
    usernameInput = document.getElementById("username-input");
    refreshBtn = document.getElementById("refresh-btn");

    analyticsViews.leetcode = document.getElementById("view-leetcode");
    analyticsViews.codechef = document.getElementById("view-codechef");
    analyticsViews.codeforces = document.getElementById("view-codeforces");
    analyticsViews.unified = document.getElementById("view-unified");

    platformUsers = {
        leetcode: document.body.dataset.leetcodeUser || localStorage.getItem("lc_user") || "lee215",
        codechef: document.body.dataset.codechefUser || localStorage.getItem("cc_user") || "tourist",
        codeforces: document.body.dataset.codeforcesUser || localStorage.getItem("cf_user") || "tourist",
    };
}

function switchPlatform(platform) {
    activePlatform = platform;
    platformBtns.forEach((b) => b.classList.toggle("active", b.dataset.platform === platform));

    if (platform === "unified") {
        searchForm.style.opacity = "0.5";
        usernameInput.disabled = true;
        usernameInput.placeholder = "Unified Hub";
        loadAllPlatforms();
        return;
    }

    searchForm.style.opacity = "1";
    usernameInput.disabled = false;
    usernameInput.placeholder = `Enter ${platform.charAt(0).toUpperCase() + platform.slice(1)} username...`;
    usernameInput.value = platformUsers[platform];

    showAnalyticsView(platform);
    if (platformCache[platform]) {
        renderPlatformView(platform, platformCache[platform]);
    } else {
        loadPlatformData(platform, platformUsers[platform]);
    }
}

async function loadPlatformData(platform, username, refresh = false) {
    try {
        const url = `/api/${platform}/${encodeURIComponent(username)}${refresh ? "?refresh=true" : ""}`;
        const data = await apiJson(url);
        if (data.success) {
            platformCache[platform] = data.data;
            showAnalyticsView(platform);
            renderPlatformView(platform, data.data);
        }
    } catch (e) { /* non-fatal */ }
}

async function loadAllPlatforms(refresh = false) {
    await Promise.allSettled([
        fetchPlatformQuietly("leetcode", platformUsers.leetcode, refresh),
        fetchPlatformQuietly("codechef", platformUsers.codechef, refresh),
        fetchPlatformQuietly("codeforces", platformUsers.codeforces, refresh),
    ]);
    showAnalyticsView("unified");
    renderUnifiedView();
}

async function fetchPlatformQuietly(platform, username, refresh) {
    if (!refresh && platformCache[platform]) return;
    try {
        const data = await apiJson(`/api/${platform}/${encodeURIComponent(username)}${refresh ? "?refresh=true" : ""}`);
        if (data.success) platformCache[platform] = data.data;
    } catch (e) { /* non-fatal */ }
}

function showAnalyticsView(platform) {
    Object.keys(analyticsViews).forEach((k) => {
        analyticsViews[k].classList.toggle("hidden", k !== platform);
    });
}

function renderPlatformView(platform, data) {
    if (platform === "leetcode") renderLeetCodeAnalytics(data);
    else if (platform === "codechef") renderCodeChefAnalytics(data);
    else if (platform === "codeforces") renderCodeforcesAnalytics(data);
}

function setSafeAvatar(imgId, url) {
    const el = document.getElementById(imgId);
    if (!el) return;
    if (url && typeof url === "string" && url.trim().startsWith("http")) {
        el.src = url.trim();
        el.style.display = "block";
    } else {
        el.removeAttribute("src");
        el.style.display = "none";
    }
}

function renderLeetCodeAnalytics(data) {
    const profile = data.profile || {};
    const acStats = data.ac_submissions || {};
    const totalStats = data.total_submissions || {};
    const allQ = data.all_questions_count || {};
    const contest = data.contest || {};
    const contestInfo = contest.contest_info || {};

    setSafeAvatar("lc-avatar", profile.userAvatar);
    document.getElementById("lc-realname").textContent = profile.realName || data.username;
    document.getElementById("lc-handle").textContent = `@${data.username}`;
    document.getElementById("lc-profile-link").href = `https://leetcode.com/${data.username}/`;

    const rankPill = document.getElementById("lc-rank-pill");
    if (profile.ranking) {
        rankPill.textContent = `#${profile.ranking.toLocaleString()}`;
        rankPill.classList.remove("hidden");
    } else {
        rankPill.classList.add("hidden");
    }

    document.getElementById("lc-bio").textContent = profile.aboutMe || "No bio provided.";
    document.getElementById("lc-pill-company").querySelector("span").textContent = profile.company || "Independent";
    document.getElementById("lc-pill-location").querySelector("span").textContent = profile.countryName || "Global";
    document.getElementById("lc-pill-reputation").querySelector("span").textContent = `Reputation: ${(profile.reputation || 0).toLocaleString()}`;

    document.getElementById("lc-streak").textContent = data.streak || 0;
    document.getElementById("lc-active-days").textContent = data.total_active_days || 0;

    const totalSolved = acStats.All ? acStats.All.count : 0;
    const totalAvail = allQ.All || 0;
    document.getElementById("lc-solved-num").textContent = totalSolved;
    document.getElementById("lc-available-num").textContent = `/ ${totalAvail}`;

    const totalSubs = totalStats.All ? totalStats.All.submissions : 0;
    const acSubs = acStats.All ? acStats.All.submissions : 0;
    const acc = totalSubs > 0 ? ((acSubs / totalSubs) * 100).toFixed(1) : 0;
    document.getElementById("lc-overall-acceptance").textContent = `${acc}%`;

    const circumference = 408.4;
    const frac = totalAvail > 0 ? totalSolved / totalAvail : 0;
    document.getElementById("lc-ring-all").style.strokeDashoffset = circumference - frac * circumference;

    renderLCDiff("easy", acStats.Easy, allQ.Easy, totalStats.Easy);
    renderLCDiff("medium", acStats.Medium, allQ.Medium, totalStats.Medium);
    renderLCDiff("hard", acStats.Hard, allQ.Hard, totalStats.Hard);

    if (contestInfo && contestInfo.attendedContestsCount > 0) {
        document.getElementById("lc-contest-rating").textContent = Math.round(contestInfo.rating || 0);
        document.getElementById("lc-contest-global-rank").textContent = contestInfo.globalRanking ? `#${contestInfo.globalRanking.toLocaleString()}` : "N/A";
        document.getElementById("lc-contest-top-pct").textContent = contestInfo.topPercentage ? `${contestInfo.topPercentage.toFixed(2)}%` : "N/A";
        document.getElementById("lc-contest-attended").textContent = contestInfo.attendedContestsCount || 0;
        const bPill = document.getElementById("lc-contest-badge");
        if (contestInfo.badge?.name) {
            bPill.textContent = contestInfo.badge.name;
            bPill.classList.remove("hidden");
        } else {
            bPill.classList.add("hidden");
        }
    }
}

function renderLCDiff(key, acItem, totalCount, totItem) {
    const solved = acItem?.count || 0;
    const total = totalCount || 0;
    const pct = total > 0 ? ((solved / total) * 100).toFixed(1) : 0;
    const subTot = totItem?.submissions || 0;
    const subAc = acItem?.submissions || 0;
    const acc = subTot > 0 ? ((subAc / subTot) * 100).toFixed(1) : 0;

    document.getElementById(`lc-${key}-count`).textContent = `${solved} / ${total}`;
    document.getElementById(`lc-${key}-bar`).style.width = `${pct}%`;
    document.getElementById(`lc-${key}-percent`).textContent = `${pct}% of total`;
    document.getElementById(`lc-${key}-acceptance`).textContent = `Acceptance: ${acc}%`;
}

function renderCodeChefAnalytics(data) {
    setSafeAvatar("cc-avatar", data.avatar);
    document.getElementById("cc-name").textContent = data.name || data.username;
    document.getElementById("cc-handle").textContent = `@${data.username}`;
    document.getElementById("cc-profile-link").href = data.profile_url || `https://www.codechef.com/users/${data.username}`;
    document.getElementById("cc-stars-pill").textContent = data.stars || "1★";
    document.getElementById("cc-division-badge").textContent = data.division || "Div 4";

    document.getElementById("cc-pill-country").querySelector("span").textContent = data.country || "Global";
    document.getElementById("cc-pill-grank").querySelector("span").textContent = `Global Rank: #${data.global_rank || "N/A"}`;
    document.getElementById("cc-pill-crank").querySelector("span").textContent = `Country Rank: #${data.country_rank || "N/A"}`;

    document.getElementById("cc-rating").textContent = data.rating || 0;
    document.getElementById("cc-peak-rating").textContent = data.highest_rating || 0;
    document.getElementById("cc-fully-solved").textContent = data.fully_solved || 0;
    document.getElementById("cc-partially-solved").textContent = data.partially_solved || 0;
    document.getElementById("cc-total-solved").textContent = data.total_solved || 0;
    document.getElementById("cc-contests-count").textContent = data.contests_count || 0;

    const tbody = document.getElementById("cc-contest-history-tbody");
    tbody.innerHTML = "";
    (data.contest_history || []).slice().reverse().forEach((c) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><strong>${escapeHtml(c.name || c.code || "Contest")}</strong></td>
            <td style="color: var(--text-muted); font-size: 0.85rem;">${escapeHtml(c.date || "N/A")}</td>
            <td>#${escapeHtml(String(c.rank || "N/A"))}</td>
            <td><strong class="text-green">${escapeHtml(String(c.rating || "N/A"))}</strong></td>
        `;
        tbody.appendChild(tr);
    });
}

function renderCodeforcesAnalytics(data) {
    setSafeAvatar("cf-avatar", data.avatar);
    document.getElementById("cf-name").textContent = data.name || data.username;
    document.getElementById("cf-handle").textContent = `@${data.username}`;
    document.getElementById("cf-profile-link").href = data.profile_url || `https://codeforces.com/profile/${data.username}`;
    document.getElementById("cf-rank-pill").textContent = data.rank || "Unrated";
    document.getElementById("cf-pill-location").querySelector("span").textContent = `${data.city || ""}, ${data.country || "Global"}`.replace(/^,\s*/, "");
    document.getElementById("cf-pill-org").querySelector("span").textContent = data.organization || "Independent";
    document.getElementById("cf-pill-contrib").querySelector("span").textContent = `Contribution: ${data.contribution || 0}`;

    document.getElementById("cf-rating").textContent = data.rating || 0;
    document.getElementById("cf-max-rating").textContent = data.max_rating || 0;
    document.getElementById("cf-max-rank-label").textContent = `Max: ${data.max_rank || ""}`;
    document.getElementById("cf-solved-count").textContent = data.total_solved || 0;
    document.getElementById("cf-contests-count").textContent = data.contests_count || 0;
    document.getElementById("cf-friends-count").textContent = data.friend_of_count || 0;
    document.getElementById("cf-max-rank").textContent = data.max_rank || "--";

    const tbody = document.getElementById("cf-recent-subs-tbody");
    tbody.innerHTML = "";
    (data.recent_solved || []).forEach((p) => {
        const tr = document.createElement("tr");
        const tags = (p.tags || []).slice(0, 3).map((t) => `<span class="topic-count" style="margin-right:4px;">${t}</span>`).join("");
        tr.innerHTML = `
            <td><strong>${escapeHtml(p.name)}</strong></td>
            <td><strong class="text-gold">${p.rating || "Unrated"}</strong></td>
            <td>${tags}</td>
            <td><a href="${p.link}" target="_blank" class="problem-link">Solve <i class="fa-solid fa-arrow-up-right-from-square"></i></a></td>
        `;
        tbody.appendChild(tr);
    });
}

function renderUnifiedView() {
    const lc = platformCache.leetcode;
    const cc = platformCache.codechef;
    const cf = platformCache.codeforces;

    if (lc) {
        document.getElementById("uni-lc-username").textContent = `@${lc.username}`;
        document.getElementById("uni-lc-solved").textContent = lc.ac_submissions?.All?.count || 0;
        document.getElementById("uni-lc-rating").textContent = Math.round(lc.contest?.contest_info?.rating || 0) || "Unrated";
        document.getElementById("uni-lc-rank").textContent = lc.profile?.ranking ? `#${lc.profile.ranking.toLocaleString()}` : "Unranked";
        document.getElementById("uni-lc-streak").textContent = `${lc.streak || 0} days`;
    }
    if (cc) {
        document.getElementById("uni-cc-username").textContent = `@${cc.username}`;
        document.getElementById("uni-cc-stars").textContent = `${cc.stars} (${cc.division})`;
        document.getElementById("uni-cc-rating").textContent = cc.rating || 0;
        document.getElementById("uni-cc-peak").textContent = cc.highest_rating || 0;
        document.getElementById("uni-cc-contests").textContent = cc.contests_count || 0;
    }
    if (cf) {
        document.getElementById("uni-cf-username").textContent = `@${cf.username}`;
        document.getElementById("uni-cf-rank").textContent = cf.rank || "Unrated";
        document.getElementById("uni-cf-rating").textContent = cf.rating || 0;
        document.getElementById("uni-cf-max").textContent = `${cf.max_rating} (${cf.max_rank})`;
        document.getElementById("uni-cf-solved").textContent = cf.total_solved || 0;
    }
}

function wireEvents() {
    platformBtns.forEach((btn) => {
        btn.addEventListener("click", () => switchPlatform(btn.dataset.platform));
    });

    searchForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const username = usernameInput.value.trim();
        if (!username) return;
        platformUsers[activePlatform] = username;
        localStorage.setItem(`${activePlatform}_user`, username);
        loadPlatformData(activePlatform, username, true);
    });

    refreshBtn.addEventListener("click", () => {
        const username = usernameInput.value.trim() || platformUsers[activePlatform];
        if (username) loadPlatformData(activePlatform, username, true);
    });
}

/** Wire listeners once. Safe to call at app boot — does not fetch anything. */
export function initAnalytics() {
    if (wired) return;
    cacheDom();
    wireEvents();
    wired = true;
}

/** Called every time the Analytics tab becomes active — loads on first visit only. */
export function onShow() {
    if (!wired) initAnalytics();
    if (!platformCache[activePlatform]) {
        loadPlatformData(activePlatform, platformUsers[activePlatform]);
    }
}
