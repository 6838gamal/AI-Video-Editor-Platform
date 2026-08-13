// Global helpers and auth state
const API = {
    get: (url) => fetch(url).then(r => r.json()),
    post: (url, body) => fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    }).then(r => r.json()),
    postForm: (url, formData) => fetch(url, { method: "POST", body: formData }).then(r => r.json()),
    del: (url) => fetch(url, { method: "DELETE" }).then(r => r.json()),
};

function el(id) { return document.getElementById(id); }

function fmtDuration(s) {
    if (!s || s <= 0) return "—";
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
}

function fmtSize(bytes) {
    if (!bytes) return "—";
    const mb = bytes / (1024 * 1024);
    return mb >= 1 ? `${mb.toFixed(1)} MB` : `${(bytes / 1024).toFixed(0)} KB`;
}

async function loadAuthArea() {
    const area = el("auth-area");
    if (!area) return;
    try {
        const me = await API.get("/api/auth/me");
        if (me.fallback) {
            area.innerHTML = `<span class="user-chip">وضع تجريبي</span>`;
        } else {
            area.innerHTML = `<span class="user-chip">${escapeHtml(me.email)}</span><button class="btn-logout" onclick="logout()">خروج</button>`;
        }
    } catch { /* ignore */ }
}

async function logout() {
    await API.post("/api/auth/logout", {});
    window.location.href = "/";
}

async function loadSystemIndicator() {
    const ind = el("system-indicator");
    if (!ind) return;
    try {
        const s = await API.get("/api/system/status");
        const dbOk = s.database === "connected";
        const dot = dbOk ? "" : "warn";
        const label = dbOk ? "النظام جاهز" : "وضع متدني — قاعدة البيانات غير متاحة";
        ind.innerHTML = `<span class="sys-dot ${dot}"></span> ${label}`;
    } catch {
        ind.innerHTML = `<span class="sys-dot warn"></span> تعذّر فحص النظام`;
    }
}

function escapeHtml(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
}

document.addEventListener("DOMContentLoaded", () => {
    loadAuthArea();
    loadSystemIndicator();
});
