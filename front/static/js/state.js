export const state = {
    config: window.__CONFIG__ || {},
    posts: [],
    selected: new Set((window.__CONFIG__ && window.__CONFIG__.post_ids) || []),
    currentTaskId: null,
    pollHandle: null,
};

export const els = {
    toast: document.getElementById("toast"),
    postsList: document.getElementById("posts-list"),
    selectedPosts: document.getElementById("selected-posts"),
    sendForm: document.getElementById("send-form"),
    sendMessage: document.getElementById("send_message"),
    btnLoadPosts: document.getElementById("btn-load-posts"),
    btnStartSend: document.getElementById("btn-start-send"),
    btnRefreshTasks: document.getElementById("btn-refresh-tasks"),
    btnRefreshPosts: document.getElementById("btn-refresh-posts"),
    btnOpenSend: document.getElementById("btn-open-send"),
    progressBar: document.getElementById("progress-bar"),
    progressStatus: document.getElementById("progress-status"),
    progressCounter: document.getElementById("progress-counter"),
    counterSent: document.getElementById("counter-sent"),
    counterFailed: document.getElementById("counter-failed"),
    counterTotal: document.getElementById("counter-total"),
    statusDot: document.getElementById("status-dot"),
    log: document.getElementById("log"),
    tasksTable: document.getElementById("tasks-table"),
};

