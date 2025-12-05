const els = {
    toast: document.getElementById("toast"),
    btnSave: document.getElementById("btn-save-config"),
    btnAddCommunity: document.getElementById("btn-add-community"),
    communitiesList: document.getElementById("communities-list"),
    requestDelay: document.getElementById("request_delay"),
    promoMessage: document.getElementById("promo_message"),
    communityCount: document.getElementById("community-count"),
};

const state = {
    communities: (window.__CONFIG__ && window.__CONFIG__.communities) || [],
    activeGroupId: (window.__CONFIG__ && window.__CONFIG__.active_group_id) || null,
};

function toast(message, isError = false) {
    if (!els.toast) return;
    els.toast.textContent = message;
    els.toast.classList.toggle("error", isError);
    els.toast.classList.add("show");
    setTimeout(() => els.toast.classList.remove("show"), 2400);
}

function updateSummary() {
    if (els.communityCount) {
        els.communityCount.textContent = state.communities.length || 0;
    }
}

function renderCommunities() {
    if (!els.communitiesList) return;
    els.communitiesList.innerHTML = "";
    if (!state.communities.length) {
        const empty = document.createElement("div");
        empty.className = "empty";
        empty.textContent = "Добавьте первую группу";
        els.communitiesList.appendChild(empty);
        return;
    }

    state.communities.forEach((c, idx) => {
        const item = document.createElement("div");
        item.className = "community-item";
        item.innerHTML = `
            <div class="community-header">
                <div class="community-actions">
                    <span class="muted">Сообщество ${idx + 1}</span>
                </div>
                <button type="button" class="btn ghost btn-remove" data-index="${idx}">Удалить</button>
            </div>
            <div class="two-cols">
                <label>
                    <span>Название</span>
                    <input type="text" class="input-name" value="${c.name || ""}" placeholder="Название или пометка">
                </label>
                <label>
                    <span>ID группы</span>
                    <input type="number" class="input-group" value="${c.group_id || ""}" placeholder="223693021">
                </label>
            </div>
            <label>
                <span>USER_TOKEN</span>
                <textarea class="input-user-token" rows="2" placeholder="Токен пользователя">${c.user_token || ""}</textarea>
            </label>
            <label>
                <span>GROUP_TOKEN</span>
                <textarea class="input-group-token" rows="2" placeholder="Токен группы">${c.group_token || ""}</textarea>
            </label>
        `;

        item.querySelector(".btn-remove").addEventListener("click", () => {
            state.communities.splice(idx, 1);
            if (state.activeGroupId === c.group_id) {
                state.activeGroupId = state.communities[0]?.group_id || null;
            }
            renderCommunities();
        });

        els.communitiesList.appendChild(item);
    });
    updateSummary();
}

function addCommunity() {
    state.communities.push({
        name: "",
        group_id: "",
        user_token: "",
        group_token: "",
    });
    renderCommunities();
}

function collectCommunities() {
    const items = Array.from(document.querySelectorAll(".community-item"));
    return items.map((item, idx) => {
        const name = item.querySelector(".input-name")?.value.trim() || "";
        const groupId = Number(item.querySelector(".input-group")?.value);
        const userToken = item.querySelector(".input-user-token")?.value.trim() || "";
        const groupToken = item.querySelector(".input-group-token")?.value.trim() || "";
        const radio = item.querySelector("input[name='activeGroup']");
        if (radio?.checked) {
            state.activeGroupId = groupId;
        }
        return {
            name,
            group_id: groupId,
            user_token: userToken,
            group_token: groupToken,
        };
    });
}

async function saveConfig() {
    try {
        const communities = collectCommunities().filter((c) => c.group_id && (c.user_token || c.group_token));
        if (!communities.length) {
            toast("Добавьте хотя бы одно сообщество и заполните ID/токены", true);
            return;
        }
        const payload = {
            communities,
            active_group_id: communities[0].group_id,
            request_delay: Number(els.requestDelay.value),
            promo_message: els.promoMessage.value,
        };
        const res = await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(await res.text());
        toast("Настройки сохранены");
    } catch (err) {
        toast("Ошибка при сохранении настроек", true);
    }
}

function bindEvents() {
    els.btnSave?.addEventListener("click", (e) => {
        e.preventDefault();
        saveConfig();
    });
    els.btnAddCommunity?.addEventListener("click", (e) => {
        e.preventDefault();
        addCommunity();
    });
}

function init() {
    if (!state.communities.length && window.__CONFIG__) {
        state.communities = [
            {
                name: "",
                group_id: window.__CONFIG__.group_id || "",
                user_token: window.__CONFIG__.user_token || "",
                group_token: window.__CONFIG__.group_token || "",
            },
        ];
    }
    renderCommunities();
    bindEvents();
    updateSummary();
}

document.addEventListener("DOMContentLoaded", init);
