import { state, els } from "./state.js";

export function toast(message, isError = false) {
    if (!els.toast) return;
    els.toast.textContent = message;
    els.toast.classList.toggle("error", isError);
    els.toast.classList.add("show");
    setTimeout(() => els.toast.classList.remove("show"), 2400);
}

export function updateMetricsFromConfig() {
    const cfg = state.config;
    const postEl = document.getElementById("metric-post");
    const delayEl = document.getElementById("metric-delay");
    if (postEl) postEl.textContent = cfg.post_ids && cfg.post_ids[0] !== undefined ? cfg.post_ids.join(", ") : "-";
    if (delayEl) delayEl.textContent = cfg.request_delay || 0;
}

export function renderCommunitySelect() {
    if (!els.communitySelect) return;
    els.communitySelect.innerHTML = "";
    if (!state.communities || !state.communities.length) {
        els.communitySelect.innerHTML = '<option value="">Нет сообществ</option>';
        return;
    }
    state.communities.forEach((c) => {
        const opt = document.createElement("option");
        opt.value = c.group_id;
        opt.textContent = c.name || `Группа ${c.group_id}`;
        if (Number(state.activeGroupId) === Number(c.group_id)) opt.selected = true;
        els.communitySelect.appendChild(opt);
    });
}

export function renderSelectedPosts() {
    const list = [...state.selected];
    if (!list.length) {
        els.selectedPosts.textContent = "Посты не выбраны.";
    } else {
        els.selectedPosts.textContent = `Выбрано постов: ${list.join(", ")}`;
    }
    updateMetricsFromConfig();
}

export function renderPosts(items) {
    state.posts = items || [];
    els.postsList.innerHTML = "";
    if (!state.posts.length) {
        els.postsList.innerHTML = '<div class="empty">В ленте нет постов или неверный токен.</div>';
        return;
    }

    state.posts.forEach((post) => {
        const wrapper = document.createElement("label");
        const hasWatch = (state.watchers || []).some((w) => Number(w.post_id) === Number(post.id) && w.status === "running");
        wrapper.className = "post" + (hasWatch ? " watched" : "");
        
        // Форматируем дату
        const date = post.date ? new Date(post.date).toLocaleDateString("ru-RU") : "";
        
        // Иконки вложений
        const attachments = [];
        if (post.has_photo) attachments.push("📷");
        if (post.has_video) attachments.push("🎥");
        if (post.attachments_count > 0 && !post.has_photo && !post.has_video) {
            attachments.push(`📎 ${post.attachments_count}`);
        }
        const attachmentsStr = attachments.length > 0 ? ` ${attachments.join(" ")}` : "";
        
        wrapper.innerHTML = `
            <input type="checkbox" name="postIds" value="${post.id}" ${state.selected.has(post.id) ? "checked" : ""}>
            <div>
                <h4>#${post.id}${attachmentsStr}</h4>
                <p>${post.preview || "Без текста"}</p>
                <div class="meta">
                    <span>👁️ ${post.views || 0}</span>
                    <span>💬 ${post.comments || 0}</span>
                    <span>❤️ ${post.likes || 0}</span>
                    <span>🔄 ${post.reposts || 0}</span>
                    ${date ? `<span class="muted">${date}</span>` : ""}
                    ${hasWatch ? `<span class="pill watched">Автоответ</span>` : ""}
                </div>
            </div>
        `;
        wrapper.querySelector("input").addEventListener("change", (e) => {
            const id = Number(e.target.value);
            if (e.target.checked) {
                state.selected.add(id);
            } else {
                state.selected.delete(id);
            }
            renderSelectedPosts();
        });
        els.postsList.appendChild(wrapper);
    });
    renderSelectedPosts();
}

export function updateGroupInfo(groupInfo) {
    const nameEl = document.getElementById("metric-group-name");
    const membersEl = document.getElementById("metric-members");
    
    if (nameEl) {
        nameEl.textContent = groupInfo.name || "Не загружено";
    }
    if (membersEl) {
        const count = groupInfo.members_count || 0;
        membersEl.textContent = count > 0 ? count.toLocaleString("ru-RU") : "-";
    }
}

export function updateLog(logLines) {
    els.log.innerHTML = "";
    if (!logLines || !logLines.length) {
        els.log.innerHTML = '<div class="row">Лог пуст.</div>';
        return;
    }
    logLines.slice(-30).forEach((line) => {
        const row = document.createElement("div");
        row.className = "row";
        row.textContent = line;
        els.log.appendChild(row);
    });
}

export function updateTaskUI(task) {
    if (!task) return;
    const { sent = 0, failed = 0, total = 0, status, log } = task;
    const progress = total ? Math.min(100, Math.round(((sent + failed) / total) * 100)) : 0;

    els.progressBar.style.width = `${progress}%`;
    els.progressStatus.textContent = status || "Ожидание";
    els.progressCounter.textContent = `${sent + failed} / ${total}`;
    els.counterSent.textContent = sent;
    els.counterFailed.textContent = failed;
    els.counterTotal.textContent = total;
    els.statusDot.dataset.state = status || "idle";
    updateLog(log);
}

export function renderTasksTable(items) {
    els.tasksTable.innerHTML = "";
    if (!items.length) {
        els.tasksTable.innerHTML = '<div class="empty">Пока нет запущенных задач.</div>';
        return;
    }
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
        els.tasksTable.appendChild(row);
    });
}

export function renderWatchers(items) {
    if (!els.watchStats) return;
    els.watchStats.innerHTML = "";
    if (!items.length) {
        els.watchStats.innerHTML = '<div class="empty">Нет активных автоответов.</div>';
        if (els.watchBadge) els.watchBadge.textContent = "0";
        return;
    }
    if (els.watchBadge) els.watchBadge.textContent = items.length.toString();
    items.forEach((w) => {
        const row = document.createElement("div");
        row.className = "row";
        row.innerHTML = `
            <div class="muted">Пост ${w.post_id}</div>
            <div class="pill ${w.status}">${w.status}</div>
            <div class="muted">Ответов: ${w.replied}</div>
            <div class="muted">Ошибок: ${w.errors}</div>
        `;
        els.watchStats.appendChild(row);
    });
}
