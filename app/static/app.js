// ──────────────────────────────────────────────────────────────
// AI Assistant frontend — vanilla JS, single file.
// Talks to /api/v1/* HTTP + /api/v1/ws/* for streaming.
// ──────────────────────────────────────────────────────────────

const API = "/api/v1";
const WS_BASE = (location.protocol === "https:" ? "wss://" : "ws://") + location.host + API;

const $ = (id) => document.getElementById(id);
const messagesEl = $("messages");
const inputEl = $("input");
const formEl = $("input-form");
const sendBtn = $("send-btn");
const dropZone = $("drop-zone");
const fileInput = $("file-input");
const fileListEl = $("file-list");
const useRagEl = $("use-rag");
const agentModeEl = $("agent-mode");
const topkEl = $("topk");
const topkValEl = $("topk-val");
const clearBtn = $("clear-btn");
const statusDot = $("status-dot");
const statusText = $("status-text");

// ── State ──
let askSocket = null;
let agentSocket = null;
let isStreaming = false;

// ── Health check ──
async function pingHealth() {
    try {
        const r = await fetch(`${API}/health`);
        if (r.ok) {
            statusDot.classList.add("online"); statusDot.classList.remove("offline");
            statusText.textContent = "online";
        } else throw new Error();
    } catch {
        statusDot.classList.add("offline"); statusDot.classList.remove("online");
        statusText.textContent = "offline";
    }
}
pingHealth();
setInterval(pingHealth, 15000);

// ── Top-K slider live label ──
topkEl.addEventListener("input", () => {
    topkValEl.textContent = topkEl.value;
});

// ── Textarea auto-grow ──
inputEl.addEventListener("input", () => {
    inputEl.style.height = "auto";
    inputEl.style.height = Math.min(inputEl.scrollHeight, 200) + "px";
});
inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        formEl.requestSubmit();
    }
});

// ── Clear chat ──
clearBtn.addEventListener("click", () => {
    messagesEl.innerHTML = "";
});

// ── Message rendering helpers ──
function addMessage(role, text = "") {
    const wrap = document.createElement("div");
    wrap.className = `msg msg-${role}`;
    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    const content = document.createElement("div");
    content.className = "content";
    content.textContent = text;
    bubble.appendChild(content);
    wrap.appendChild(bubble);
    messagesEl.appendChild(wrap);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return { wrap, bubble, content };
}

function addCursor(bubble) {
    const cursor = document.createElement("span");
    cursor.className = "cursor";
    bubble.appendChild(cursor);
    return cursor;
}

function addSources(bubble, sources) {
    if (!sources || sources.length === 0) return;
    const box = document.createElement("div");
    box.className = "sources";
    box.innerHTML = `<strong>Sources</strong><ol>${sources
        .map((s) => `<li>${escapeHtml(s.id)} — ${escapeHtml((s.snippet || "").slice(0, 120))}…</li>`)
        .join("")}</ol>`;
    bubble.appendChild(box);
}

function addAgentStep(bubble, step) {
    const div = document.createElement("div");
    div.className = "agent-step";
    div.innerHTML = `
        <div class="label">${escapeHtml(step.action)}</div>
        <div class="content"><em>${escapeHtml(step.thought)}</em></div>
        <div class="content">${escapeHtml(step.observation || "")}</div>
    `;
    bubble.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, (c) =>
        ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );
}

// ── Submit message ──
formEl.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (isStreaming) return;
    const text = inputEl.value.trim();
    if (!text) return;

    inputEl.value = "";
    inputEl.style.height = "auto";
    addMessage("user", text);

    if (agentModeEl.checked) {
        await streamAgent(text);
    } else {
        await streamAsk(text);
    }
});

function setStreaming(state) {
    isStreaming = state;
    sendBtn.disabled = state;
}

// ── Ask streaming ──
async function streamAsk(question) {
    const { bubble, content } = addMessage("bot", "");
    const cursor = addCursor(bubble);
    setStreaming(true);

    // Get sources via HTTP first (cheap parallel call would be nicer but keeps it simple)
    let sources = [];
    if (useRagEl.checked) {
        // Sources will come via the HTTP /ask call — but we want streaming, so just fetch once via WS.
        // We render sources after stream completes by doing a lightweight HTTP /ask in parallel.
    }

    const sock = new WebSocket(`${WS_BASE}/ws/ask`);
    let acc = "";
    let receivedSources = null;

    sock.onopen = () => {
        sock.send(JSON.stringify({
            question,
            use_rag: useRagEl.checked,
            top_k: parseInt(topkEl.value, 10),
        }));
    };

    sock.onmessage = (event) => {
        const evt = JSON.parse(event.data);
        if (evt.type === "start") {
            // cursor already showing
        } else if (evt.type === "sources") {
            receivedSources = evt.data;
            // Log retrieval result to console for debugging — not shown in UI
            if (useRagEl.checked) {
                const files = [...new Set((receivedSources || []).map((s) => (s.id || "").split("#")[0]))];
                console.log(
                    `[retrieval] ${receivedSources.length} chunks from ${files.length} file(s):`,
                    files,
                    receivedSources,
                );
            }
        } else if (evt.type === "token") {
            acc += evt.data;
            content.textContent = acc;
            messagesEl.scrollTop = messagesEl.scrollHeight;
        } else if (evt.type === "end") {
            cursor.remove();
            sock.close();
            setStreaming(false);
        } else if (evt.type === "error") {
            content.textContent = `⚠️ ${JSON.stringify(evt.data)}`;
            cursor.remove();
            sock.close();
            setStreaming(false);
        }
    };

    sock.onerror = () => {
        content.textContent = "⚠️ Connection error.";
        cursor.remove();
        setStreaming(false);
    };
}

function renderRetrievalBadge(bubble, sources) {
    const badge = document.createElement("div");
    badge.className = "retrieval-badge";
    if (sources.length === 0) {
        badge.innerHTML = `<span class="dot offline"></span> No chunks retrieved — answering from general knowledge`;
        badge.classList.add("warn");
    } else {
        const names = [...new Set(sources.map((s) => (s.id || "").split("#")[0]))];
        badge.innerHTML = `<span class="dot online"></span> ${sources.length} chunks from ${names.length} file(s): ${escapeHtml(names.join(", "))}`;
    }
    bubble.insertBefore(badge, bubble.firstChild);
}

// ── Agent streaming ──
async function streamAgent(task) {
    const { bubble, content } = addMessage("bot", "");
    content.textContent = "Thinking…";
    setStreaming(true);

    const sock = new WebSocket(`${WS_BASE}/ws/agent`);

    sock.onopen = () => {
        sock.send(JSON.stringify({ task, max_steps: 5 }));
        content.textContent = "";
    };

    sock.onmessage = (event) => {
        const evt = JSON.parse(event.data);
        if (evt.type === "step") {
            addAgentStep(bubble, evt.data);
        } else if (evt.type === "final") {
            const finalP = document.createElement("p");
            finalP.innerHTML = `<strong>Answer:</strong> ${escapeHtml(evt.data)}`;
            bubble.appendChild(finalP);
            messagesEl.scrollTop = messagesEl.scrollHeight;
            sock.close();
            setStreaming(false);
        } else if (evt.type === "error") {
            content.textContent = `⚠️ ${JSON.stringify(evt.data)}`;
            sock.close();
            setStreaming(false);
        }
    };

    sock.onerror = () => {
        content.textContent = "⚠️ Connection error.";
        setStreaming(false);
    };
}

// ── File library (persisted) ──
async function refreshFileList() {
    try {
        const r = await fetch(`${API}/documents`);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = await r.json();
        renderFileList(data.documents);
    } catch (e) {
        console.warn("could not load documents", e);
    }
}

function renderFileList(docs) {
    fileListEl.innerHTML = "";
    if (!docs || docs.length === 0) {
        const empty = document.createElement("li");
        empty.className = "file-list-empty";
        empty.textContent = "No files yet — upload a PDF above.";
        fileListEl.appendChild(empty);
        return;
    }
    docs.forEach((d) => fileListEl.appendChild(renderFileItem(d)));
}

function renderFileItem(doc) {
    const li = document.createElement("li");
    li.className = "file-item";
    li.innerHTML = `
        <span style="color: var(--success); font-size: 14px;">✓</span>
        <span class="file-name" title="${escapeHtml(doc.source)}">${escapeHtml(doc.source)}</span>
        <span class="file-meta">${doc.chunks} chunks</span>
        <button class="delete-btn" title="Remove">✕</button>
    `;
    li.querySelector(".delete-btn").addEventListener("click", () => deleteDocument(doc.source));
    return li;
}

async function deleteDocument(source) {
    if (!confirm(`Remove "${source}" from the knowledge base?`)) return;
    try {
        const r = await fetch(`${API}/documents/${encodeURIComponent(source)}`, { method: "DELETE" });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        await refreshFileList();
    } catch (e) {
        alert(`Delete failed: ${e.message}`);
    }
}

function addPendingFileItem(name) {
    // Remove "empty" placeholder if present
    const empty = fileListEl.querySelector(".file-list-empty");
    if (empty) empty.remove();

    const li = document.createElement("li");
    li.className = "file-item";
    li.innerHTML = `
        <span class="spinner"></span>
        <span class="file-name">${escapeHtml(name)}</span>
        <span class="file-meta">uploading…</span>
    `;
    fileListEl.appendChild(li);
    return li;
}

async function uploadPdf(file) {
    const li = addPendingFileItem(file.name);
    const form = new FormData();
    form.append("file", file);

    try {
        const r = await fetch(`${API}/upload`, { method: "POST", body: form });
        if (!r.ok) {
            const err = await r.json().catch(() => ({}));
            throw new Error(err?.error?.message || `HTTP ${r.status}`);
        }
        await r.json();
        li.remove();
        await refreshFileList();
    } catch (e) {
        li.classList.add("error");
        li.innerHTML = `
            <span style="font-size: 14px;">✗</span>
            <span class="file-name">${escapeHtml(file.name)}</span>
            <span class="file-meta">${escapeHtml(e.message)}</span>
        `;
    }
}

// Drag & drop
["dragenter", "dragover"].forEach((ev) =>
    dropZone.addEventListener(ev, (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    })
);
["dragleave", "drop"].forEach((ev) =>
    dropZone.addEventListener(ev, (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
    })
);
dropZone.addEventListener("drop", (e) => {
    const files = [...e.dataTransfer.files].filter((f) => f.type === "application/pdf");
    files.forEach(uploadPdf);
});
fileInput.addEventListener("change", () => {
    [...fileInput.files].forEach(uploadPdf);
    fileInput.value = "";
});

// Hydrate file list on page load — files persist server-side
refreshFileList();
