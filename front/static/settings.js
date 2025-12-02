const els = {
    toast: document.getElementById("toast"),
    btnSave: document.getElementById("btn-save-config"),
    configForm: document.getElementById("config-form"),
};

function toast(message, isError = false) {
    if (!els.toast) return;
    els.toast.textContent = message;
    els.toast.classList.toggle("error", isError);
    els.toast.classList.add("show");
    setTimeout(() => els.toast.classList.remove("show"), 2400);
}

function serializeConfigForm() {
    const formData = new FormData(els.configForm);
    return {
        user_token: formData.get("user_token")?.toString().trim() || "",
        group_token: formData.get("group_token")?.toString().trim() || "",
        group_id: Number(formData.get("group_id")),
        request_delay: Number(formData.get("request_delay")),
        promo_message: formData.get("promo_message")?.toString() || "",
    };
}

async function saveConfig() {
    try {
        const payload = serializeConfigForm();
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
}

document.addEventListener("DOMContentLoaded", bindEvents);
