const form = document.getElementById("shortenForm");
const urlInput = document.getElementById("urlInput");
const result = document.getElementById("result");
const shortUrlLink = document.getElementById("shortUrlLink");
const errorBox = document.getElementById("errorBox");
const copyBtn = document.getElementById("copyBtn");
const urlTableBody = document.getElementById("urlTableBody");
const shortenBtn = document.getElementById("shortenBtn");
const btnText = document.getElementById("btnText");
const btnSpinner = document.getElementById("btnSpinner");
const themeToggle = document.getElementById("themeToggle");
const toast = document.getElementById("toast");

// ---------------------------
// Theme toggle (dark/light)
// ---------------------------
function applyTheme(theme) {
    if (theme === "light") {
        document.body.classList.add("light-mode");
        themeToggle.textContent = "☀️";
    } else {
        document.body.classList.remove("light-mode");
        themeToggle.textContent = "🌙";
    }
}

const savedTheme = localStorage.getItem("theme") || "dark";
applyTheme(savedTheme);

themeToggle.addEventListener("click", () => {
    const isLight = document.body.classList.contains("light-mode");
    const newTheme = isLight ? "dark" : "light";
    applyTheme(newTheme);
    localStorage.setItem("theme", newTheme);
});

// ---------------------------
// Toast helper
// ---------------------------
function showToast(message) {
    toast.textContent = message;
    toast.classList.remove("hidden");
    requestAnimationFrame(() => toast.classList.add("show"));
    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.classList.add("hidden"), 300);
    }, 2000);
}

// ---------------------------
// Loading spinner helpers
// ---------------------------
function setLoading(isLoading) {
    shortenBtn.disabled = isLoading;
    if (isLoading) {
        btnText.classList.add("hidden");
        btnSpinner.classList.remove("hidden");
    } else {
        btnText.classList.remove("hidden");
        btnSpinner.classList.add("hidden");
    }
}

// ---------------------------
// Shorten form submit
// ---------------------------
form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorBox.classList.add("hidden");
    result.classList.add("hidden");

    const url = urlInput.value.trim();
    if (!url) return;

    setLoading(true);

    try {
        const res = await fetch("/api/shorten", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url })
        });

        const data = await res.json();

        if (!res.ok) {
            errorBox.textContent = data.error || "Something went wrong.";
            errorBox.classList.remove("hidden");
            setLoading(false);
            return;
        }

        shortUrlLink.textContent = data.short_url;
        shortUrlLink.href = data.short_url;
        result.classList.remove("hidden");
        urlInput.value = "";
        loadUrls();
        showToast("Short URL created!");
    } catch (err) {
        errorBox.textContent = "Failed to connect to server.";
        errorBox.classList.remove("hidden");
    } finally {
        setLoading(false);
    }
});

// ---------------------------
// Copy button
// ---------------------------
copyBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(shortUrlLink.href);
    copyBtn.textContent = "✓ Copied";
    copyBtn.classList.add("copied");
    showToast("Copied to clipboard!");
    setTimeout(() => {
        copyBtn.textContent = "Copy";
        copyBtn.classList.remove("copied");
    }, 1500);
});

// ---------------------------
// Load recent URLs
// ---------------------------
async function loadUrls() {
    try {
        const res = await fetch("/api/urls");
        const urls = await res.json();

        urlTableBody.innerHTML = "";
        urls.forEach((item) => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>🔗 <a href="/${item.short_code}" target="_blank">/${item.short_code}</a></td>
                <td>${item.original_url}</td>
                <td>🕒 ${item.created_at}</td>
            `;
            urlTableBody.appendChild(row);
        });
    } catch (err) {
        console.error("Failed to load URLs", err);
    }
}

loadUrls();
