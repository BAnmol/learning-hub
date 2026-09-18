// ============================================================================
// Daily Tracker & Mastery Roadmap — streak, difficulty breakdown, activity
// heatmap, and the step-by-step roadmap grid.
// ============================================================================
import { apiJson, escapeHtml } from "./utils.js?v=8.0";
import { switchMode } from "./nav.js?v=8.0";
import { filterByStep } from "./studio.js?v=8.0";

let trackerStreakNum, trackerTotalSolved, trackerEasySolved, trackerMediumSolved, trackerHardSolved;
let trackerCalendarHeatmap, roadmapStepsGrid;
let cached = false;

function cacheDom() {
    trackerStreakNum = document.getElementById("tracker-streak-num");
    trackerTotalSolved = document.getElementById("tracker-total-solved");
    trackerEasySolved = document.getElementById("tracker-easy-solved");
    trackerMediumSolved = document.getElementById("tracker-medium-solved");
    trackerHardSolved = document.getElementById("tracker-hard-solved");
    trackerCalendarHeatmap = document.getElementById("tracker-calendar-heatmap");
    roadmapStepsGrid = document.getElementById("roadmap-steps-grid");
    cached = true;
}

export async function loadTrackerStats() {
    if (!cached) cacheDom();
    try {
        const data = await apiJson("/api/dsa/stats");
        if (data.success && data.stats) {
            renderTrackerStats(data.stats);
        }
    } catch (e) { /* non-fatal */ }
}

function renderTrackerStats(stats) {
    trackerStreakNum.textContent = stats.current_streak || 0;
    trackerTotalSolved.textContent = `${stats.total_solved || 0} / ${stats.total_available || 325}`;
    trackerEasySolved.textContent = `${stats.easy?.solved || 0} / ${stats.easy?.total || 0}`;
    trackerMediumSolved.textContent = `${stats.medium?.solved || 0} / ${stats.medium?.total || 0}`;
    trackerHardSolved.textContent = `${stats.hard?.solved || 0} / ${stats.hard?.total || 0}`;

    renderTrackerHeatmap(stats.activity_heatmap || {});
    renderRoadmapSteps(stats.steps || []);
}

function renderTrackerHeatmap(heatmapData) {
    trackerCalendarHeatmap.innerHTML = "";
    const totalDays = 182; // 26 weeks
    const today = new Date();

    for (let i = totalDays - 1; i >= 0; i--) {
        const d = new Date();
        d.setDate(today.getDate() - i);
        const dateKey = d.toISOString().split("T")[0];
        const entry = heatmapData[dateKey] || {};
        const count = (entry.solved || 0) + (entry.submissions || 0);

        let level = 0;
        if (count > 0 && count <= 2) level = 1;
        else if (count > 2 && count <= 5) level = 2;
        else if (count > 5 && count <= 10) level = 3;
        else if (count > 10) level = 4;

        const cell = document.createElement("div");
        cell.className = `heatmap-cell level-${level}`;
        cell.title = `${dateKey}: ${entry.solved || 0} solved, ${entry.submissions || 0} submissions`;
        trackerCalendarHeatmap.appendChild(cell);
    }
}

function renderRoadmapSteps(steps) {
    roadmapStepsGrid.innerHTML = "";
    steps.forEach((s) => {
        const card = document.createElement("div");
        card.className = "step-card";
        card.innerHTML = `
            <div class="step-card-header">
                <div>
                    <div class="step-name">${escapeHtml(s.step)}</div>
                    <div class="step-topic">${escapeHtml(s.topic)}</div>
                </div>
                <span class="step-pct-pill">${s.progress_pct}%</span>
            </div>
            <div class="step-progress-track">
                <div class="step-progress-fill" style="width: ${s.progress_pct}%"></div>
            </div>
            <div class="step-card-footer">
                <span>${s.solved_count} of ${s.total_problems} Solved</span>
                <span>${s.easy_count}E • ${s.medium_count}M • ${s.hard_count}H</span>
            </div>
        `;

        card.addEventListener("click", () => {
            switchMode("studio");
            filterByStep(s.step);
        });

        roadmapStepsGrid.appendChild(card);
    });
}
