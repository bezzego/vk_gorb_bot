import { state, els } from "./state.js";
import { toast, renderPosts, renderSelectedPosts, updateMetricsFromConfig, updateTaskUI, renderTasksTable, updateGroupInfo } from "./ui.js";
import { loadPosts, startSend, fetchTask, fetchTasks, fetchGroupInfo } from "./api.js";

async function handleLoadPosts() {
    const items = await loadPosts();
    if (items.length > 0) {
        renderPosts(items);
        toast("Посты обновлены");
    }
}

async function handleStartSend() {
    const postIds = [...state.selected];
    const message = els.sendMessage.value.trim();

    if (!postIds.length) {
        toast("Выберите хотя бы один пост", true);
        return;
    }
    if (!message) {
        toast("Введите текст сообщения", true);
        return;
    }
    try {
        const data = await startSend(postIds, message);
        state.currentTaskId = data.task_id;
        toast("Задача запущена");
        pollTask(data.task_id);
        refreshTasks();
    } catch (err) {
        // Error already handled in api.js
    }
}

async function pollTask(taskId) {
    if (state.pollHandle) clearInterval(state.pollHandle);

    const tick = async () => {
        const data = await fetchTask(taskId);
        if (!data) return;
        updateTaskUI(data);
        if (["completed", "failed"].includes(data.status)) {
            clearInterval(state.pollHandle);
            state.pollHandle = null;
            refreshTasks();
        }
    };

    await tick();
    state.pollHandle = setInterval(tick, 1500);
}

async function refreshTasks() {
    const items = await fetchTasks();
    renderTasksTable(items);
}

function bindEvents() {
    els.btnLoadPosts?.addEventListener("click", (e) => {
        e.preventDefault();
        handleLoadPosts();
    });
    els.btnStartSend?.addEventListener("click", (e) => {
        e.preventDefault();
        handleStartSend();
    });
    els.btnRefreshTasks?.addEventListener("click", (e) => {
        e.preventDefault();
        refreshTasks();
    });
    els.btnRefreshPosts?.addEventListener("click", (e) => {
        e.preventDefault();
        handleLoadPosts();
    });
    els.btnOpenSend?.addEventListener("click", (e) => {
        e.preventDefault();
        document.getElementById("send-form")?.scrollIntoView({ behavior: "smooth" });
    });
}

async function loadGroupInfo() {
    const groupInfo = await fetchGroupInfo();
    if (groupInfo) {
        updateGroupInfo(groupInfo);
    }
}

function init() {
    renderSelectedPosts();
    bindEvents();
    updateMetricsFromConfig();
    refreshTasks();
    loadGroupInfo(); // Загружаем информацию о группе
}

document.addEventListener("DOMContentLoaded", init);

