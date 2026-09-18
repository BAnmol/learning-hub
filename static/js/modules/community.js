// ============================================================================
// Community — a single public chat room every registered member shares, plus
// private one-on-one direct messages. Registered-users-only: there's no
// separate "guest" role in this app, so this module (like every other
// feature module) is dormant until a login is confirmed — see app.js.
//
// No WebSocket infrastructure exists in this app, so both the public room
// and DM threads use lightweight polling (fetch "anything newer than the
// last message id I have") instead. Polling only runs while the Community
// tab is actually visible — see the onModeChange hook in initCommunity().
// ============================================================================
import { apiJson, escapeHtml } from "./utils.js?v=8.0";
import { getUser } from "./auth.js?v=8.0";
import { onModeChange } from "./nav.js?v=8.0";

const CHAT_POLL_MS = 4000;
const DM_POLL_MS = 4000;
const CONVERSATIONS_POLL_MS = 8000;

let wired = false;
let activeSubTab = "chat"; // 'chat' | 'dm'

let lastChatMessageId = 0;
let chatPollTimer = null;

let activeConversationUserId = null;
let lastDmMessageId = 0;
let dmPollTimer = null;
let conversationsPollTimer = null;
let userSearchDebounce = null;

let subTabs, chatPane, dmPane;
let chatMessages, chatForm, chatInput;
let dmConversationsList, dmThreadEmpty, dmThreadActive, dmThreadMessages, dmThreadForm, dmThreadInput;
let dmThreadUsername, dmThreadAvatar;
let btnNewDm, dmNewConvoBox, dmUserSearch, dmUserSearchResults;
let dmUnreadPill, navUnreadPill;

function cacheDom() {
    subTabs = document.querySelectorAll(".community-sub-tab");
    chatPane = document.getElementById("community-pane-chat");
    dmPane = document.getElementById("community-pane-dm");

    chatMessages = document.getElementById("community-chat-messages");
    chatForm = document.getElementById("community-chat-form");
    chatInput = document.getElementById("community-chat-input");

    dmConversationsList = document.getElementById("dm-conversations-list");
    dmThreadEmpty = document.getElementById("dm-thread-empty");
    dmThreadActive = document.getElementById("dm-thread-active");
    dmThreadMessages = document.getElementById("dm-thread-messages");
    dmThreadForm = document.getElementById("dm-thread-form");
    dmThreadInput = document.getElementById("dm-thread-input");
    dmThreadUsername = document.getElementById("dm-thread-username");
    dmThreadAvatar = document.getElementById("dm-thread-avatar");

    btnNewDm = document.getElementById("btn-new-dm");
    dmNewConvoBox = document.getElementById("dm-new-convo-box");
    dmUserSearch = document.getElementById("dm-user-search");
    dmUserSearchResults = document.getElementById("dm-user-search-results");

    dmUnreadPill = document.getElementById("dm-unread-pill");
    navUnreadPill = document.getElementById("community-unread-pill");
}

function autoResize(el) {
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
}

function renderMessageTime(createdAt) {
    // created_at is "YYYY-MM-DD HH:MM:SS" server time — show just HH:MM.
    if (!createdAt) return "";
    const parts = createdAt.split(" ");
    return parts.length > 1 ? parts[1].slice(0, 5) : createdAt;
}

function wireSubTabs() {
    subTabs.forEach((tab) => {
        tab.addEventListener("click", () => switchSubTab(tab.dataset.ctab));
    });
}

function switchSubTab(target) {
    if (target === activeSubTab) return;
    activeSubTab = target;
    subTabs.forEach((t) => t.classList.toggle("active", t.dataset.ctab === target));
    chatPane.classList.toggle("hidden", target !== "chat");
    dmPane.classList.toggle("hidden", target !== "dm");

    if (target === "chat") {
        stopDmPolling();
        stopConversationsPolling();
        loadChatMessages();
        startChatPolling();
    } else {
        stopChatPolling();
        loadConversations();
        startConversationsPolling();
        if (activeConversationUserId) startDmPolling();
    }
}

// ============================================================================
// Public Community Chat
// ============================================================================

function appendChatMessage(msg) {
    const welcome = chatMessages.querySelector(".community-chat-welcome");
    if (welcome) welcome.remove();

    const isSelf = msg.user_id === getUser()?.id;
    const wrap = document.createElement("div");
    wrap.className = `community-msg${isSelf ? " community-msg-self" : ""}`;
    wrap.innerHTML = `
        <div class="community-msg-avatar">${escapeHtml((msg.username || "?").charAt(0).toUpperCase())}</div>
        <div class="community-msg-body">
            <div class="community-msg-meta"><strong>${escapeHtml(msg.username)}</strong> <span class="community-msg-time">${renderMessageTime(msg.created_at)}</span></div>
            <div class="community-msg-text">${escapeHtml(msg.message)}</div>
        </div>
    `;
    chatMessages.appendChild(wrap);
}

async function loadChatMessages() {
    try {
        const data = await apiJson("/api/community/messages?limit=50");
        if (data.success && data.messages) {
            chatMessages.innerHTML = "";
            if (!data.messages.length) {
                chatMessages.innerHTML = `
                    <div class="community-chat-welcome">
                        <div class="community-chat-welcome-icon"><i class="fa-solid fa-people-group"></i></div>
                        <h3>Welcome to the Community</h3>
                        <p>One shared room for every member. Ask questions, share progress, or just say hi.</p>
                    </div>
                `;
            } else {
                data.messages.forEach(appendChatMessage);
                lastChatMessageId = data.messages[data.messages.length - 1].id;
            }
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    } catch (e) { /* non-fatal */ }
}

async function pollChatMessages() {
    try {
        const data = await apiJson(`/api/community/messages?after_id=${lastChatMessageId}`);
        if (data.success && data.messages && data.messages.length) {
            const wasNearBottom = chatMessages.scrollHeight - chatMessages.scrollTop - chatMessages.clientHeight < 80;
            data.messages.forEach(appendChatMessage);
            lastChatMessageId = data.messages[data.messages.length - 1].id;
            if (wasNearBottom) chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    } catch (e) { /* non-fatal */ }
}

function startChatPolling() {
    stopChatPolling();
    chatPollTimer = setInterval(pollChatMessages, CHAT_POLL_MS);
}

function stopChatPolling() {
    if (chatPollTimer) { clearInterval(chatPollTimer); chatPollTimer = null; }
}

async function sendChatMessage(text) {
    const trimmed = text.trim();
    if (!trimmed) return;
    try {
        const data = await apiJson("/api/community/messages", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: trimmed }),
        });
        if (data.success && data.message_data) {
            appendChatMessage(data.message_data);
            lastChatMessageId = data.message_data.id;
            chatMessages.scrollTop = chatMessages.scrollHeight;
        } else if (data.error) {
            alert(data.error);
        }
    } catch (e) { /* non-fatal */ }
}

function wireChatForm() {
    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const text = chatInput.value;
        chatInput.value = "";
        autoResize(chatInput);
        sendChatMessage(text);
    });
    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            chatForm.requestSubmit();
        }
    });
    chatInput.addEventListener("input", () => autoResize(chatInput));
}

// ============================================================================
// Direct Messages
// ============================================================================

function updateUnreadBadges(conversations) {
    const totalUnread = conversations.reduce((sum, c) => sum + (c.unread_count || 0), 0);
    [dmUnreadPill, navUnreadPill].forEach((pill) => {
        if (!pill) return;
        if (totalUnread > 0) {
            pill.textContent = totalUnread > 99 ? "99+" : String(totalUnread);
            pill.classList.remove("hidden");
        } else {
            pill.classList.add("hidden");
        }
    });
}

async function loadConversations() {
    try {
        const data = await apiJson("/api/community/conversations");
        if (data.success) {
            renderConversations(data.conversations || []);
            updateUnreadBadges(data.conversations || []);
        }
    } catch (e) { /* non-fatal */ }
}

function renderConversations(conversations) {
    if (!dmConversationsList) return;
    if (!conversations.length) {
        dmConversationsList.innerHTML = `<div class="dm-empty-hint">No conversations yet.<br>Click <i class="fa-solid fa-square-pen"></i> above to message someone.</div>`;
        return;
    }
    dmConversationsList.innerHTML = conversations.map((c) => `
        <button type="button" class="dm-convo-item${c.other_user_id === activeConversationUserId ? " active" : ""}" data-uid="${c.other_user_id}" data-uname="${escapeHtml(c.other_username)}">
            <div class="dm-convo-avatar">${escapeHtml((c.other_username || "?").charAt(0).toUpperCase())}</div>
            <div class="dm-convo-meta">
                <span class="dm-convo-name">${escapeHtml(c.other_username)}</span>
                <span class="dm-convo-preview">${escapeHtml((c.last_message || "").slice(0, 42))}</span>
            </div>
            ${c.unread_count > 0 ? `<span class="dm-convo-unread">${c.unread_count > 99 ? "99+" : c.unread_count}</span>` : ""}
        </button>
    `).join("");

    dmConversationsList.querySelectorAll(".dm-convo-item").forEach((btn) => {
        btn.addEventListener("click", () => openConversation(Number(btn.dataset.uid), btn.dataset.uname));
    });
}

function startConversationsPolling() {
    stopConversationsPolling();
    conversationsPollTimer = setInterval(loadConversations, CONVERSATIONS_POLL_MS);
}

function stopConversationsPolling() {
    if (conversationsPollTimer) { clearInterval(conversationsPollTimer); conversationsPollTimer = null; }
}

function appendDmMessage(msg) {
    const isSelf = msg.sender_id === getUser()?.id;
    const wrap = document.createElement("div");
    wrap.className = `community-msg${isSelf ? " community-msg-self" : ""}`;
    wrap.innerHTML = `
        <div class="community-msg-body">
            <div class="community-msg-text">${escapeHtml(msg.message)}</div>
            <div class="community-msg-time">${renderMessageTime(msg.created_at)}</div>
        </div>
    `;
    dmThreadMessages.appendChild(wrap);
}

async function openConversation(userId, username) {
    activeConversationUserId = userId;
    lastDmMessageId = 0;
    if (dmNewConvoBox) dmNewConvoBox.classList.add("hidden");
    if (dmUserSearch) dmUserSearch.value = "";

    dmThreadEmpty.classList.add("hidden");
    dmThreadActive.classList.remove("hidden");
    dmThreadUsername.textContent = username;
    dmThreadAvatar.textContent = (username || "?").charAt(0).toUpperCase();
    dmThreadMessages.innerHTML = `<div class="dm-thread-loading"><i class="fa-solid fa-spinner fa-spin"></i></div>`;

    dmConversationsList.querySelectorAll(".dm-convo-item").forEach((b) => {
        b.classList.toggle("active", Number(b.dataset.uid) === userId);
    });

    try {
        const data = await apiJson(`/api/community/dm/${userId}?limit=100`);
        dmThreadMessages.innerHTML = "";
        if (data.success && data.messages) {
            data.messages.forEach(appendDmMessage);
            if (data.messages.length) lastDmMessageId = data.messages[data.messages.length - 1].id;
            dmThreadMessages.scrollTop = dmThreadMessages.scrollHeight;
        }
    } catch (e) { /* non-fatal */ }

    startDmPolling();
    loadConversations(); // refresh unread counts now that this thread has been read
}

async function pollDmMessages() {
    if (!activeConversationUserId) return;
    try {
        const data = await apiJson(`/api/community/dm/${activeConversationUserId}?after_id=${lastDmMessageId}`);
        if (data.success && data.messages && data.messages.length) {
            data.messages.forEach(appendDmMessage);
            lastDmMessageId = data.messages[data.messages.length - 1].id;
            dmThreadMessages.scrollTop = dmThreadMessages.scrollHeight;
        }
    } catch (e) { /* non-fatal */ }
}

function startDmPolling() {
    stopDmPolling();
    dmPollTimer = setInterval(pollDmMessages, DM_POLL_MS);
}

function stopDmPolling() {
    if (dmPollTimer) { clearInterval(dmPollTimer); dmPollTimer = null; }
}

async function sendDmMessage(text) {
    const trimmed = text.trim();
    if (!trimmed || !activeConversationUserId) return;
    try {
        const data = await apiJson(`/api/community/dm/${activeConversationUserId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: trimmed }),
        });
        if (data.success && data.message_data) {
            appendDmMessage(data.message_data);
            lastDmMessageId = data.message_data.id;
            dmThreadMessages.scrollTop = dmThreadMessages.scrollHeight;
            loadConversations();
        } else if (data.error) {
            alert(data.error);
        }
    } catch (e) { /* non-fatal */ }
}

function wireDmForm() {
    dmThreadForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const text = dmThreadInput.value;
        dmThreadInput.value = "";
        autoResize(dmThreadInput);
        sendDmMessage(text);
    });
    dmThreadInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            dmThreadForm.requestSubmit();
        }
    });
    dmThreadInput.addEventListener("input", () => autoResize(dmThreadInput));
}

function wireNewDm() {
    btnNewDm.addEventListener("click", () => {
        dmNewConvoBox.classList.toggle("hidden");
        if (!dmNewConvoBox.classList.contains("hidden")) {
            dmUserSearch.focus();
            searchUsers("");
        }
    });

    dmUserSearch.addEventListener("input", () => {
        clearTimeout(userSearchDebounce);
        userSearchDebounce = setTimeout(() => searchUsers(dmUserSearch.value.trim()), 250);
    });
}

async function searchUsers(query) {
    try {
        const data = await apiJson(`/api/community/users?search=${encodeURIComponent(query)}`);
        if (data.success) renderUserSearchResults(data.users || []);
    } catch (e) { /* non-fatal */ }
}

function renderUserSearchResults(users) {
    if (!users.length) {
        dmUserSearchResults.innerHTML = `<div class="dm-empty-hint">No members found.</div>`;
        return;
    }
    dmUserSearchResults.innerHTML = users.map((u) => `
        <button type="button" class="dm-user-result" data-uid="${u.id}" data-uname="${escapeHtml(u.username)}">
            <div class="dm-convo-avatar">${escapeHtml(u.username.charAt(0).toUpperCase())}</div>
            <span>${escapeHtml(u.username)}</span>
        </button>
    `).join("");

    dmUserSearchResults.querySelectorAll(".dm-user-result").forEach((btn) => {
        btn.addEventListener("click", () => openConversation(Number(btn.dataset.uid), btn.dataset.uname));
    });
}

// ============================================================================
// Lifecycle
// ============================================================================

export function initCommunity() {
    if (wired) return;
    cacheDom();
    wireSubTabs();
    wireChatForm();
    wireDmForm();
    wireNewDm();
    wired = true;

    // This is the only feature module that polls on an interval — stop
    // every timer the instant the user navigates to a different tab.
    onModeChange((mode) => {
        if (mode !== "community") {
            stopChatPolling();
            stopDmPolling();
            stopConversationsPolling();
        }
    });
}

/** Called every time the Community tab becomes active. */
export function onShow() {
    if (!wired) initCommunity();
    if (activeSubTab === "chat") {
        loadChatMessages();
        startChatPolling();
    } else {
        loadConversations();
        startConversationsPolling();
        if (activeConversationUserId) startDmPolling();
    }
}

const GLOBAL_UNREAD_POLL_MS = 30000;
let globalUnreadPollTimer = null;

/** Lightweight unread-DM badge refresh — safe to call right after login,
 *  before the user has ever opened the Community tab. Also starts a slow
 *  background poll (once) so the nav badge notices a new DM even while the
 *  user is off on another tab entirely — everything else in this module
 *  only polls while Community is the active tab. */
export async function refreshUnreadBadge() {
    try {
        const data = await apiJson("/api/community/conversations");
        if (data.success) updateUnreadBadges(data.conversations || []);
    } catch (e) { /* non-fatal */ }

    if (!globalUnreadPollTimer) {
        globalUnreadPollTimer = setInterval(refreshUnreadBadge, GLOBAL_UNREAD_POLL_MS);
    }
}
