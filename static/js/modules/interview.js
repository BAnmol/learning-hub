// ============================================================================
// Timed AI Mock Interview Mode (45-Minute Technical Round)
// Handles mandatory candidate intake, real-time 45m urgency countdown,
// AI interviewer dialogue & hints, code test sandbox, and FAANG scorecard.
// ============================================================================

import { formatMarkdown, escapeHtml } from "./utils.js?v=8.0";
import { createPythonEditor, getEditorValue, setEditorValue, setEditorReadOnly, refreshEditorTheme } from "./editor.js";

// Session State
let interviewSession = null;
let timerInterval = null;
let timeRemaining = 2700; // 45:00 in seconds
let totalDuration = 2700;
let hintsUsed = 0;
let isSubmitting = false;
let isPaused = false;
let cmInterviewView = null; // CodeMirror 6 EditorView for the interview editor

/**
 * Initialize Mock Interview module event listeners.
 */
export function initInterview() {
    // Keep the interview code editor's syntax theme in sync with the
    // site-wide light/dark toggle (the editor is created once and reused,
    // so it doesn't pick up theme changes on its own).
    window.addEventListener("dsa-theme-change", () => refreshEditorTheme(cmInterviewView));

    const intakeForm = document.getElementById("interview-intake-form");
    if (intakeForm) {
        intakeForm.addEventListener("submit", handleIntakeSubmit);
    }

    // View History Buttons
    const btnHistory = document.getElementById("btn-view-interview-history");
    if (btnHistory) {
        btnHistory.addEventListener("click", () => showHistoryView());
    }

    const btnScorecardHistory = document.getElementById("btn-scorecard-history");
    if (btnScorecardHistory) {
        btnScorecardHistory.addEventListener("click", () => showHistoryView());
    }

    const btnBackIntake = document.getElementById("btn-history-back-intake");
    if (btnBackIntake) {
        btnBackIntake.addEventListener("click", () => showIntakeView());
    }

    const btnRetake = document.getElementById("btn-scorecard-retake");
    if (btnRetake) {
        btnRetake.addEventListener("click", () => showIntakeView());
    }

    // Pause / Resume Controls
    const btnPause = document.getElementById("btn-pause-interview");
    if (btnPause) {
        btnPause.addEventListener("click", () => togglePauseInterview());
    }

    const btnResumeOverlay = document.getElementById("btn-resume-overlay");
    if (btnResumeOverlay) {
        btnResumeOverlay.addEventListener("click", () => togglePauseInterview(false));
    }

    // Restart Test Controls
    const btnRestart = document.getElementById("btn-restart-interview");
    if (btnRestart) {
        btnRestart.addEventListener("click", () => restartInterview());
    }

    const btnRestartOverlay = document.getElementById("btn-restart-overlay");
    if (btnRestartOverlay) {
        btnRestartOverlay.addEventListener("click", () => restartInterview());
    }

    // Tab switcher between Problem Statement and AI Interviewer in Room
    document.querySelectorAll(".pane-tab-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            const ptab = e.currentTarget.dataset.ptab;
            switchPaneTab(ptab);
        });
    });

    // Hints Dropdown
    const btnRequestHint = document.getElementById("btn-request-hint");
    const hintsMenu = document.getElementById("hints-menu-dropdown");
    if (btnRequestHint && hintsMenu) {
        btnRequestHint.addEventListener("click", (e) => {
            e.stopPropagation();
            if (isPaused) return;
            hintsMenu.classList.toggle("hidden");
        });

        document.addEventListener("click", () => {
            hintsMenu.classList.add("hidden");
        });

        document.querySelectorAll(".hints-menu-item").forEach((item) => {
            item.addEventListener("click", (e) => {
                e.stopPropagation();
                if (isPaused) return;
                const tier = parseInt(item.dataset.tier, 10);
                hintsMenu.classList.add("hidden");
                requestProgressiveHint(tier);
            });
        });
    }

    // Chat Form
    const chatForm = document.getElementById("interview-chat-form");
    if (chatForm) {
        chatForm.addEventListener("submit", handleChatSubmit);
    }

    // Quick Pitch Prompt Chips
    document.querySelectorAll(".pitch-chip").forEach((chip) => {
        chip.addEventListener("click", () => {
            if (isPaused) return;
            const text = chip.dataset.text;
            const chatInput = document.getElementById("interview-chat-input");
            if (chatInput) {
                chatInput.value = text;
                chatInput.focus();
            }
        });
    });

    // Code Sandbox Run Tests
    const btnRunTests = document.getElementById("btn-interview-run-code");
    if (btnRunTests) {
        btnRunTests.addEventListener("click", () => {
            if (isPaused) return;
            handleRunTests();
        });
    }

    // Reset Starter Code
    const btnResetCode = document.getElementById("btn-interview-reset-code");
    if (btnResetCode) {
        btnResetCode.addEventListener("click", () => {
            if (isPaused) return;
            if (interviewSession && interviewSession.problem && interviewSession.problem.starter_code) {
                if (confirm("Reset editor back to initial starter boilerplate? Your changes will be replaced.")) {
                    const starter = interviewSession.problem.starter_code;
                    if (cmInterviewView) {
                        setEditorValue(cmInterviewView, starter);
                    } else {
                        const ta = document.getElementById("interview-code-textarea");
                        if (ta) ta.value = starter;
                    }
                }
            }
        });
    }

    // Submit Final Round Button
    const btnFinish = document.getElementById("btn-finish-interview");
    if (btnFinish) {
        btnFinish.addEventListener("click", () => {
            if (confirm("Are you ready to submit your 45-minute technical interview for final FAANG grading?")) {
                finishInterview(false);
            }
        });
    }
}


/**
 * Called when user navigates to the Mock Interview mode tab.
 */
export function onShow() {
    // If not currently in an active interview session, show intake screen
    if (!interviewSession) {
        showIntakeView();
    }
}

// ============================================================================
// View Switchers
// ============================================================================

function hideAllInterviewViews() {
    document.getElementById("interview-view-intake")?.classList.add("hidden");
    document.getElementById("interview-view-room")?.classList.add("hidden");
    document.getElementById("interview-view-scorecard")?.classList.add("hidden");
    document.getElementById("interview-view-history")?.classList.add("hidden");
}

function showIntakeView() {
    stopTimer();
    isPaused = false;
    document.getElementById("interview-workspace-container")?.classList.remove("is-test-paused");
    document.getElementById("interview-pause-overlay")?.classList.add("hidden");
    interviewSession = null;
    hideAllInterviewViews();
    document.getElementById("interview-view-intake")?.classList.remove("hidden");
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function showRoomView() {
    hideAllInterviewViews();
    document.getElementById("interview-view-room")?.classList.remove("hidden");
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function showScorecardView() {
    stopTimer();
    isPaused = false;
    document.getElementById("interview-workspace-container")?.classList.remove("is-test-paused");
    document.getElementById("interview-pause-overlay")?.classList.add("hidden");
    hideAllInterviewViews();
    document.getElementById("interview-view-scorecard")?.classList.remove("hidden");
    window.scrollTo({ top: 0, behavior: "smooth" });
}


function showHistoryView() {
    hideAllInterviewViews();
    document.getElementById("interview-view-history")?.classList.remove("hidden");
    window.scrollTo({ top: 0, behavior: "smooth" });
    loadInterviewHistory();
}

function switchPaneTab(ptab) {
    document.querySelectorAll(".pane-tab-btn").forEach((b) => {
        b.classList.toggle("active", b.dataset.ptab === ptab);
    });

    const probPane = document.getElementById("pane-content-problem");
    const chatPane = document.getElementById("pane-content-chat");

    if (ptab === "problem") {
        probPane?.classList.remove("hidden");
        chatPane?.classList.add("hidden");
    } else {
        probPane?.classList.add("hidden");
        chatPane?.classList.remove("hidden");
        // Clear unread dot
        document.getElementById("chat-unread-dot")?.classList.add("hidden");
        // Scroll dialogue to bottom
        const stream = document.getElementById("interview-chat-stream");
        if (stream) stream.scrollTop = stream.scrollHeight;
    }
}

// ============================================================================
// Intake Submission & Validation Gate
// ============================================================================

async function handleIntakeSubmit(e) {
    e.preventDefault();

    const errorBanner = document.getElementById("intake-error-banner");
    const errorText = document.getElementById("intake-error-text");
    errorBanner?.classList.add("hidden");

    const role = document.getElementById("intake-role")?.value.trim();
    const company = document.getElementById("intake-company")?.value.trim();
    const exp = document.getElementById("intake-experience")?.value.trim();
    const skills = document.getElementById("intake-skills")?.value.trim();
    const qual = document.getElementById("intake-qualification")?.value.trim();

    // STRICT VALIDATION: Without details the test MUST NOT start!
    if (!role || !company || !exp || !skills || !qual) {
        if (errorBanner && errorText) {
            errorText.textContent = "All candidate details (Target Role, Company Tier, Experience Level, Focus Skills, and Qualification) are strictly mandatory before launching the technical round.";
            errorBanner.classList.remove("hidden");
            errorBanner.scrollIntoView({ behavior: "smooth", block: "center" });
        }
        return;
    }

    const startBtn = document.getElementById("btn-start-interview");
    const origHtml = startBtn ? startBtn.innerHTML : "";
    if (startBtn) {
        startBtn.disabled = true;
        startBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Calibrating Interview Round...`;
    }

    const intakePayload = {
        target_role: role,
        target_company: company,
        experience_level: exp,
        focus_skills: skills,
        qualification: qual,
    };

    try {
        const resp = await fetch("/api/interview/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ intake: intakePayload }),
        });

        const data = await resp.json();
        if (!resp.ok || !data.success) {
            throw new Error(data.error || "Failed to initialize interview round.");
        }

        // Initialize active session
        interviewSession = data;
        hintsUsed = 0;
        timeRemaining = data.duration_seconds || 2700;
        totalDuration = timeRemaining;

        setupInterviewRoom(data);
        showRoomView();
        startTimer();
    } catch (err) {
        if (errorBanner && errorText) {
            errorText.textContent = err.message || "Failed to start interview.";
            errorBanner.classList.remove("hidden");
        }
    } finally {
        if (startBtn) {
            startBtn.disabled = false;
            startBtn.innerHTML = origHtml;
        }
    }
}

// ============================================================================
// Active Interview Room Setup
// ============================================================================

function setupInterviewRoom(data) {
    window.currentInterviewSessionId = data.session_id;
    const intake = data.intake || {};
    const prob = data.problem || {};

    // Header candidate chips
    document.getElementById("room-role-display").textContent = intake.target_role || "Candidate";
    document.getElementById("room-company-display").textContent = intake.target_company?.split("(")[0].trim() || "Tech";
    document.getElementById("room-level-display").textContent = intake.experience_level?.split("(")[0].trim() || "L3/L4";

    // Hints badge
    document.getElementById("room-hints-num").textContent = "0";

    // Problem details
    document.getElementById("interview-problem-title").textContent = prob.title || "Technical Problem";
    const diffPill = document.getElementById("interview-problem-diff");
    if (diffPill) {
        diffPill.textContent = prob.difficulty || "Medium";
        diffPill.className = `difficulty-pill ${(prob.difficulty || "medium").toLowerCase()}`;
    }
    document.getElementById("interview-problem-step").textContent = prob.step || "DSA";
    document.getElementById("interview-problem-topic").textContent = prob.topic || "Core Algorithm";

    // Markdown problem description
    const descBox = document.getElementById("interview-problem-desc");
    if (descBox) {
        descBox.innerHTML = formatMarkdown(prob.description || "No description provided.");
    }

    // Method signature & constraints
    const sigEl = document.getElementById("interview-method-signature");
    if (sigEl) {
        sigEl.textContent = prob.signature || `solve(self, ...):`;
    }

    const constraintsBox = document.getElementById("interview-constraints-container");
    if (constraintsBox) {
        if (prob.constraints && prob.constraints.length > 0) {
            constraintsBox.innerHTML = `<strong>Constraints:</strong><ul>${prob.constraints.map((c) => `<li><code>${c}</code></li>`).join("")}</ul>`;
        } else {
            constraintsBox.innerHTML = `<em>Standard LeetCode memory &amp; execution constraints apply.</em>`;
        }
    }

    // Starter code in editor (CodeMirror 6)
    const cmHost = document.getElementById("cm-interview-editor");
    const starterCode = prob.starter_code || "# Write your Python solution here\n";
    if (cmHost && !cmInterviewView) {
        // First mount — create the editor
        cmInterviewView = createPythonEditor(cmHost, {
            initialValue: starterCode,
            onRunShortcut: () => handleRunTests(),
        });
    } else if (cmInterviewView) {
        // Subsequent interview start — reset the content
        setEditorValue(cmInterviewView, starterCode);
    } else {
        // Fallback for environments without the CM host
        const editor = document.getElementById("interview-code-textarea");
        if (editor) editor.value = starterCode;
    }

    // Results panel reset
    const resultsBody = document.getElementById("interview-test-results-body");
    if (resultsBody) {
        resultsBody.innerHTML = `<span class="results-placeholder">Click <strong>Run Tests</strong> to verify your code against problem test cases during the interview.</span>`;
    }
    const statusBadge = document.getElementById("interview-tests-status-badge");
    if (statusBadge) {
        statusBadge.textContent = "Idle";
        statusBadge.className = "badge-status-idle";
    }

    // Render dialogue
    renderChatMessages(data.transcript || []);
    switchPaneTab("problem");
}

// ============================================================================
// 45:00 Digital Urgency Countdown Clock
// ============================================================================

function startTimer() {
    stopTimer();
    updateClockDisplay();

    timerInterval = setInterval(() => {
        timeRemaining -= 1;
        updateClockDisplay();

        if (timeRemaining <= 0) {
            stopTimer();
            // HEAT OF THE REAL TEST: Time expired auto-submission!
            alert("45-Minute Technical Interview Time is UP!\n\nYour active solution is being automatically submitted for FAANG evaluation.");
            finishInterview(true);
        }
    }, 1000);
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

/** Called on logout so a running 45-minute countdown can't fire an auto-submit
 *  (which would 401) against a session that no longer exists. */
export function stopActiveTimers() {
    stopTimer();
}

function updateClockDisplay() {
    const clockEl = document.getElementById("interview-clock-display");
    const subtextEl = document.getElementById("interview-clock-subtext");
    const timerWidget = document.getElementById("interview-timer-widget");
    if (!clockEl) return;

    const mins = Math.floor(Math.max(0, timeRemaining) / 60);
    const secs = Math.max(0, timeRemaining) % 60;
    const formatted = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
    clockEl.textContent = formatted;

    // Visual urgency states
    if (timeRemaining <= 300) {
        // Critical: < 5 mins
        timerWidget?.classList.add("timer-state-critical");
        timerWidget?.classList.remove("timer-state-urgent", "timer-state-normal");
        if (subtextEl) subtextEl.textContent = "CRITICAL: Final Minutes!";
    } else if (timeRemaining <= 900) {
        // Urgent: 5 to 15 mins
        timerWidget?.classList.add("timer-state-urgent");
        timerWidget?.classList.remove("timer-state-critical", "timer-state-normal");
        if (subtextEl) subtextEl.textContent = "Urgent: Wrap Up Code";
    } else {
        // Normal: > 15 mins
        timerWidget?.classList.add("timer-state-normal");
        timerWidget?.classList.remove("timer-state-critical", "timer-state-urgent");
        if (subtextEl) subtextEl.textContent = "Time Remaining";
    }
}

// ============================================================================
// Pause / Resume & Restart Test Controls
// ============================================================================

export async function togglePauseInterview(forcedState = null) {
    if (!interviewSession) return;

    const shouldPause = forcedState !== null ? forcedState : !isPaused;
    isPaused = shouldPause;

    const workspaceContainer = document.getElementById("interview-workspace-container");
    const pauseOverlay = document.getElementById("interview-pause-overlay");
    const pauseTimeDisplay = document.getElementById("pause-time-left-display");
    const codeTextarea = document.getElementById("interview-code-textarea");
    const btnPause = document.getElementById("btn-pause-interview");
    const btnPauseText = document.getElementById("btn-pause-text");
    const subtextEl = document.getElementById("interview-clock-subtext");

    const mins = Math.floor(Math.max(0, timeRemaining) / 60);
    const secs = Math.max(0, timeRemaining) % 60;
    const formatted = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;

    if (isPaused) {
        stopTimer();
        workspaceContainer?.classList.add("is-test-paused");
        pauseOverlay?.classList.remove("hidden");
        if (pauseTimeDisplay) pauseTimeDisplay.textContent = formatted;
        // CodeMirror: make editor read-only when paused
        if (cmInterviewView) {
            setEditorReadOnly(cmInterviewView, true);
        } else if (codeTextarea) {
            codeTextarea.readOnly = true;
        }

        if (btnPause) {
            btnPause.innerHTML = `<i class="fa-solid fa-play text-green"></i> <span id="btn-pause-text">Resume</span>`;
        }
        if (subtextEl) subtextEl.textContent = "TEST PAUSED";
    } else {
        workspaceContainer?.classList.remove("is-test-paused");
        pauseOverlay?.classList.add("hidden");
        // CodeMirror: re-enable editing when resumed
        if (cmInterviewView) {
            setEditorReadOnly(cmInterviewView, false);
        } else if (codeTextarea) {
            codeTextarea.readOnly = false;
        }

        if (btnPause) {
            btnPause.innerHTML = `<i class="fa-solid fa-pause"></i> <span id="btn-pause-text">Pause</span>`;
        }
        updateClockDisplay();
        startTimer();
    }
}

export function restartInterview() {
    if (!interviewSession) return;

    const confirmed = confirm(
        "Are you sure you want to restart this 45-minute technical test?\n\n" +
        "• Timer will reset back to 45:00\n" +
        "• Code editor will restore initial starter code\n" +
        "• Hint count and test console results will be cleared\n\n" +
        "Click OK to restart the test."
    );

    if (!confirmed) return;

    stopTimer();
    timeRemaining = totalDuration;
    hintsUsed = 0;

    const hintsNum = document.getElementById("room-hints-num");
    if (hintsNum) hintsNum.textContent = "0";

    const starterCode = interviewSession.problem?.starter_code || "# Write your Python solution here\n";
    if (cmInterviewView) {
        setEditorValue(cmInterviewView, starterCode);
    } else {
        const editor = document.getElementById("interview-code-textarea");
        if (editor) editor.value = starterCode;
    }

    // Reset console
    const resultsBody = document.getElementById("interview-test-results-body");
    if (resultsBody) {
        resultsBody.innerHTML = `<span class="results-placeholder">Click <strong>Run Tests</strong> to verify your code against problem test cases during the interview.</span>`;
    }
    const statusBadge = document.getElementById("interview-tests-status-badge");
    if (statusBadge) {
        statusBadge.textContent = "Idle";
        statusBadge.className = "badge-status-idle";
    }

    // Unpause if paused
    if (isPaused) {
        togglePauseInterview(false);
    } else {
        updateClockDisplay();
        startTimer();
    }
}


// ============================================================================
// Interviewer Chat & Dialogue
// ============================================================================

function renderChatMessages(transcript) {
    const stream = document.getElementById("interview-chat-stream");
    if (!stream) return;

    stream.innerHTML = "";
    transcript.forEach((msg) => {
        const msgDiv = document.createElement("div");
        const role = msg.role;

        if (role === "system") {
            msgDiv.className = "chat-msg chat-msg-system";
            msgDiv.innerHTML = `<span class="system-tag">${msg.text}</span>`;
        } else if (role === "user") {
            msgDiv.className = "chat-msg chat-msg-user";
            msgDiv.innerHTML = `
                <div class="msg-bubble user-bubble">
                    <div class="msg-header"><i class="fa-solid fa-user"></i> You <span class="msg-time">${msg.timestamp || ""}</span></div>
                    <div class="msg-text">${escapeHtml(msg.text)}</div>
                </div>
            `;
        } else {
            msgDiv.className = "chat-msg chat-msg-interviewer";
            msgDiv.innerHTML = `
                <div class="msg-bubble interviewer-bubble">
                    <div class="msg-header"><i class="fa-solid fa-user-tie text-purple"></i> AI Interviewer <span class="msg-time">${msg.timestamp || ""}</span></div>
                    <div class="msg-text">${formatMarkdown(msg.text)}</div>
                </div>
            `;
        }
        stream.appendChild(msgDiv);
    });

    stream.scrollTop = stream.scrollHeight;
}

async function handleChatSubmit(e) {
    e.preventDefault();
    if (!interviewSession || isPaused) return;

    const input = document.getElementById("interview-chat-input");
    const message = input ? input.value.trim() : "";
    if (!message) return;

    input.value = "";
    const currentCode = cmInterviewView ? getEditorValue(cmInterviewView) : (document.getElementById("interview-code-textarea")?.value || "");

    // Optimistically render user message
    const nowTime = new Date().toTimeString().split(" ")[0];
    const stream = document.getElementById("interview-chat-stream");
    if (stream) {
        const userDiv = document.createElement("div");
        userDiv.className = "chat-msg chat-msg-user";
        userDiv.innerHTML = `
            <div class="msg-bubble user-bubble">
                <div class="msg-header"><i class="fa-solid fa-user"></i> You <span class="msg-time">${nowTime}</span></div>
                <div class="msg-text">${escapeHtml(message)}</div>
            </div>
        `;
        stream.appendChild(userDiv);

        // Typing indicator
        const typingDiv = document.createElement("div");
        typingDiv.id = "interviewer-typing-indicator";
        typingDiv.className = "chat-msg chat-msg-interviewer";
        typingDiv.innerHTML = `
            <div class="msg-bubble interviewer-bubble">
                <div class="msg-header"><i class="fa-solid fa-user-tie text-purple"></i> AI Interviewer</div>
                <div class="msg-text"><i class="fa-solid fa-ellipsis fa-fade"></i> Evaluating response...</div>
            </div>
        `;
        stream.appendChild(typingDiv);
        stream.scrollTop = stream.scrollHeight;
    }

    try {
        const resp = await fetch("/api/interview/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: interviewSession.session_id,
                message: message,
                message_type: "chat",
                current_code: currentCode,
            }),
        });

        const data = await resp.json();
        document.getElementById("interviewer-typing-indicator")?.remove();

        if (resp.ok && data.success && data.transcript) {
            renderChatMessages(data.transcript);
        }
    } catch (err) {
        document.getElementById("interviewer-typing-indicator")?.remove();
        console.error("Chat error:", err);
    }
}

// ============================================================================
// 3-Tier Progressive Hint System
// ============================================================================

async function requestProgressiveHint(tier) {
    if (!interviewSession) return;

    const penalties = { 1: 5, 2: 15, 3: 25 };
    const tierNames = { 1: "Tier 1: Gentle Nudge", 2: "Tier 2: Structural Clue", 3: "Tier 3: Algorithmic Strategy" };
    const penalty = penalties[tier] || 10;
    const name = tierNames[tier] || `Tier ${tier}`;

    const confirmed = confirm(
        `Request ${name}?\n\n` +
        `Penalty Notice: Using this hint will deduct -${penalty} points from your final evaluation scorecard.\n\n` +
        `Do you want to proceed?`
    );

    if (!confirmed) return;

    const currentCode = cmInterviewView ? getEditorValue(cmInterviewView) : (document.getElementById("interview-code-textarea")?.value || "");

    try {
        const resp = await fetch("/api/interview/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: interviewSession.session_id,
                message_type: "hint",
                hint_level: tier,
                current_code: currentCode,
            }),
        });

        const data = await resp.json();
        if (resp.ok && data.success) {
            hintsUsed = data.hints_used;
            document.getElementById("room-hints-num").textContent = String(hintsUsed);

            if (data.transcript) {
                renderChatMessages(data.transcript);
            }

            // Switch to Interviewer tab and flash unread indicator
            switchPaneTab("chat");
        } else {
            alert(data.error || "Failed to generate hint.");
        }
    } catch (err) {
        console.error("Hint request failed:", err);
    }
}

// ============================================================================
// Code Execution & Testing Sandbox
// ============================================================================

async function handleRunTests() {
    if (!interviewSession) return;

    const runBtn = document.getElementById("btn-interview-run-code");
    const statusBadge = document.getElementById("interview-tests-status-badge");
    const resultsBody = document.getElementById("interview-test-results-body");
    const code = cmInterviewView ? getEditorValue(cmInterviewView) : (document.getElementById("interview-code-textarea")?.value || "");

    if (runBtn) {
        runBtn.disabled = true;
        runBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Running...`;
    }
    if (statusBadge) {
        statusBadge.textContent = "Evaluating...";
        statusBadge.className = "badge-status-running";
    }

    const timeSpent = totalDuration - timeRemaining;

    try {
        const resp = await fetch("/api/interview/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: interviewSession.session_id,
                code: code,
                time_spent_seconds: timeSpent,
            }),
        });

        const data = await resp.json();
        if (!resp.ok || !data.success) {
            throw new Error(data.error || "Execution failed.");
        }

        const res = data.result || {};
        renderTestResults(res);
    } catch (err) {
        if (resultsBody) {
            resultsBody.innerHTML = `<div class="test-error-block"><i class="fa-solid fa-triangle-exclamation"></i> ${escapeHtml(err.message || "Error running code.")}</div>`;
        }
        if (statusBadge) {
            statusBadge.textContent = "Error";
            statusBadge.className = "badge-status-fail";
        }
    } finally {
        if (runBtn) {
            runBtn.disabled = false;
            runBtn.innerHTML = `<i class="fa-solid fa-play"></i> Run Tests`;
        }
    }
}

function renderTestResults(res) {
    const statusBadge = document.getElementById("interview-tests-status-badge");
    const resultsBody = document.getElementById("interview-test-results-body");
    if (!resultsBody) return;

    const passed = Boolean(res.passed);
    const testsPassed = res.tests_passed || 0;
    const testsTotal = res.tests_total || 0;
    const execTime = res.execution_time_ms ? `${res.execution_time_ms.toFixed(1)} ms` : "--";
    const errorMsg = res.error || "";

    if (statusBadge) {
        if (passed) {
            statusBadge.textContent = "Passed";
            statusBadge.className = "badge-status-pass";
        } else {
            statusBadge.textContent = "Failed";
            statusBadge.className = "badge-status-fail";
        }
    }

    let html = `
        <div class="test-results-summary ${passed ? "pass" : "fail"}">
            <div class="summary-stat">
                <i class="fa-solid ${passed ? "fa-circle-check text-green" : "fa-circle-xmark text-red"}"></i>
                <span><strong>${testsPassed} / ${testsTotal}</strong> Tests Passed</span>
            </div>
            <div class="summary-stat">
                <i class="fa-solid fa-stopwatch text-cyan"></i>
                <span>Runtime: <strong>${execTime}</strong></span>
            </div>
        </div>
    `;

    if (errorMsg) {
        html += `
            <div class="test-trace-box">
                <div class="trace-title"><i class="fa-solid fa-bug"></i> Traceback / Runtime Error:</div>
                <pre><code>${escapeHtml(errorMsg)}</code></pre>
            </div>
        `;
    }

    if (res.output) {
        html += `
            <div class="test-stdout-box">
                <div class="stdout-title"><i class="fa-solid fa-terminal"></i> Standard Output:</div>
                <pre><code>${escapeHtml(res.output)}</code></pre>
            </div>
        `;
    }

    resultsBody.innerHTML = html;
}

// ============================================================================
// Final Submission & Scorecard Rendering
// ============================================================================

async function finishInterview(isAutoSubmit = false) {
    if (!interviewSession || isSubmitting) return;
    isSubmitting = true;

    stopTimer();
    const code = cmInterviewView ? getEditorValue(cmInterviewView) : (document.getElementById("interview-code-textarea")?.value || "");
    const timeSpent = Math.max(1, totalDuration - timeRemaining);
    const status = isAutoSubmit ? "timed_out" : "completed";

    // Show loading overlay or button state
    const submitBtn = document.getElementById("btn-finish-interview");
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Grading Round...`;
    }

    try {
        const resp = await fetch("/api/interview/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: interviewSession.session_id,
                code: code,
                time_spent_seconds: timeSpent,
                status: status,
            }),
        });

        const data = await resp.json();
        if (!resp.ok || !data.success) {
            throw new Error(data.error || "Failed to submit interview.");
        }

        renderScorecard(data.scorecard, data.test_result);
        showScorecardView();
    } catch (err) {
        alert(`Error submitting interview: ${err.message || err}`);
    } finally {
        isSubmitting = false;
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<i class="fa-solid fa-flag-checkered"></i> Submit Final Round`;
        }
    }
}

function renderScorecard(card, testRes) {
    if (!card) return;

    const score = card.score || 0;
    const decision = card.hire_decision || "LEAN HIRE";
    const timeSpent = card.time_spent_seconds || 0;
    const mins = Math.floor(timeSpent / 60);
    const secs = timeSpent % 60;
    const timeStr = `${mins}m ${secs}s`;

    // Overall Score Circle
    const scoreCircle = document.getElementById("scorecard-overall-score");
    if (scoreCircle) {
        scoreCircle.textContent = String(score);
    }

    // Hire Decision Badge
    const decisionBadge = document.getElementById("scorecard-decision-badge");
    if (decisionBadge) {
        decisionBadge.textContent = decision;
        let colorClass = "decision-lean-hire";
        if (decision === "STRONG HIRE") colorClass = "decision-strong-hire";
        else if (decision === "LEAN NO HIRE") colorClass = "decision-lean-no-hire";
        else if (decision === "NO HIRE") colorClass = "decision-no-hire";
        decisionBadge.className = `decision-pill ${colorClass}`;
    }

    // Telemetry
    document.getElementById("scorecard-time-spent").textContent = timeStr;
    document.getElementById("scorecard-tests-passed").textContent = `${card.tests_passed || 0} / ${card.tests_total || 0}`;
    document.getElementById("scorecard-hints-used").textContent = String(card.hints_used || 0);

    // Rubric Scores
    const rubric = card.rubric_scores || {};
    setRubricDimension("ps", rubric.problem_solving || 0);
    setRubricDimension("eff", rubric.efficiency || 0);
    setRubricDimension("cq", rubric.code_quality || 0);
    setRubricDimension("comm", rubric.communication || 0);

    // Qualitative Feedback
    const fb = card.feedback || {};
    const execBox = document.getElementById("scorecard-exec-summary");
    if (execBox) {
        execBox.innerHTML = `<p>${formatMarkdown(fb.executive_summary || "Technical assessment concluded successfully.")}</p>`;
    }

    const strengthsList = document.getElementById("scorecard-strengths-list");
    if (strengthsList) {
        strengthsList.innerHTML = (fb.strengths || ["Clean and correct problem implementation."])
            .map((s) => `<li>${escapeHtml(s)}</li>`)
            .join("");
    }

    const areasList = document.getElementById("scorecard-areas-list");
    if (areasList) {
        areasList.innerHTML = (fb.areas_for_improvement || ["Continue practicing edge case validation."])
            .map((a) => `<li>${escapeHtml(a)}</li>`)
            .join("");
    }

    const recBox = document.getElementById("scorecard-recommendations");
    if (recBox) {
        recBox.innerHTML = `<strong><i class="fa-solid fa-lightbulb text-yellow"></i> Recommended Focus:</strong> <span>${escapeHtml(fb.recommendations || "Practice adjacent algorithmic patterns under timed conditions.")}</span>`;
    }
}

function setRubricDimension(key, val) {
    const scoreEl = document.getElementById(`rubric-score-${key}`);
    const fillEl = document.getElementById(`rubric-fill-${key}`);
    const pct = Math.min(100, Math.round((val / 25) * 100));

    if (scoreEl) scoreEl.textContent = `${val} / 25`;
    if (fillEl) fillEl.style.width = `${pct}%`;
}

// ============================================================================
// Past Interviews History
// ============================================================================

async function loadInterviewHistory() {
    const tbody = document.getElementById("interview-history-tbody");
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="7" class="text-center"><i class="fa-solid fa-spinner fa-spin"></i> Loading interview sessions...</td></tr>`;

    try {
        const resp = await fetch("/api/interview/history");
        const data = await resp.json();

        if (!resp.ok || !data.success) {
            throw new Error(data.error || "Failed to load history.");
        }

        const history = data.history || [];
        if (history.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">No mock interviews completed yet. Launch your first 45-minute technical round above!</td></tr>`;
            return;
        }

        tbody.innerHTML = history.map((h) => {
            const date = h.created_at || "—";
            const role = h.target_role || "SDE";
            const company = h.target_company || "Tier-1";
            const problem = h.problem_title || h.problem_id || "DSA Problem";
            const timeSpent = `${Math.floor((h.time_spent_seconds || 0) / 60)}m ${(h.time_spent_seconds || 0) % 60}s`;
            const score = h.score || 0;
            const verdict = h.hire_decision || "LEAN HIRE";

            let verdictColor = "tag-green";
            if (verdict === "NO HIRE") verdictColor = "tag-red";
            else if (verdict.includes("LEAN")) verdictColor = "tag-yellow";

            return `
                <tr>
                    <td><code>${date}</code></td>
                    <td><strong>${escapeHtml(role)}</strong><br><small class="text-muted">${escapeHtml(company)}</small></td>
                    <td><span class="text-cyan">${escapeHtml(problem)}</span></td>
                    <td>${timeSpent}</td>
                    <td><strong>${score}</strong> / 100</td>
                    <td><span class="verdict-tag ${verdictColor}">${escapeHtml(verdict)}</span></td>
                    <td>
                        <button class="btn btn-glass-sm btn-view-past-card" data-sid="${h.id}">
                            <i class="fa-solid fa-eye"></i> Scorecard
                        </button>
                    </td>
                </tr>
            `;
        }).join("");

        // Attach view buttons
        document.querySelectorAll(".btn-view-past-card").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const sid = btn.dataset.sid;
                try {
                    const r = await fetch(`/api/interview/session/${sid}`);
                    const sData = await r.json();
                    if (sData.success && sData.session) {
                        const s = sData.session;
                        const scorecard = {
                            score: s.score,
                            hire_decision: s.hire_decision,
                            time_spent_seconds: s.time_spent_seconds,
                            tests_passed: s.tests_passed,
                            tests_total: s.tests_total,
                            hints_used: s.hints_used,
                            rubric_scores: s.rubric_scores,
                            feedback: s.feedback,
                        };
                        renderScorecard(scorecard, {});
                        showScorecardView();
                    }
                } catch (e) {
                    alert("Could not load session scorecard.");
                }
            });
        });
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-red">Failed to load history: ${escapeHtml(err.message)}</td></tr>`;
    }
}
