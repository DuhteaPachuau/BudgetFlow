const palette = ["#22c55e", "#ef4444", "#facc15", "#a855f7", "#38bdf8", "#f97316", "#14b8a6"];
const currency = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2
});

function readJsonData(node, name) {
    try {
        return JSON.parse(node.dataset[name] || "[]");
    } catch (error) {
        return [];
    }
}

function registerServiceWorker() {
    if ("serviceWorker" in navigator) {
        navigator.serviceWorker.register("/service-worker.js").catch(() => {});
    }
}

function setupMenu() {
    const button = document.querySelector("[data-toggle-menu]");
    const closeButton = document.querySelector("[data-close-menu]");
    const sidebar = document.querySelector(".sidebar");
    if (button && sidebar) {
        const setMenuState = isOpen => {
            sidebar.classList.toggle("open", isOpen);
            document.body.classList.toggle("menu-open", isOpen);
            button.textContent = "Menu";
            button.setAttribute("aria-expanded", isOpen ? "true" : "false");
        };
        button.setAttribute("aria-expanded", "false");
        button.setAttribute("aria-label", "Toggle navigation menu");
        button.addEventListener("click", () => {
            setMenuState(!sidebar.classList.contains("open"));
        });
        if (closeButton) {
            closeButton.addEventListener("click", () => setMenuState(false));
        }
        sidebar.querySelectorAll("a").forEach(link => {
            link.addEventListener("click", () => {
                setMenuState(false);
            });
        });
    }
}

function setupLogoutConfirm() {
    const modal = document.querySelector("[data-logout-modal]");
    const cancel = document.querySelector("[data-cancel-logout]");
    const confirm = document.querySelector("[data-confirm-logout]");
    if (!modal || !confirm) return;

    document.querySelectorAll("[data-logout-link]").forEach(link => {
        link.addEventListener("click", event => {
            event.preventDefault();
            modal.hidden = false;
        });
    });

    if (cancel) {
        cancel.addEventListener("click", () => {
            modal.hidden = true;
        });
    }

    modal.addEventListener("click", event => {
        if (event.target === modal) {
            modal.hidden = true;
        }
    });

    confirm.addEventListener("click", () => {
        confirm.textContent = "Logging out...";
        confirm.classList.add("loading");
    });
}

function drawDonut() {
    const canvas = document.getElementById("categoryDonut");
    if (!canvas || !window.Chart) return;
    const labels = readJsonData(canvas, "labels");
    const values = readJsonData(canvas, "values");
    new Chart(canvas, {
        type: "doughnut",
        data: {
            labels: labels.length ? labels : ["No expenses"],
            datasets: [{
                data: values.length ? values : [1],
                backgroundColor: values.length ? palette : ["rgba(255,255,255,0.12)"],
                borderColor: "#1a1a2e",
                borderWidth: 4,
                hoverOffset: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "68%",
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { color: "#f7f8ff", boxWidth: 12, padding: 18 }
                },
                tooltip: {
                    callbacks: {
                        label: context => `${context.label}: ${currency.format(context.parsed || 0)}`
                    }
                }
            }
        }
    });
}

function drawTrends() {
    const canvas = document.getElementById("trendsChart");
    if (!canvas || !window.Chart) return;
    const labels = readJsonData(canvas, "labels");
    new Chart(canvas, {
        type: "line",
        data: {
            labels,
            datasets: [
                { label: "Income", data: readJsonData(canvas, "income"), borderColor: "#22c55e", backgroundColor: "rgba(34,197,94,0.08)", tension: 0.35 },
                { label: "Regular Expenses", data: readJsonData(canvas, "expenses"), borderColor: "#ef4444", backgroundColor: "rgba(239,68,68,0.08)", tension: 0.35 },
                { label: "Bills", data: readJsonData(canvas, "bills"), borderColor: "#facc15", backgroundColor: "rgba(250,204,21,0.08)", tension: 0.35 },
                { label: "Savings", data: readJsonData(canvas, "savings"), borderColor: "#a855f7", backgroundColor: "rgba(168,85,247,0.08)", tension: 0.35 }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: { labels: { color: "#f7f8ff" } },
                tooltip: {
                    callbacks: {
                        label: context => `${context.dataset.label}: ${currency.format(context.parsed.y || 0)}`
                    }
                }
            },
            scales: {
                x: { ticks: { color: "#9ca3b8" }, grid: { color: "rgba(255,255,255,0.06)" } },
                y: {
                    ticks: {
                        color: "#9ca3b8",
                        callback: value => currency.format(value)
                    },
                    grid: { color: "rgba(255,255,255,0.06)" }
                }
            }
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    setupMenu();
    setupLogoutConfirm();
    drawDonut();
    drawTrends();
    registerServiceWorker();
});


function exportPDF() {
    const url = `https://budgetflow-631y.onrender.com/reports/monthly/?month={{ selected_month }}&format=pdf`;
    window.open(url, '_system');
}