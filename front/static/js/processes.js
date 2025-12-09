import { toast } from "./ui.js";

async function fetchJson(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(await res.text());
    return await res.json();
}

async function loadTasks() {
    const container = document.getElementById("process-tasks");
    if (!container) return;
    container.innerHTML = '<div class="empty">Загрузка...</div>';
    try {
        const data = await fetchJson("/api/tasks");
        const items = data.items || [];
        if (!items.length) {
            container.innerHTML = '<div class="empty">Пока нет задач.</div>';
            return;
        }
        container.innerHTML = "";
        items.forEach((task) => {
            const row = document.createElement("div");
            row.className = "row";
            const posts = (task.post_ids || []).length ? task.post_ids.join(", ") : "—";
            row.innerHTML = `
                <div>#${task.id}</div>
                <div class="muted">Посты: ${posts}</div>
                <div><span class="pill ${task.status}">${task.status}</span></div>
                <div class="muted">${task.sent}/${task.total}</div>
            `;
            container.appendChild(row);
        });
    } catch (err) {
        container.innerHTML = `<div class="empty">Ошибка загрузки задач</div>`;
        toast("Не удалось загрузить задачи", true);
    }
}

async function loadWatchers() {
    const container = document.getElementById("process-watchers");
    if (!container) return;
    container.innerHTML = '<div class="empty">Загрузка...</div>';
    try {
        const data = await fetchJson("/api/watch");
        const items = data.items || [];
        if (!items.length) {
            container.innerHTML = '<div class="empty">Нет активных автоответов.</div>';
            return;
        }
        container.innerHTML = "";
        items.forEach((w) => {
            const row = document.createElement("div");
            row.className = "row";
            row.innerHTML = `
                <div class="muted">Пост ${w.post_id}</div>
                <div><span class="pill ${w.status}">${w.status}</span></div>
                <div class="muted">Ответов: ${w.replied}</div>
                <div class="muted">Ошибок: ${w.errors}</div>
            `;
            container.appendChild(row);
        });
    } catch (err) {
        container.innerHTML = `<div class="empty">Ошибка загрузки автоответов</div>`;
        toast("Не удалось загрузить автоответы", true);
    }
}

function bindButtons() {
    document.getElementById("btn-refresh-tasks")?.addEventListener("click", (e) => {
        e.preventDefault();
        loadTasks();
    });
    document.getElementById("btn-refresh-watchers")?.addEventListener("click", (e) => {
        e.preventDefault();
        loadWatchers();
    });
}

function init() {
    bindButtons();
    loadTasks();
    loadWatchers();
    setInterval(() => {
        loadTasks();
        loadWatchers();
    }, 5000);
}

document.addEventListener("DOMContentLoaded", init);
