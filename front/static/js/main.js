import { state, els } from "./state.js";
import {
    toast,
    renderPosts,
    renderSelectedPosts,
    updateMetricsFromConfig,
    updateTaskUI,
    renderTasksTable,
    updateGroupInfo,
    renderCommunitySelect,
    renderWatchers,
} from "./ui.js";
import {
    loadPosts,
    startSend,
    fetchTask,
    fetchTasks,
    fetchGroupInfo,
    setActiveGroup,
    startWatch,
    fetchWatchers,
} from "./api.js";

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

async function refreshWatchers() {
    state.watchers = await fetchWatchers();
    renderWatchers(state.watchers);
    renderPosts(state.posts); // обновляем подсветку постов
}

async function handleChangeCommunity(groupId) {
    try {
        const data = await setActiveGroup(groupId);
        state.config = data;
        state.communities = data.communities || [];
        state.activeGroupId = data.active_group_id;
        state.selected = new Set();
        renderCommunitySelect();
        renderSelectedPosts();
        updateMetricsFromConfig();
        const groupInfo = await fetchGroupInfo();
        if (groupInfo) updateGroupInfo(groupInfo);
        const items = await loadPosts();
        if (items.length > 0) {
            renderPosts(items);
            toast("Сообщество переключено");
        }
    } catch (err) {
        toast("Не удалось переключить сообщество", true);
    }
}

async function handleStartWatch() {
    const postIds = [...state.selected];
    const message = document.getElementById("watch_message")?.value.trim() || "";
    if (!postIds.length) {
        toast("Выберите пост для автоответа", true);
        return;
    }
    if (!message) {
        toast("Введите текст автоответа", true);
        return;
    }
    try {
        await startWatch(postIds[0], message);
        toast("Автоответ запущен");
        await refreshWatchers();
        await handleLoadPosts();
    } catch (err) {
        toast("Не удалось запустить автоответ", true);
    }
}

function bindEvents() {
    els.communitySelect?.addEventListener("change", (e) => {
        const val = Number(e.target.value);
        if (val) {
            handleChangeCommunity(val);
        }
    });
    els.btnLoadPosts?.addEventListener("click", (e) => {
        e.preventDefault();
        handleLoadPosts();
    });
    els.btnStartSend?.addEventListener("click", (e) => {
        e.preventDefault();
        handleStartSend();
    });
    document.getElementById("btn-start-watch")?.addEventListener("click", (e) => {
        e.preventDefault();
        handleStartWatch();
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
    renderCommunitySelect();
    bindEvents();
    updateMetricsFromConfig();
    refreshTasks();
    refreshWatchers();
    loadGroupInfo(); // Загружаем информацию о группе
}

document.addEventListener("DOMContentLoaded", init);
