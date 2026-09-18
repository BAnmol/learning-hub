// ============================================================================
// DSA Code Studio — problem browser, Python editor, and the run/submit
// console. All requests are login-gated server-side; initStudio() is only
// ever called once a session is confirmed (see app.js).
// ============================================================================
import { apiJson, escapeHtml, formatMarkdown } from "./utils.js?v=8.0";
import { VisualizerPlayer } from "./visualizer.js?v=8.0";
import { buildVisualSimulation } from "./trace_simulator.js?v=8.0";
import { createPythonEditor, getEditorValue, setEditorValue, refreshEditorTheme } from "./editor.js";
import { getCurrentMode } from "./nav.js?v=8.0";

let stepFilter, difficultyFilter, statusFilter, problemSelect, prevProbBtn, nextProbBtn, bookmarkBtn;
let filterMatchNum, filterMatchTotal, problemPositionPill;
let probTitle, probStepBadge, probTopicBadge, probDiffBadge, probStatusBadge;
let probDescText, probRefSolutionCode, copySolutionBtn, probNotesInput, saveNotesBtn;
let codeEditor, resetCodeBtn, runCodeBtn, submitCodeBtn;
let cmStudioView = null; // CodeMirror 6 EditorView instance for code studio
let consoleStatusPill, testResultsContainer, customInputField, runCustomBtn;
let approachBtnBrute, approachBtnOptimized, bruteForceUnavailable, visualizeBtn, visualizerPanel;

// Explanation panel DOM refs
let explPanel, explLoading, explContent, explEmpty;
let explApproachBadge, explApproachName, explKeyInsight, explIntuition;
let explTime, explSpace, explSteps, explMistakes, explRegenerateBtn;
let traceCasePills, traceCustomBox, traceCustomInput, traceCustomSimulateBtn;
let traceInputSummary, traceMemoryHud, traceFirstBtn, traceLastBtn;
let traceInputVisual, traceStepper, tracePrevBtn, traceNextBtn, tracePlayBtn;
let traceStepCounter, tracePhaseCard, tracePhaseName, tracePhaseDesc;

// AI Review panel DOM refs
let reviewLoading, reviewContent, reviewEmpty, reviewScoreVal, reviewVerdictBadge, reviewSourceBadge, reviewSummaryText;
let reviewTimeVal, reviewTimeTarget, reviewTimeRat, reviewSpaceVal, reviewSpaceTarget, reviewSpaceRat;
let reviewStrengthsList, reviewAntipatternsList, reviewEdgeCasesList, reviewRefactorExp, reviewRefactoredCode;
let triggerReviewBtn, reviewStartCtaBtn, reviewCopyCodeBtn, reviewApplyCodeBtn, aiReviewToolbarBtn;
let currentReviewResult = null;

let loadedProblemsList = [];
let currentProblem = null;
let currentApproach = "optimized"; // 'optimized' | 'brute'
let booted = false;
let visualizerPlayer = null;

// Explanation & Simulation state
let currentExplanation = null;
let activeSimulation = null;
let selectedCaseInput = "";
let selectedCaseLabel = "";
let traceCurrentStep = 0;
let tracePlayInterval = null;
let traceSpeedMs = 1400;
let lastTestInput = null; // last input from Run/Submit
let solutionTabVisited = false;
let totalProblemCatalogSize = 342;


function cacheDom() {
    stepFilter = document.getElementById("step-filter");
    difficultyFilter = document.getElementById("difficulty-filter");
    statusFilter = document.getElementById("status-filter");
    problemSelect = document.getElementById("problem-select");
    prevProbBtn = document.getElementById("prev-prob-btn");
    nextProbBtn = document.getElementById("next-prob-btn");
    bookmarkBtn = document.getElementById("bookmark-btn");
    filterMatchNum = document.getElementById("filter-match-num");
    filterMatchTotal = document.getElementById("filter-match-total");
    problemPositionPill = document.getElementById("problem-position-pill");

    probTitle = document.getElementById("prob-title");
    probStepBadge = document.getElementById("prob-step-badge");
    probTopicBadge = document.getElementById("prob-topic-badge");
    probDiffBadge = document.getElementById("prob-diff-badge");
    probStatusBadge = document.getElementById("prob-status-badge");

    probDescText = document.getElementById("prob-description-text");
    probRefSolutionCode = document.getElementById("prob-ref-solution-code");
    copySolutionBtn = document.getElementById("copy-solution-btn");
    probNotesInput = document.getElementById("prob-notes-input");
    saveNotesBtn = document.getElementById("save-notes-btn");

    approachBtnBrute = document.getElementById("approach-btn-brute");
    approachBtnOptimized = document.getElementById("approach-btn-optimized");
    bruteForceUnavailable = document.getElementById("brute-force-unavailable");
    visualizeBtn = document.getElementById("visualize-btn");
    visualizerPanel = document.getElementById("visualizer-panel");

    codeEditor = document.getElementById("code-editor"); // hidden textarea (fallback/compat)
    resetCodeBtn = document.getElementById("reset-code-btn");
    runCodeBtn = document.getElementById("run-code-btn");
    submitCodeBtn = document.getElementById("submit-code-btn");

    consoleStatusPill = document.getElementById("console-status-pill");
    testResultsContainer = document.getElementById("test-results-container");
    customInputField = document.getElementById("custom-input-field");
    runCustomBtn = document.getElementById("run-custom-btn");

    // Explanation panel
    explPanel        = document.getElementById("explanation-panel");
    explLoading      = document.getElementById("expl-loading");
    explContent      = document.getElementById("expl-content");
    explEmpty        = document.getElementById("expl-empty");
    explApproachBadge= document.getElementById("expl-approach-badge");
    explApproachName = document.getElementById("expl-approach-name");
    explKeyInsight   = document.getElementById("expl-key-insight");
    explIntuition    = document.getElementById("expl-intuition");
    explTime         = document.getElementById("expl-time");
    explSpace        = document.getElementById("expl-space");
    explSteps        = document.getElementById("expl-steps");
    explMistakes     = document.getElementById("expl-mistakes");
    explRegenerateBtn= document.getElementById("expl-regenerate-btn");
    traceCasePills   = document.getElementById("trace-case-pills");
    traceCustomBox   = document.getElementById("trace-custom-box");
    traceCustomInput = document.getElementById("trace-custom-input");
    traceCustomSimulateBtn = document.getElementById("trace-custom-simulate-btn");
    traceInputSummary = document.getElementById("trace-input-summary");
    traceMemoryHud   = document.getElementById("trace-memory-hud");
    traceFirstBtn    = document.getElementById("trace-first-btn");
    traceLastBtn     = document.getElementById("trace-last-btn");
    traceInputVisual = document.getElementById("trace-input-visual");
    traceStepper     = document.getElementById("trace-stepper");
    tracePrevBtn     = document.getElementById("trace-prev-btn");
    traceNextBtn     = document.getElementById("trace-next-btn");
    tracePlayBtn     = document.getElementById("trace-play-btn");
    traceStepCounter = document.getElementById("trace-step-counter");
    tracePhaseCard   = document.getElementById("trace-phase-card");
    tracePhaseName   = document.getElementById("trace-phase-name");
    tracePhaseDesc   = document.getElementById("trace-phase-desc");

    // AI Review panel
    reviewLoading        = document.getElementById("review-loading");
    reviewContent        = document.getElementById("review-content");
    reviewEmpty          = document.getElementById("review-empty");
    reviewScoreVal       = document.getElementById("review-score-val");
    reviewVerdictBadge   = document.getElementById("review-verdict-badge");
    reviewSourceBadge    = document.getElementById("review-source-badge");
    reviewSummaryText    = document.getElementById("review-summary-text");
    reviewTimeVal        = document.getElementById("review-time-val");
    reviewTimeTarget     = document.getElementById("review-time-target");
    reviewTimeRat        = document.getElementById("review-time-rat");
    reviewSpaceVal       = document.getElementById("review-space-val");
    reviewSpaceTarget    = document.getElementById("review-space-target");
    reviewSpaceRat       = document.getElementById("review-space-rat");
    reviewStrengthsList  = document.getElementById("review-strengths-list");
    reviewAntipatternsList = document.getElementById("review-antipatterns-list");
    reviewEdgeCasesList  = document.getElementById("review-edge-cases-list");
    reviewRefactorExp    = document.getElementById("review-refactor-exp");
    reviewRefactoredCode = document.getElementById("review-refactored-code");
    triggerReviewBtn     = document.getElementById("trigger-review-btn");
    reviewStartCtaBtn    = document.getElementById("review-start-cta-btn");
    reviewCopyCodeBtn    = document.getElementById("review-copy-code-btn");
    reviewApplyCodeBtn   = document.getElementById("review-apply-code-btn");
    aiReviewToolbarBtn   = document.getElementById("ai-review-btn");
}

// ============================================================================
// EXPLANATION & DYNAMIC TEST-CASE VISUAL SIMULATION
// ============================================================================

function showExplState(state) {
    if (explLoading) explLoading.classList.toggle("hidden", state !== "loading");
    if (explContent) explContent.classList.toggle("hidden", state !== "content");
    if (explEmpty)   explEmpty.classList.toggle("hidden",   state !== "empty");
}

async function fetchAndRenderExplanation(force = false) {
    if (!currentProblem) return;
    showExplState("loading");
    const approach = currentApproach;
    const url = `/api/dsa/explain/${encodeURIComponent(currentProblem.id)}?approach=${approach}${force ? "&force=1" : ""}`;
    try {
        const data = await apiJson(url);
        if (data.success && data.explanation) {
            currentExplanation = data.explanation;
            renderExplanation(data.explanation);
            showExplState("content");
        } else {
            showExplState("empty");
            if (explEmpty) explEmpty.innerHTML = `<i class="fa-solid fa-circle-info"></i><p>${escapeHtml(data.error || "No explanation available.")}</p>`;
        }
    } catch (_) {
        showExplState("empty");
    }
}

function renderExplanation(expl) {
    const isOpt = expl.approach === "optimized";
    if (explApproachBadge) {
        explApproachBadge.textContent = isOpt ? "Optimized" : "Brute Force";
        explApproachBadge.className = `expl-approach-badge ${isOpt ? "optimized-badge" : "brute-badge"}`;
    }
    if (explApproachName) explApproachName.textContent = expl.approach_name || "";
    if (explKeyInsight)   explKeyInsight.textContent   = expl.key_insight || "";
    if (explIntuition)    explIntuition.textContent    = expl.intuition || "";
    if (explTime)         explTime.textContent  = expl.time_complexity  || "—";
    if (explSpace)        explSpace.textContent = expl.space_complexity || "—";

    // Step-by-step textual cards
    if (explSteps) {
        explSteps.innerHTML = "";
        (expl.steps || []).forEach((s, i) => {
            const d = document.createElement("div");
            d.className = "expl-step-item";
            d.innerHTML = `<div class="expl-step-num">${i + 1}</div>
                <div class="expl-step-body">
                    <div class="expl-step-label">${escapeHtml(s.label || "")}</div>
                    <div class="expl-step-detail">${escapeHtml(s.detail || "")}</div>
                </div>`;
            explSteps.appendChild(d);
        });
    }

    // Common mistakes
    if (explMistakes) {
        explMistakes.innerHTML = "";
        (expl.common_mistakes || []).forEach((m) => {
            const li = document.createElement("li");
            li.textContent = m;
            explMistakes.appendChild(li);
        });
    }

    // Dynamic Test-Case Selector & Visual Simulation Stage
    setupTestCaseSelector(expl);
}

/** Build test case pills and boot the interactive visual simulator. */
function setupTestCaseSelector(expl) {
    if (!traceCasePills) return;
    traceCasePills.innerHTML = "";

    const cases = (expl && expl.sample_test_cases) || (currentProblem && currentProblem.sample_test_cases) || [
        { label: "Case 1", input: "[2, 7, 11, 15], 9" },
        { label: "Case 2", input: "[3, 2, 4], 6" },
        { label: "Case 3", input: "[3, 3], 6" },
    ];

    const pillItems = [];

    // Predefined cases
    cases.forEach((c, idx) => {
        pillItems.push({
            id: `case-${idx}`,
            label: c.label || `Case ${idx + 1}`,
            input: c.input,
            description: c.description || "",
        });
    });

    // Last test run from editor (if available)
    if (lastTestInput) {
        pillItems.push({
            id: "case-last-run",
            label: "Last Test Run",
            input: lastTestInput,
            description: "Result from editor execution",
        });
    }

    // Custom input pill
    pillItems.push({
        id: "case-custom",
        label: "Custom Input",
        isCustom: true,
        input: "",
    });

    let activePillBtn = null;

    pillItems.forEach((item, index) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "trace-case-pill";
        btn.id = `pill-${item.id}`;
        btn.title = item.description || item.input;
        btn.innerHTML = escapeHtml(item.label);

        btn.addEventListener("click", () => {
            traceCasePills.querySelectorAll(".trace-case-pill").forEach((p) => p.classList.remove("active"));
            btn.classList.add("active");
            activePillBtn = btn;

            if (item.isCustom) {
                if (traceCustomBox) {
                    traceCustomBox.classList.remove("hidden");
                    if (traceCustomInput) {
                        if (!traceCustomInput.value && selectedCaseInput) {
                            traceCustomInput.value = selectedCaseInput;
                        }
                        traceCustomInput.focus();
                    }
                }
                if (traceCustomInput && traceCustomInput.value.trim()) {
                    runSimulation(traceCustomInput.value.trim(), "Custom Input");
                }
            } else {
                if (traceCustomBox) traceCustomBox.classList.add("hidden");
                runSimulation(item.input, item.label);
            }
        });

        traceCasePills.appendChild(btn);

        // Auto-select first item
        if (index === 0) {
            btn.classList.add("active");
            activePillBtn = btn;
            runSimulation(item.input, item.label);
        }
    });
}

/** Execute dynamic visual simulation on the selected test case */
function runSimulation(rawInput, label = "") {
    if (!currentProblem) return;
    selectedCaseInput = rawInput;
    selectedCaseLabel = label;
    stopTraceAutoPlay();

    activeSimulation = buildVisualSimulation(currentProblem, currentApproach, rawInput);
    traceCurrentStep = 0;

    if (traceInputSummary) {
        traceInputSummary.textContent = activeSimulation.inputSummary || rawInput || "(no input)";
    }

    renderSimulationStepper();
    updateSimulationView();
}

/** Render clickable step dots for the simulation timeline */
function renderSimulationStepper() {
    if (!traceStepper || !activeSimulation) return;
    traceStepper.innerHTML = "";

    const frames = activeSimulation.frames || [];
    frames.forEach((f, i) => {
        const dot = document.createElement("div");
        dot.className = `trace-phase-dot ht-${f.phase || "scan"}`;
        if (i < traceCurrentStep)  dot.classList.add("done");
        if (i === traceCurrentStep) dot.classList.add("active");

        dot.innerHTML = `
            <div class="trace-phase-dot-circle">${i + 1}</div>
            <div class="trace-phase-dot-label">${escapeHtml(f.title || `Step ${i + 1}`)}</div>
        `;

        dot.addEventListener("click", () => {
            traceCurrentStep = i;
            updateSimulationView();
        });
        traceStepper.appendChild(dot);
    });
}

/** Update element highlights, floating pointer pins, memory HUD, and explanation text */
function updateSimulationView() {
    if (!activeSimulation || !activeSimulation.frames.length) return;
    const frames = activeSimulation.frames;
    const total = frames.length;
    const frame = frames[traceCurrentStep];

    // Counter & Navigation buttons
    if (traceStepCounter) traceStepCounter.textContent = `${traceCurrentStep + 1} / ${total}`;
    if (traceFirstBtn)    traceFirstBtn.disabled = (traceCurrentStep === 0);
    if (tracePrevBtn)     tracePrevBtn.disabled = (traceCurrentStep === 0);
    if (traceNextBtn)     traceNextBtn.disabled = (traceCurrentStep === total - 1);
    if (traceLastBtn)     traceLastBtn.disabled = (traceCurrentStep === total - 1);

    // Guidance Card
    if (tracePhaseCard) tracePhaseCard.className = `trace-phase-card ht-${frame.phase || "scan"}`;
    if (tracePhaseName) tracePhaseName.innerHTML = `<i class="fa-solid fa-crosshairs"></i> ${escapeHtml(frame.title || `Step ${traceCurrentStep + 1}`)}`;
    if (tracePhaseDesc) tracePhaseDesc.innerHTML = frame.guidance || "";

    // 1. Render Visual Elements with Floating Pointers
    if (traceInputVisual) {
        traceInputVisual.innerHTML = "";
        const items = activeSimulation.items || [];
        const roles = frame.roles || {};
        const pointers = frame.pointers || {};

        items.forEach((val, idx) => {
            const cellWrap = document.createElement("div");
            cellWrap.className = "trace-cell-wrap";

            // Floating Pointer Tag (e.g. "▲ i", "▲ low", "▲ match")
            if (pointers[idx]) {
                const ptrTag = document.createElement("div");
                const isMatchPtr = pointers[idx] === "match" || pointers[idx] === "found";
                const isCmpPtr = ["compare", "swap", "mid", "mismatch"].includes(pointers[idx]);
                ptrTag.className = `trace-ptr-tag ${isMatchPtr ? "ptr-match" : isCmpPtr ? "ptr-compare" : ""}`;
                ptrTag.textContent = `▲ ${pointers[idx]}`;
                cellWrap.appendChild(ptrTag);
            } else {
                // Invisible placeholder for vertical alignment
                const spacer = document.createElement("div");
                spacer.style.height = "16px";
                cellWrap.appendChild(spacer);
            }

            // Token Cell Card
            const role = roles[idx] || "idle";
            const token = document.createElement("div");
            token.className = `trace-token ${role}`;
            token.textContent = val;
            cellWrap.appendChild(token);

            // Index Pill
            const idxPill = document.createElement("div");
            idxPill.className = "trace-cell-idx";
            idxPill.textContent = idx;
            cellWrap.appendChild(idxPill);

            traceInputVisual.appendChild(cellWrap);
        });
    }

    // 2. Render Live Memory & Variables HUD
    if (traceMemoryHud) {
        if (frame.memory && Object.keys(frame.memory).length > 0) {
            traceMemoryHud.classList.remove("hidden");
            traceMemoryHud.innerHTML = Object.keys(frame.memory).map((k) => `
                <div class="trace-memory-chip">
                    <strong>${escapeHtml(k)}:</strong> <code>${escapeHtml(String(frame.memory[k]))}</code>
                </div>
            `).join("");
        } else {
            traceMemoryHud.classList.add("hidden");
        }
    }

    // 3. Highlight active dot in stepper
    if (traceStepper) {
        const dots = traceStepper.querySelectorAll(".trace-phase-dot");
        dots.forEach((dot, i) => {
            dot.classList.toggle("done", i < traceCurrentStep);
            dot.classList.toggle("active", i === traceCurrentStep);
        });
    }
}

function stopTraceAutoPlay() {
    if (tracePlayInterval) {
        clearInterval(tracePlayInterval);
        tracePlayInterval = null;
        if (tracePlayBtn) tracePlayBtn.innerHTML = `<i class="fa-solid fa-play"></i> Auto-Play`;
    }
}

function wireExplanationEvents() {
    // Stepping buttons
    if (traceFirstBtn) traceFirstBtn.addEventListener("click", () => {
        traceCurrentStep = 0;
        updateSimulationView();
    });

    if (traceLastBtn) traceLastBtn.addEventListener("click", () => {
        if (activeSimulation && activeSimulation.frames) {
            traceCurrentStep = activeSimulation.frames.length - 1;
            updateSimulationView();
        }
    });

    if (tracePrevBtn) tracePrevBtn.addEventListener("click", () => {
        if (traceCurrentStep > 0) {
            traceCurrentStep--;
            updateSimulationView();
        }
    });

    if (traceNextBtn) traceNextBtn.addEventListener("click", () => {
        if (activeSimulation && traceCurrentStep < activeSimulation.frames.length - 1) {
            traceCurrentStep++;
            updateSimulationView();
        }
    });

    // Auto-play button
    if (tracePlayBtn) tracePlayBtn.addEventListener("click", () => {
        if (tracePlayInterval) {
            stopTraceAutoPlay();
        } else {
            tracePlayBtn.innerHTML = `<i class="fa-solid fa-pause"></i> Pause`;
            tracePlayInterval = setInterval(() => {
                if (activeSimulation && traceCurrentStep < activeSimulation.frames.length - 1) {
                    traceCurrentStep++;
                    updateSimulationView();
                } else {
                    stopTraceAutoPlay();
                    traceCurrentStep = 0;
                    updateSimulationView();
                }
            }, traceSpeedMs);
        }
    });

    // Speed toggles (1x vs 1.8x)
    document.querySelectorAll(".btn-speed").forEach((btn) => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".btn-speed").forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            traceSpeedMs = parseInt(btn.dataset.speed, 10) || 1400;
            if (tracePlayInterval) {
                stopTraceAutoPlay();
                tracePlayBtn?.click();
            }
        });
    });

    // Custom Input simulation
    if (traceCustomSimulateBtn) {
        traceCustomSimulateBtn.addEventListener("click", () => {
            const val = traceCustomInput ? traceCustomInput.value.trim() : "";
            if (val) {
                runSimulation(val, "Custom Input");
            }
        });
    }

    if (traceCustomInput) {
        traceCustomInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                traceCustomSimulateBtn?.click();
            }
        });
    }

    // Re-generate explanation
    if (explRegenerateBtn) explRegenerateBtn.addEventListener("click", () => {
        currentExplanation = null;
        fetchAndRenderExplanation(true);
    });
}

// ============================================================================
// AI CODE REVIEW & BIG-O ANALYZER
// ============================================================================

function showReviewState(state) {
    if (reviewLoading) reviewLoading.classList.toggle("hidden", state !== "loading");
    if (reviewContent) reviewContent.classList.toggle("hidden", state !== "content");
    if (reviewEmpty)   reviewEmpty.classList.toggle("hidden",   state !== "empty");
}

async function runAiReview() {
    if (!currentProblem) return;
    const code = cmStudioView ? getEditorValue(cmStudioView) : (codeEditor.value || "");

    // Jump to the Review tab so progress is visible even when triggered from
    // the editor toolbar button rather than the tab itself.
    if (window.switchSubTab) window.switchSubTab("review");
    showReviewState("loading");

    try {
        const data = await apiJson("/api/dsa/review", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ problem_id: currentProblem.id, code }),
        });

        if (data.success && data.review) {
            currentReviewResult = data.review;
            renderReviewResult(data.review);
            showReviewState("content");
        } else {
            showReviewState("empty");
            const msgEl = reviewEmpty ? reviewEmpty.querySelector("p") : null;
            if (msgEl) msgEl.textContent = data.error || "Code review failed. Please try again.";
        }
    } catch (e) {
        showReviewState("empty");
        const msgEl = reviewEmpty ? reviewEmpty.querySelector("p") : null;
        if (msgEl) msgEl.textContent = "Network error while running the code review.";
    }
}

function renderReviewResult(review) {
    if (reviewScoreVal) reviewScoreVal.textContent = review.score ?? "--";
    if (reviewVerdictBadge) {
        reviewVerdictBadge.textContent = review.verdict || "—";
        reviewVerdictBadge.className = `review-verdict-badge badge-${review.verdict_badge || "good"}`;
    }
    if (reviewSourceBadge) {
        reviewSourceBadge.innerHTML = review.source === "ai"
            ? `<i class="fa-solid fa-microchip"></i> AI Engine`
            : `<i class="fa-solid fa-code-compare"></i> Static Analyzer`;
    }
    if (reviewSummaryText) reviewSummaryText.textContent = review.summary || "";

    if (reviewTimeVal) reviewTimeVal.textContent = review.time_complexity || "—";
    if (reviewTimeTarget) reviewTimeTarget.textContent = `Target: ${review.optimal_time || "—"}`;
    if (reviewTimeRat) reviewTimeRat.textContent = review.time_rationale || "";

    if (reviewSpaceVal) reviewSpaceVal.textContent = review.space_complexity || "—";
    if (reviewSpaceTarget) reviewSpaceTarget.textContent = `Target: ${review.optimal_space || "—"}`;
    if (reviewSpaceRat) reviewSpaceRat.textContent = review.space_rationale || "";

    if (reviewStrengthsList) {
        const strengths = review.strengths || [];
        reviewStrengthsList.innerHTML = strengths.length
            ? strengths.map((s) => `<li><i class="fa-solid fa-check text-green"></i> ${escapeHtml(s)}</li>`).join("")
            : `<li><i class="fa-solid fa-check text-green"></i> No specific strengths flagged.</li>`;
    }

    if (reviewAntipatternsList) {
        const patterns = review.anti_patterns || [];
        reviewAntipatternsList.innerHTML = patterns.length
            ? patterns.map((p) => {
                const sev = (p.severity || "low").toLowerCase();
                return `
                    <div class="review-antipattern-card sev-${sev}">
                        <div class="antipattern-header">
                            <i class="fa-solid fa-triangle-exclamation"></i>
                            <strong>${escapeHtml(p.title || "Issue")}</strong>
                            <span class="sev-badge ${sev}">${sev.toUpperCase()}</span>
                        </div>
                        <p class="antipattern-desc">${escapeHtml(p.description || "")}</p>
                        ${p.suggestion ? `<div class="antipattern-sug"><i class="fa-solid fa-arrow-right text-green"></i> ${escapeHtml(p.suggestion)}</div>` : ""}
                    </div>
                `;
            }).join("")
            : `<div class="review-antipattern-card sev-low"><div class="antipattern-header"><i class="fa-solid fa-circle-check text-green"></i> <strong>No anti-patterns detected.</strong></div></div>`;
    }

    if (reviewEdgeCasesList) {
        const cases = review.edge_cases || [];
        reviewEdgeCasesList.innerHTML = cases.length
            ? cases.map((c) => {
                const status = (c.status || "passed").toLowerCase();
                return `
                    <div class="review-edge-item">
                        <div class="edge-title-row">
                            <span class="edge-name">${escapeHtml(c.case || "Edge case")}</span>
                            <span class="edge-status-pill ${status}">${status.toUpperCase()}</span>
                        </div>
                        ${c.detail ? `<div class="edge-detail">${escapeHtml(c.detail)}</div>` : ""}
                    </div>
                `;
            }).join("")
            : `<div class="review-edge-item"><div class="edge-title-row"><span class="edge-name">No edge cases flagged.</span></div></div>`;
    }

    if (reviewRefactorExp) reviewRefactorExp.textContent = review.refactor_explanation || "";
    if (reviewRefactoredCode) reviewRefactoredCode.textContent = review.refactored_code || "# No refactored code available";
}

function wireReviewEvents() {
    if (triggerReviewBtn) triggerReviewBtn.addEventListener("click", () => runAiReview());
    if (reviewStartCtaBtn) reviewStartCtaBtn.addEventListener("click", () => runAiReview());
    if (aiReviewToolbarBtn) aiReviewToolbarBtn.addEventListener("click", () => runAiReview());

    if (reviewCopyCodeBtn) {
        reviewCopyCodeBtn.addEventListener("click", () => {
            if (!currentReviewResult || !currentReviewResult.refactored_code) return;
            navigator.clipboard.writeText(currentReviewResult.refactored_code);
            reviewCopyCodeBtn.innerHTML = `<i class="fa-solid fa-check"></i> Copied!`;
            setTimeout(() => { reviewCopyCodeBtn.innerHTML = `<i class="fa-regular fa-copy"></i> Copy Code`; }, 1500);
        });
    }

    if (reviewApplyCodeBtn) {
        reviewApplyCodeBtn.addEventListener("click", () => {
            if (!currentReviewResult || !currentReviewResult.refactored_code) return;
            if (cmStudioView) {
                setEditorValue(cmStudioView, currentReviewResult.refactored_code);
            } else if (codeEditor) {
                codeEditor.value = currentReviewResult.refactored_code;
            }
            reviewApplyCodeBtn.innerHTML = `<i class="fa-solid fa-check"></i> Applied!`;
            setTimeout(() => { reviewApplyCodeBtn.innerHTML = `<i class="fa-solid fa-arrow-right-to-bracket"></i> Apply to Editor`; }, 1500);
        });
    }

    // Ctrl+Shift+R — quick AI Review shortcut, matches the toolbar button's tooltip.
    // Scoped to the Studio tab being active so it doesn't shadow the browser's
    // own hard-reload shortcut (and silently trigger a review) on every other tab.
    document.addEventListener("keydown", (e) => {
        if (getCurrentMode() !== "studio") return;
        if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === "r") {
            e.preventDefault();
            runAiReview();
        }
    });
}

window.switchSubTab = function(target) {
    const subTabs = document.querySelectorAll(".sub-tab");
    const subTabContents = {
        desc: document.getElementById("tab-content-desc"),
        solution: document.getElementById("tab-content-solution"),
        review: document.getElementById("tab-content-review"),
        notes: document.getElementById("tab-content-notes"),
    };

    subTabs.forEach((tab) => {
        tab.classList.toggle("active", tab.dataset.subtab === target);
    });

    Object.keys(subTabContents).forEach((k) => {
        if (subTabContents[k]) {
            subTabContents[k].classList.toggle("hidden", k !== target);
        }
    });

    // Auto-load explanation when Approach tab is opened
    if (target === "solution" && currentProblem) {
        fetchAndRenderExplanation();
    }
};

window.fetchAndRenderExplanation = fetchAndRenderExplanation;
window.runSimulation = runSimulation;

function setupSubTabs() {
    const subTabs = document.querySelectorAll(".sub-tab");
    subTabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            const target = tab.dataset.subtab;
            window.switchSubTab(target);
        });
    });
}

function setupConsoleTabs() {
    const consoleTabs = document.querySelectorAll(".console-tab");
    const consolePanes = {
        tests: document.getElementById("console-tab-tests"),
        custom: document.getElementById("console-tab-custom"),
    };

    consoleTabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            consoleTabs.forEach((t) => t.classList.remove("active"));
            tab.classList.add("active");
            const target = tab.dataset.ctab;
            Object.keys(consolePanes).forEach((k) => {
                consolePanes[k].classList.toggle("hidden", k !== target);
            });
        });
    });
}

async function loadStepsFilter() {
    try {
        const data = await apiJson("/api/dsa/steps");
        if (data.success && data.steps) {
            stepFilter.innerHTML = `<option value="">All Steps</option>`;
            data.steps.forEach((s) => {
                const opt = document.createElement("option");
                opt.value = s.step;
                opt.textContent = `${s.step} (${s.solved_count}/${s.total_problems})`;
                stepFilter.appendChild(opt);
            });
        }
    } catch (e) { /* non-fatal */ }
}

export async function loadFilteredProblems(targetStep = "") {
    if (targetStep) stepFilter.value = targetStep;
    const step = stepFilter.value;
    const diff = difficultyFilter.value;
    const status = statusFilter.value;

    try {
        const url = `/api/dsa/problems?step=${encodeURIComponent(step)}&difficulty=${encodeURIComponent(diff)}&status=${encodeURIComponent(status)}`;
        const data = await apiJson(url);
        if (data.success) {
            loadedProblemsList = data.problems;
            if (data.total_count) totalProblemCatalogSize = data.total_count;
            if (filterMatchNum) filterMatchNum.textContent = loadedProblemsList.length;
            if (filterMatchTotal) {
                if (!step && !diff && !status) {
                    totalProblemCatalogSize = loadedProblemsList.length;
                    filterMatchTotal.textContent = "problems";
                } else {
                    filterMatchTotal.textContent = `of ${totalProblemCatalogSize} problems`;
                }
            }
            problemSelect.innerHTML = "";
            if (loadedProblemsList.length === 0) {
                problemSelect.innerHTML = `<option value="">No problems found</option>`;
                problemPositionPill.textContent = "0 / 0";
                return;
            }

            loadedProblemsList.forEach((p) => {
                const opt = document.createElement("option");
                opt.value = p.id;
                const checkmark = p.status === "solved" ? "✓ " : "";
                const star = p.is_bookmarked ? "★ " : "";
                opt.textContent = `${checkmark}${star}[${p.difficulty}] ${p.title}`;
                problemSelect.appendChild(opt);
            });

            const currentStillMatches = currentProblem && loadedProblemsList.some((p) => p.id === currentProblem.id);
            if (currentStillMatches) {
                problemSelect.value = currentProblem.id;
                updatePositionPill();
            } else {
                // The open problem fell outside the new filter (or nothing was
                // open yet) — load the first match instead of leaving the
                // dropdown, position pill, and Prev/Next controls pointing at
                // a problem that's no longer in the visible set.
                await loadProblem(loadedProblemsList[0].id);
            }
        } else if (problemSelect) {
            problemSelect.innerHTML = `<option value="">Couldn't load problems — try again</option>`;
        }
    } catch (e) {
        if (problemSelect) {
            problemSelect.innerHTML = `<option value="">Couldn't load problems — check your connection</option>`;
        }
    }
}

function updatePositionPill() {
    if (!currentProblem || loadedProblemsList.length === 0) {
        problemPositionPill.textContent = "— / —";
        return;
    }
    const idx = loadedProblemsList.findIndex((p) => p.id === currentProblem.id);
    problemPositionPill.textContent = idx >= 0 ? `${idx + 1} / ${loadedProblemsList.length}` : `— / ${loadedProblemsList.length}`;
}

async function loadProblem(problemId) {
    if (!problemId) return;
    try {
        const data = await apiJson(`/api/dsa/problem/${encodeURIComponent(problemId)}`);
        if (data.success) {
            currentProblem = data.problem;
            window.currentProblemId = currentProblem.id;
            renderProblemView(currentProblem);
        }
    } catch (e) { /* non-fatal */ }
}

/** Current Python source in the Studio editor — CodeMirror when mounted, else the hidden fallback textarea. */
window.getStudioCode = function() {
    return cmStudioView ? getEditorValue(cmStudioView) : (codeEditor?.value || "");
};

window.loadTestCaseIntoCustom = function(rawInput) {
    if (!rawInput) return;
    const customTabBtn = document.querySelectorAll(".console-tab")[1];
    if (customTabBtn) customTabBtn.click();
    if (customInputField) {
        customInputField.value = rawInput;
        customInputField.focus();
    }
};

function buildProblemDescriptionHtml(p) {
    const params = p.parameters || [];
    const constraints = p.constraints || [];
    const testCases = p.sample_test_cases || [];
    const retType = p.return_type || "Any";
    const signature = p.signature || `def ${p.method_name}(self, ...):`;

    // 1. Parameters HTML
    let paramsHtml = "";
    if (params.length > 0) {
        paramsHtml = params.map(param => `
            <div class="param-chip">
                <div class="param-chip-header">
                    <span class="param-name"><code>${escapeHtml(param.name)}</code></span>
                    <span class="param-type">${escapeHtml(param.type)}</span>
                </div>
                ${param.description ? `<div class="param-desc">${escapeHtml(param.description)}</div>` : ""}
            </div>
        `).join("");
    }

    // 2. Return type chip
    const returnChipHtml = `
        <div class="param-chip return-chip">
            <div class="param-chip-header">
                <span class="param-name"><strong>Return Type</strong></span>
                <span class="param-type">${escapeHtml(retType)}</span>
            </div>
            <div class="param-desc">Expected output from <code>Solution.${escapeHtml(p.method_name)}()</code></div>
        </div>
    `;

    // 3. Examples HTML (at least 2 test cases)
    let examplesHtml = "";
    if (testCases.length > 0) {
        examplesHtml = testCases.slice(0, 3).map((c, idx) => {
            const rawIn = c.raw_input || c.input || "";
            return `
                <div class="problem-example-card">
                    <div class="example-card-header">
                        <span class="example-badge"><i class="fa-solid fa-flask"></i> ${escapeHtml(c.label || `Example ${idx + 1}`)}</span>
                        ${rawIn ? `
                            <button type="button" class="btn btn-ghost btn-xs btn-use-example" data-raw-input="${escapeHtml(rawIn)}" title="Load this input into Custom Input console">
                                <i class="fa-solid fa-play text-green"></i> Test This Input
                            </button>
                        ` : ""}
                    </div>
                    <div class="example-card-body">
                        <div class="example-row">
                            <span class="example-label">Input:</span>
                            <pre class="example-val"><code>${escapeHtml(c.input || "")}</code></pre>
                        </div>
                        <div class="example-row">
                            <span class="example-label">Output:</span>
                            <pre class="example-val text-green"><code>${escapeHtml(c.output || c.expected_output || "Valid Result")}</code></pre>
                        </div>
                        ${c.explanation ? `
                            <div class="example-row explanation-row">
                                <span class="example-label">Explanation:</span>
                                <div class="example-explanation">${escapeHtml(c.explanation)}</div>
                            </div>
                        ` : ""}
                    </div>
                </div>
            `;
        }).join("");
    }

    // 4. Constraints HTML
    let constraintsHtml = "";
    if (constraints.length > 0) {
        constraintsHtml = constraints.map(con => `
            <li class="constraint-item">
                <i class="fa-solid fa-circle-dot constraint-bullet"></i>
                <span><code>${escapeHtml(con)}</code></span>
            </li>
        `).join("");
    }

    return `
        <div class="problem-desc-container">
            <!-- Problem Header & Goal -->
            <div class="prob-desc-header">
                <h3>${escapeHtml(p.title)}</h3>
                ${p.description ? `
                    <div class="prob-markdown-body">
                        ${formatMarkdown(p.description)}
                    </div>
                ` : `
                    <p class="prob-intro-summary">
                        Implement the <code>Solution.${escapeHtml(p.method_name)}()</code> method in Python to solve this DSA problem.
                        Review the function parameters, 2 concrete sample test cases, and constraints below before writing and testing your code.
                    </p>
                `}
            </div>

            <!-- Parameters & Signature Section -->
            <div class="problem-desc-section">
                <div class="section-title-bar">
                    <i class="fa-solid fa-code text-accent"></i>
                    <h4>Parameters & Function Signature</h4>
                </div>
                <div class="signature-box">
                    <code>${escapeHtml(signature)}</code>
                </div>
                <div class="param-chips-grid">
                    ${paramsHtml}
                    ${returnChipHtml}
                </div>
            </div>

            <!-- Examples & Test Cases Section (2+ Cases) -->
            <div class="problem-desc-section">
                <div class="section-title-bar">
                    <i class="fa-solid fa-vial-circle-check text-green"></i>
                    <h4>Examples & Sample Test Cases</h4>
                </div>
                <div class="examples-list">
                    ${examplesHtml}
                </div>
            </div>

            <!-- Constraints Section -->
            <div class="problem-desc-section">
                <div class="section-title-bar">
                    <i class="fa-solid fa-shield-halved text-yellow"></i>
                    <h4>Constraints & Complexity</h4>
                </div>
                <ul class="constraints-list">
                    ${constraintsHtml}
                </ul>
            </div>
        </div>
    `;
}

function renderProblemView(p) {
    updatePositionPill();
    problemSelect.value = p.id;
    probTitle.textContent = p.title;

    if (p.step && (p.step.includes("AI/ML") || p.step.includes("Step 18"))) {
        probStepBadge.innerHTML = `<i class="fa-solid fa-brain text-purple"></i> ${escapeHtml(p.step)}`;
    } else {
        probStepBadge.textContent = p.step;
    }
    probTopicBadge.textContent = p.topic;

    probDiffBadge.className = `meta-tag diff-tag ${p.difficulty.toLowerCase()}-tag`;
    probDiffBadge.textContent = p.difficulty;

    probStatusBadge.className = `meta-tag status-tag ${p.status}-tag`;
    probStatusBadge.textContent = p.status.toUpperCase();

    bookmarkBtn.classList.toggle("bookmarked", p.is_bookmarked);
    bookmarkBtn.innerHTML = p.is_bookmarked ? `<i class="fa-solid fa-star"></i>` : `<i class="fa-regular fa-star"></i>`;

    probDescText.innerHTML = buildProblemDescriptionHtml(p);


    // Approach tab: reset to Optimized, show/hide the Brute Force toggle
    // depending on whether a verified brute-force solution exists for this problem.
    currentApproach = "optimized";
    approachBtnOptimized.classList.add("active");
    approachBtnBrute.classList.remove("active");
    const hasBruteForce = !!p.brute_force_solution;
    approachBtnBrute.classList.toggle("hidden", !hasBruteForce);
    bruteForceUnavailable.classList.toggle("hidden", true);
    renderApproachCode();
    visualizerPanel.classList.add("hidden");
    visualizeBtn.innerHTML = `<i class="fa-solid fa-diagram-project"></i> Visualize Flow`;
    if (visualizerPlayer) visualizerPlayer.stop();

    // Reset explanation panel for the new problem
    currentExplanation = null;
    showExplState("empty");
    if (explEmpty) explEmpty.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i><p>Open the <strong>Approach</strong> tab to generate an AI explanation.</p>`;

    // Reset AI review panel for the new problem
    currentReviewResult = null;
    showReviewState("empty");

    probNotesInput.value = p.notes || "";

    // Load code into CodeMirror 6 editor
    const codeToLoad = p.user_code || p.starter_code || "";
    if (cmStudioView) {
        setEditorValue(cmStudioView, codeToLoad);
    } else {
        codeEditor.value = codeToLoad; // fallback
    }

    consoleStatusPill.className = "status-pill idle";
    consoleStatusPill.textContent = "Ready";
    testResultsContainer.innerHTML = `<div class="test-results-empty">Click <strong>Run Code</strong> (Ctrl+Enter) or <strong>Submit</strong> (Ctrl+Shift+Enter) to evaluate your solution.</div>`;
}

function renderApproachCode() {
    if (!currentProblem) return;
    if (currentApproach === "brute") {
        if (currentProblem.brute_force_solution) {
            probRefSolutionCode.textContent = currentProblem.brute_force_solution;
        } else {
            // Shouldn't normally happen (button is hidden when unavailable),
            // but fall back gracefully rather than showing nothing.
            probRefSolutionCode.textContent = currentProblem.reference_solution || "# No solution available";
            bruteForceUnavailable.classList.remove("hidden");
        }
    } else {
        probRefSolutionCode.textContent = currentProblem.reference_solution || "# No reference solution available";
    }
}

// updateLineNumbers: now handled natively by CodeMirror's built-in line gutter.
// Kept as a no-op for any legacy calls.
function updateLineNumbers() { /* no-op: CodeMirror handles line numbers */ }

async function executeCode(isSubmit = false, customInput = "") {
    if (!currentProblem) return;
    const code = cmStudioView ? getEditorValue(cmStudioView) : (codeEditor.value || "");

    consoleStatusPill.className = "status-pill running";
    consoleStatusPill.textContent = isSubmit ? "Evaluating..." : "Running Tests...";
    testResultsContainer.innerHTML = `<div class="test-results-empty"><i class="fa-solid fa-spinner fa-spin"></i> Executing Python sandbox against test cases...</div>`;

    document.querySelectorAll(".console-tab")[0]?.click();

    try {
        const endpoint = isSubmit ? "/api/dsa/submit" : "/api/dsa/run";
        const data = await apiJson(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ problem_id: currentProblem.id, code, custom_input: customInput }),
        });

        if (!data.success) {
            consoleStatusPill.className = "status-pill error";
            consoleStatusPill.textContent = "Error";
            testResultsContainer.innerHTML = `<div class="test-case-item failed"><strong class="text-red">Execution Error:</strong><pre style="margin-top:6px;">${escapeHtml(data.error || "Unknown error")}</pre></div>`;
            return;
        }

        const result = data.result || {};
        const isAccepted = result.passed;

        if (isAccepted) {
            consoleStatusPill.className = "status-pill accepted";
            consoleStatusPill.textContent = isSubmit ? "Accepted" : "Passed";
        } else {
            consoleStatusPill.className = "status-pill error";
            consoleStatusPill.textContent = result.status || "Failed";
        }

        renderExecutionResults(result);

        // Capture first test input so the Trace Animator can use it
        const testResults = result.test_results || [];
        if (testResults.length > 0 && testResults[0].input) {
            lastTestInput = testResults[0].input;
            // If Approach tab is open, update test case pills and simulate the test input
            const solutionTab = document.getElementById("tab-content-solution");
            if (solutionTab && !solutionTab.classList.contains("hidden") && currentExplanation) {
                setupTestCaseSelector(currentExplanation);
                runSimulation(lastTestInput, "Last Test Run");
            }
        }

        if (isSubmit && isAccepted) {
            currentProblem.status = "solved";
            probStatusBadge.className = "meta-tag status-tag solved-tag";
            probStatusBadge.textContent = "SOLVED";
            await loadFilteredProblems();
        }
    } catch (err) {
        consoleStatusPill.className = "status-pill error";
        consoleStatusPill.textContent = "Network Error";
        testResultsContainer.innerHTML = `<div class="test-case-item failed"><strong class="text-red">Network Error:</strong> Failed to reach Python execution backend.</div>`;
    }
}

function renderExecutionResults(res) {
    let html = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <div>
                <strong class="${res.passed ? 'text-green' : 'text-red'}" style="font-size:1.1rem;">${res.status}</strong>
                <span style="color:var(--text-muted); font-size:0.8rem; margin-left:8px;">(${res.tests_passed || 0}/${res.tests_total || 0} passed)</span>
            </div>
            <div style="font-size:0.8rem; color:var(--text-muted);">
                Runtime: <strong class="text-cyan">${res.execution_time_ms || 0}ms</strong>
            </div>
        </div>
    `;

    if (res.error) {
        html += `
            <div class="test-case-item failed">
                <strong class="text-red">Traceback / Error Output:</strong>
                <pre style="margin-top:6px; color:#f87171; white-space:pre-wrap;">${escapeHtml(res.error)}</pre>
            </div>
        `;
    }

    if (res.stdout) {
        html += `
            <div class="test-case-item">
                <strong class="text-yellow">Console Stdout:</strong>
                <pre style="margin-top:6px; color:#e2e8f0; white-space:pre-wrap;">${escapeHtml(res.stdout)}</pre>
            </div>
        `;
    }

    if (res.test_results && res.test_results.length > 0) {
        res.test_results.forEach((t, i) => {
            html += `
                <div class="test-case-item ${t.passed ? 'passed' : 'failed'}">
                    <div class="test-meta-row">
                        <span>Test Case #${t.test_id || i + 1}</span>
                        <span class="${t.passed ? 'text-green' : 'text-red'}">${t.passed ? 'Passed' : 'Failed'}</span>
                    </div>
                    <div class="test-diff-grid">
                        <div>
                            <span style="color:var(--text-muted); font-size:0.75rem;">INPUT:</span>
                            <div class="test-field">${escapeHtml(t.input)}</div>
                        </div>
                        <div>
                            <span style="color:var(--text-muted); font-size:0.75rem;">YOUR OUTPUT:</span>
                            <div class="test-field ${t.passed ? 'text-green' : 'text-red'}">${escapeHtml(t.user_output)}</div>
                        </div>
                    </div>
                    ${!t.passed && t.expected_output ? `
                        <div style="margin-top:6px;">
                            <span style="color:var(--text-muted); font-size:0.75rem;">EXPECTED OUTPUT:</span>
                            <div class="test-field text-gold">${escapeHtml(t.expected_output)}</div>
                        </div>
                    ` : ''}
                </div>
            `;
        });
    }

    testResultsContainer.innerHTML = html;
}

function wireEvents() {
    setupSubTabs();
    setupConsoleTabs();

    stepFilter.addEventListener("change", () => loadFilteredProblems());
    difficultyFilter.addEventListener("change", () => loadFilteredProblems());
    statusFilter.addEventListener("change", () => loadFilteredProblems());

    problemSelect.addEventListener("change", (e) => {
        if (e.target.value) loadProblem(e.target.value);
    });

    // Delegated so it keeps working across every re-render of probDescText.innerHTML
    // (the "Test This Input" buttons on example cards are rebuilt per problem load).
    probDescText.addEventListener("click", (e) => {
        const btn = e.target.closest(".btn-use-example");
        if (btn && btn.dataset.rawInput !== undefined) {
            window.loadTestCaseIntoCustom(btn.dataset.rawInput);
        }
    });

    prevProbBtn.addEventListener("click", () => {
        if (!currentProblem || loadedProblemsList.length === 0) return;
        const idx = loadedProblemsList.findIndex((p) => p.id === currentProblem.id);
        if (idx > 0) loadProblem(loadedProblemsList[idx - 1].id);
    });

    nextProbBtn.addEventListener("click", () => {
        if (!currentProblem || loadedProblemsList.length === 0) return;
        const idx = loadedProblemsList.findIndex((p) => p.id === currentProblem.id);
        if (idx >= 0 && idx < loadedProblemsList.length - 1) {
            loadProblem(loadedProblemsList[idx + 1].id);
        }
    });

    bookmarkBtn.addEventListener("click", async () => {
        if (!currentProblem) return;
        const newBm = !currentProblem.is_bookmarked;
        currentProblem.is_bookmarked = newBm;
        bookmarkBtn.classList.toggle("bookmarked", newBm);
        bookmarkBtn.innerHTML = newBm ? `<i class="fa-solid fa-star"></i>` : `<i class="fa-regular fa-star"></i>`;

        await apiJson("/api/dsa/notes", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ problem_id: currentProblem.id, is_bookmarked: newBm }),
        });
        await loadFilteredProblems();
    });

    saveNotesBtn.addEventListener("click", async () => {
        if (!currentProblem) return;
        const notes = probNotesInput.value;
        saveNotesBtn.disabled = true;
        saveNotesBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Saving...`;

        await apiJson("/api/dsa/notes", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ problem_id: currentProblem.id, notes }),
        });

        setTimeout(() => {
            saveNotesBtn.disabled = false;
            saveNotesBtn.innerHTML = `<i class="fa-solid fa-check"></i> Saved!`;
            setTimeout(() => { saveNotesBtn.innerHTML = `<i class="fa-solid fa-floppy-disk"></i> Save Notes`; }, 1500);
        }, 400);
    });

    copySolutionBtn.addEventListener("click", () => {
        const code = currentApproach === "brute" ? currentProblem?.brute_force_solution : currentProblem?.reference_solution;
        if (!code) return;
        navigator.clipboard.writeText(code);
        copySolutionBtn.innerHTML = `<i class="fa-solid fa-check"></i> Copied!`;
        setTimeout(() => { copySolutionBtn.innerHTML = `<i class="fa-regular fa-copy"></i> Copy Code`; }, 1500);
    });

    approachBtnOptimized.addEventListener("click", () => {
        currentApproach = "optimized";
        approachBtnOptimized.classList.add("active");
        approachBtnOptimized.setAttribute("aria-selected", "true");
        approachBtnBrute.classList.remove("active");
        approachBtnBrute.setAttribute("aria-selected", "false");
        bruteForceUnavailable.classList.add("hidden");
        renderApproachCode();
        // Re-fetch explanation for optimized if Solution tab is visible
        const solutionTab = document.getElementById("tab-content-solution");
        if (solutionTab && !solutionTab.classList.contains("hidden")) {
            fetchAndRenderExplanation();
        }
    });

    approachBtnBrute.addEventListener("click", () => {
        if (approachBtnBrute.classList.contains("hidden")) return;
        currentApproach = "brute";
        approachBtnBrute.classList.add("active");
        approachBtnBrute.setAttribute("aria-selected", "true");
        approachBtnOptimized.classList.remove("active");
        approachBtnOptimized.setAttribute("aria-selected", "false");
        bruteForceUnavailable.classList.add("hidden");
        renderApproachCode();
        // Re-fetch explanation for brute force
        const solutionTab = document.getElementById("tab-content-solution");
        if (solutionTab && !solutionTab.classList.contains("hidden")) {
            fetchAndRenderExplanation();
        }
    });

    visualizeBtn.addEventListener("click", () => {
        if (!currentProblem) return;
        const isHidden = visualizerPanel.classList.contains("hidden");
        if (isHidden) {
            if (!visualizerPlayer) visualizerPlayer = new VisualizerPlayer(visualizerPanel);
            visualizerPlayer.load(currentProblem.topic);
            visualizerPanel.classList.remove("hidden");
            visualizeBtn.innerHTML = `<i class="fa-solid fa-eye-slash"></i> Hide Flow`;
        } else {
            if (visualizerPlayer) visualizerPlayer.stop();
            visualizerPanel.classList.add("hidden");
            visualizeBtn.innerHTML = `<i class="fa-solid fa-diagram-project"></i> Visualize Flow`;
        }
    });

    resetCodeBtn.addEventListener("click", () => {
        if (!currentProblem) return;
        if (confirm("Reset editor to default starter template?")) {
            const starter = currentProblem.starter_code || "";
            if (cmStudioView) {
                setEditorValue(cmStudioView, starter);
            } else {
                codeEditor.value = starter;
            }
        }
    });

    // ── Initialize CodeMirror 6 for the Code Studio ──────────────────────────
    const cmHost = document.getElementById("cm-studio-editor");
    if (cmHost) {
        cmStudioView = createPythonEditor(cmHost, {
            initialValue: codeEditor.value || "",
            onRunShortcut: () => executeCode(false),
            onSubmitShortcut: () => executeCode(true),
        });
    }

    // Keep the code editor's syntax theme in sync with the site-wide light/dark toggle.
    window.addEventListener("dsa-theme-change", () => refreshEditorTheme(cmStudioView));

    runCodeBtn.addEventListener("click", () => executeCode(false));
    submitCodeBtn.addEventListener("click", () => executeCode(true));
    runCustomBtn.addEventListener("click", () => {
        const customIn = customInputField.value.trim();
        executeCode(false, customIn);
    });
}

/** Boot the studio once (called after the first confirmed login). */
export async function initStudio() {
    if (booted) return;
    booted = true;
    cacheDom();
    wireEvents();
    wireExplanationEvents();
    wireReviewEvents();

    await loadStepsFilter();
    await loadFilteredProblems();
    if (loadedProblemsList.length > 0) {
        await loadProblem(loadedProblemsList[0].id);
    }

    // Auto-open Approach tab if requested via URL param or hash
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("tab") === "solution" || window.location.hash === "#solution" || window.location.hash === "#approach") {
        if (window.switchSubTab) {
            window.switchSubTab("solution");
        }
    }
}

/** Called every time the Studio tab becomes active. */
export function onShow() {
    // CodeMirror refreshes itself; nothing extra needed.
    if (cmStudioView) cmStudioView.requestMeasure();
}

/** Used by the Tracker roadmap cards to jump into a specific step. */
export function filterByStep(step) {
    loadFilteredProblems(step);
}
