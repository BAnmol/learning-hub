// ============================================================================
// Notion Integration & Notes Sync Module (Multi-Tenant & Privacy-Isolated)
// Handles connection lifecycle, auto-provisioning, syncing code solutions &
// personal notes, and exporting mock interview scorecards.
// ============================================================================

let isNotionConnected = false;
let notionData = null;

/**
 * Initialize Notion event listeners.
 */
export function initNotion() {
    // Open Modal
    const btnHub = document.getElementById("btn-notion-hub");
    if (btnHub) {
        btnHub.addEventListener("click", () => openNotionModal());
    }

    // Close Modal
    const btnClose = document.getElementById("btn-close-notion");
    const modal = document.getElementById("notion-modal");
    if (btnClose && modal) {
        btnClose.addEventListener("click", () => {
            modal.style.display = "none";
        });

        modal.addEventListener("click", (e) => {
            if (e.target === modal) {
                modal.style.display = "none";
            }
        });
    }

    // Show/Hide token
    const btnToggleToken = document.getElementById("btn-toggle-notion-token");
    const tokenInput = document.getElementById("notion-token-input");
    if (btnToggleToken && tokenInput) {
        btnToggleToken.addEventListener("click", () => {
            const isPw = tokenInput.type === "password";
            tokenInput.type = isPw ? "text" : "password";
            btnToggleToken.innerHTML = isPw ? '<i class="fa-regular fa-eye-slash"></i>' : '<i class="fa-regular fa-eye"></i>';
        });
    }

    // Connect Form Submit
    const connectForm = document.getElementById("notion-connect-form");
    if (connectForm) {
        connectForm.addEventListener("submit", handleNotionConnect);
    }

    // Disconnect Button
    const btnDisconnect = document.getElementById("btn-disconnect-notion");
    if (btnDisconnect) {
        btnDisconnect.addEventListener("click", handleNotionDisconnect);
    }

    // Auto-sync Toggle
    const toggleAutosync = document.getElementById("toggle-notion-autosync");
    if (toggleAutosync) {
        toggleAutosync.addEventListener("change", async (e) => {
            try {
                await fetch("/api/notion/toggle-autosync", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ auto_sync_enabled: e.target.checked }),
                });
            } catch (err) {
                console.error("Failed to update Notion autosync setting:", err);
            }
        });
    }

    // Sync Problem Buttons in Code Studio
    const btnSyncProb = document.getElementById("btn-sync-problem-notion");
    if (btnSyncProb) {
        btnSyncProb.addEventListener("click", () => syncActiveProblemToNotion(btnSyncProb));
    }

    const btnSyncNotes = document.getElementById("btn-sync-notes-notion");
    if (btnSyncNotes) {
        btnSyncNotes.addEventListener("click", () => syncActiveProblemToNotion(btnSyncNotes));
    }

    // Export Scorecard in Mock Interview
    const btnExportScorecard = document.getElementById("btn-scorecard-notion");
    if (btnExportScorecard) {
        btnExportScorecard.addEventListener("click", () => exportScorecardToNotion(btnExportScorecard));
    }

    // Fetch initial status on load
    refreshNotionStatus();
}

/**
 * Fetch and update Notion status from backend.
 */
export async function refreshNotionStatus() {
    try {
        const resp = await fetch("/api/notion/status");
        if (!resp.ok) return;
        const data = await resp.json();

        isNotionConnected = Boolean(data.connected);
        notionData = data;

        updateNotionUI(data);
    } catch (err) {
        console.warn("Could not fetch Notion status:", err);
    }
}

function updateNotionUI(data) {
    const hubBtn = document.getElementById("btn-notion-hub");
    const pillText = document.getElementById("notion-pill-text");

    if (hubBtn) {
        if (data && data.connected) {
            hubBtn.classList.add("connected");
            if (pillText) pillText.textContent = "Notion";
            hubBtn.title = `Notion Connected (${data.workspace_name || "Workspace"})`;
        } else {
            hubBtn.classList.remove("connected");
            if (pillText) pillText.textContent = "Notion";
            hubBtn.title = "Connect to Notion";
        }
    }

    const stateDisc = document.getElementById("notion-state-disconnected");
    const stateConn = document.getElementById("notion-state-connected");

    if (data && data.connected) {
        if (stateDisc) stateDisc.style.display = "none";
        if (stateConn) stateConn.style.display = "block";

        const wsNameEl = document.getElementById("notion-connected-workspace-name");
        if (wsNameEl) wsNameEl.textContent = data.workspace_name || "Personal Notion Workspace";

        const probLink = document.getElementById("link-notion-problems-db");
        if (probLink && data.problems_db_id) {
            const cleanId = data.problems_db_id.replace(/-/g, "");
            probLink.href = `https://notion.so/${cleanId}`;
        }

        const scoreLink = document.getElementById("link-notion-scorecards-db");
        if (scoreLink && data.scorecards_db_id) {
            const cleanId = data.scorecards_db_id.replace(/-/g, "");
            scoreLink.href = `https://notion.so/${cleanId}`;
        }

        const autosyncEl = document.getElementById("toggle-notion-autosync");
        if (autosyncEl) {
            autosyncEl.checked = Boolean(data.auto_sync_enabled);
        }
    } else {
        if (stateDisc) stateDisc.style.display = "block";
        if (stateConn) stateConn.style.display = "none";
    }
}

export function openNotionModal() {
    const modal = document.getElementById("notion-modal");
    if (modal) {
        modal.style.display = "flex";
        clearNotionAlert();
        refreshNotionStatus();
    }
}

async function handleNotionConnect(e) {
    e.preventDefault();
    clearNotionAlert();

    const tokenInput = document.getElementById("notion-token-input");
    const parentPageInput = document.getElementById("notion-parent-page-input");
    const autoProvisionCheck = document.getElementById("notion-auto-provision-check");
    const submitBtn = document.getElementById("btn-submit-connect-notion");

    const token = tokenInput ? tokenInput.value.trim() : "";
    const parentPage = parentPageInput ? parentPageInput.value.trim() : "";
    const autoProvision = autoProvisionCheck ? autoProvisionCheck.checked : true;

    if (!token) {
        showNotionAlert("Please enter your Notion Internal Integration Secret.", "error");
        return;
    }

    const origHtml = submitBtn ? submitBtn.innerHTML : "";
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Verifying &amp; Auto-Provisioning...`;
    }

    try {
        const resp = await fetch("/api/notion/connect", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                token: token,
                parent_page_id: parentPage,
                auto_provision: autoProvision,
            }),
        });

        const data = await resp.json();
        if (!resp.ok || !data.success) {
            throw new Error(data.error || "Failed to connect Notion workspace.");
        }

        tokenInput.value = "";
        if (parentPageInput) parentPageInput.value = "";

        showNotionAlert("Connected successfully! Your Notion workspace has been provisioned.", "success");
        await refreshNotionStatus();
    } catch (err) {
        showNotionAlert(err.message || "Failed to connect to Notion.", "error");
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = origHtml;
        }
    }
}

async function handleNotionDisconnect() {
    if (!confirm("Are you sure you want to disconnect your Notion workspace?")) return;

    try {
        const resp = await fetch("/api/notion/disconnect", { method: "POST" });
        const data = await resp.json();
        if (!resp.ok || !data.success) {
            throw new Error(data.error || "Failed to disconnect.");
        }
        await refreshNotionStatus();
        showNotionAlert("Notion workspace disconnected.", "info");
    } catch (err) {
        showNotionAlert(err.message || "Error disconnecting.", "error");
    }
}

/**
 * Sync active problem, code solution, and study notes to Notion.
 */
export async function syncActiveProblemToNotion(triggerBtn = null) {
    if (!isNotionConnected) {
        openNotionModal();
        showNotionAlert("Please connect your Notion workspace first to enable automated note syncing.", "info");
        return;
    }

    const problemTitleEl = document.getElementById("prob-title");
    const problemId = window.currentProblemId || (problemTitleEl ? problemTitleEl.dataset.problemId : null);
    if (!problemId) {
        alert("No problem currently active in the Studio to sync.");
        return;
    }

    const code = document.getElementById("code-editor")?.value || "";
    const notes = document.getElementById("prob-notes-input")?.value || "";

    const origHtml = triggerBtn ? triggerBtn.innerHTML : "";
    if (triggerBtn) {
        triggerBtn.disabled = true;
        triggerBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Syncing...`;
    }

    try {
        const resp = await fetch("/api/notion/sync-problem", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                problem_id: problemId,
                code: code,
                notes: notes,
            }),
        });

        const data = await resp.json();
        if (!resp.ok || !data.success) {
            throw new Error(data.error || "Sync failed.");
        }

        if (triggerBtn) {
            triggerBtn.innerHTML = `<i class="fa-solid fa-check text-green"></i> Synced to Notion`;
            setTimeout(() => {
                triggerBtn.innerHTML = origHtml;
                triggerBtn.disabled = false;
            }, 3500);
        }

        if (data.url) {
            const viewNow = confirm("Successfully synced to Notion! Would you like to open your Notion page now?");
            if (viewNow) {
                window.open(data.url, "_blank");
            }
        }
    } catch (err) {
        alert(`Notion Sync Error: ${err.message}`);
        if (triggerBtn) {
            triggerBtn.disabled = false;
            triggerBtn.innerHTML = origHtml;
        }
    }
}

/**
 * Export mock interview scorecard to Notion.
 */
export async function exportScorecardToNotion(triggerBtn = null) {
    if (!isNotionConnected) {
        openNotionModal();
        showNotionAlert("Please connect your Notion workspace first to export interview scorecards.", "info");
        return;
    }

    // Obtain active session ID from window or interview module
    const sessionId = window.currentInterviewSessionId;
    if (!sessionId) {
        alert("No completed mock interview session found to export.");
        return;
    }

    const origHtml = triggerBtn ? triggerBtn.innerHTML : "";
    if (triggerBtn) {
        triggerBtn.disabled = true;
        triggerBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Exporting...`;
    }

    try {
        const resp = await fetch("/api/notion/sync-interview", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId }),
        });

        const data = await resp.json();
        if (!resp.ok || !data.success) {
            throw new Error(data.error || "Export failed.");
        }

        if (triggerBtn) {
            triggerBtn.innerHTML = `<i class="fa-solid fa-check text-green"></i> Exported to Notion`;
            setTimeout(() => {
                triggerBtn.innerHTML = origHtml;
                triggerBtn.disabled = false;
            }, 3500);
        }

        if (data.url) {
            const viewNow = confirm("Scorecard exported to Notion! Would you like to open the Notion page now?");
            if (viewNow) {
                window.open(data.url, "_blank");
            }
        }
    } catch (err) {
        alert(`Notion Export Error: ${err.message}`);
        if (triggerBtn) {
            triggerBtn.disabled = false;
            triggerBtn.innerHTML = origHtml;
        }
    }
}

function showNotionAlert(msg, type = "info") {
    const alertBox = document.getElementById("notion-alert");
    if (!alertBox) return;

    alertBox.textContent = msg;
    alertBox.className = `auth-alert alert-${type}`;
    alertBox.style.display = "block";
}

function clearNotionAlert() {
    const alertBox = document.getElementById("notion-alert");
    if (alertBox) alertBox.style.display = "none";
}
