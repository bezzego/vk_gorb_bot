import { state, els } from "./state.js";
import { toast } from "./ui.js";

export async function loadPosts() {
    els.postsList.innerHTML = '<div class="empty">Загружаю посты...</div>';
    try {
        const res = await fetch("/api/posts?limit=100");
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        return data.items || [];
    } catch (err) {
        els.postsList.innerHTML = `<div class="empty">Не удалось загрузить посты: ${err}</div>`;
        toast("Ошибка загрузки постов", true);
        return [];
    }
}

export async function startSend(postIds, message) {
    try {
        const res = await fetch("/api/send", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ post_ids: postIds, message }),
        });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        return data;
    } catch (err) {
        toast("Не удалось запустить рассылку", true);
        throw err;
    }
}

export async function fetchTask(taskId) {
    try {
        const res = await fetch(`/api/tasks/${taskId}`);
        if (!res.ok) return null;
        return await res.json();
    } catch (err) {
        console.error(err);
        return null;
    }
}

export async function fetchTasks() {
    try {
        const res = await fetch("/api/tasks");
        if (!res.ok) return [];
        const data = await res.json();
        return data.items || [];
    } catch (err) {
        console.error(err);
        return [];
    }
}

export async function fetchGroupInfo() {
    try {
        const res = await fetch("/api/group/info");
        if (!res.ok) return null;
        return await res.json();
    } catch (err) {
        console.error(err);
        return null;
    }
}

export async function fetchPostDetails(postId) {
    try {
        const res = await fetch(`/api/posts/${postId}`);
        if (!res.ok) return null;
        return await res.json();
    } catch (err) {
        console.error(err);
        return null;
    }
}

export async function setActiveGroup(groupId) {
    const res = await fetch("/api/config/active", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ group_id: Number(groupId) }),
    });
    if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail);
    }
    return await res.json();
}

export async function startWatch(postId, message) {
    const res = await fetch("/api/watch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ post_id: Number(postId), message }),
    });
    if (!res.ok) throw new Error(await res.text());
    return await res.json();
}

export async function fetchWatchers() {
    try {
        const res = await fetch("/api/watch");
        if (!res.ok) return [];
        const data = await res.json();
        return data.items || [];
    } catch (err) {
        console.error(err);
        return [];
    }
}
