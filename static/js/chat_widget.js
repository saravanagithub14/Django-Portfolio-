/**
 * V.E.R.A. chat widget: talks to POST /chatbot/api/chat/ ({message} -> {response, sources}). It asks for
 * NDJSON, so the server streams which agent is working before the answer, and the loader shows it.
 * Look, states and fixed lines follow the V.E.R.A. brand kit. Replies are plain text and are
 * HTML-escaped before display; the server keeps the conversation history in the Django session.
 */
(function () {
    const API_URL = "/chatbot/api/chat/";
    const container = document.getElementById("chat-widget-container");
    if (!container) return;

    // Name and greeting come from the enabled Chatbot row (Django admin), via data attributes
    const BOT_NAME = container.dataset.botName || "V.E.R.A.";
    const GREETING = container.dataset.welcome ||
        "Hello. I'm V.E.R.A., Saravana's assistant. I've read everything he's worked on, so ask away.";
    const LINES = {
        returning: "Welcome back. Where were we?",
        thinking: "Checking the records.",
        error: "Something broke on my side. Give me a moment and ask again.",
    };
    // The agents behind V.E.R.A. (chatbot/agents/), shown in the loader as they're picked and start work
    const AGENTS = [
        { id: "guard", name: "Guard" },
        { id: "privacy", name: "Privacy" },
        { id: "portfolio", name: "Portfolio" },
        { id: "tutor", name: "Tutor" },
    ];
    const STEP_LINES = {
        "router:routing": "Routing your question",
        "guard:checking": "Guard is checking for tricks",
        "privacy:checking": "Privacy is reviewing the question",
        "portfolio:searching": LINES.thinking.replace(/\.$/, ""),
        "portfolio:writing": "Writing from the records",
        "tutor:searching": "Tutor is preparing a lesson",
        "tutor:writing": "Tutor is writing the lesson",
    };
    // Fixed-line agents answer instantly; keep the picked agent on screen long enough to read
    const MIN_STEP_MS = 650;
    const SUGGESTIONS = ["What does he do right now?", "His best projects", "Can he run a workshop?", "Biology to AI, how?"];
    const VISITED_KEY = "vera.visited";

    const escapeHtml = (s) => String(s).replace(/[&<>"']/g, (c) => (
        { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    // "V.E.R.A." -> V<i>.</i>E<i>.</i>... so the dots render in lime
    const wordmark = (name) => escapeHtml(name).replace(/\./g, "<i>.</i>");
    // The Node V mark from the brand kit: two source nodes meeting at one lit answer node
    const mark = (size) => `<svg class="vera-mark" width="${size}" height="${size}" viewBox="0 0 64 64" aria-hidden="true">
        <rect width="64" height="64" rx="15" fill="#111418"/>
        <path d="M17 18 L32 45 L47 18" fill="none" stroke="#B5E655" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
        <circle class="halo" cx="32" cy="45" r="11" fill="#B5E655" fill-opacity=".22"/>
        <circle class="n1" cx="17" cy="18" r="5" fill="#EEF2F6"/>
        <circle class="n2" cx="47" cy="18" r="5" fill="#EEF2F6"/>
        <circle class="core" cx="32" cy="45" r="6.5" fill="#B5E655"/></svg>`;

    let returning = false;
    try { returning = localStorage.getItem(VISITED_KEY) === "1"; } catch (e) {}

    container.innerHTML = `
        <button id="chat-fab" type="button" aria-label="Ask ${escapeHtml(BOT_NAME)}" aria-expanded="false" aria-controls="chat-window">
            ${mark(34)}<span class="fab-label">Ask <span class="vera-wordmark">${wordmark(BOT_NAME)}</span></span>
        </button>
        <div id="chat-window" role="dialog" aria-label="${escapeHtml(BOT_NAME)} chat">
            <div class="chat-header">
                <span class="chat-header-mark">${mark(38)}</span>
                <div class="chat-header-text">
                    <span class="vera-wordmark">${wordmark(BOT_NAME)}</span>
                    <small>Answers from Saravana's own records</small>
                </div>
                <button class="close-chat" type="button" aria-label="Close chat">&times;</button>
            </div>
            <div id="chat-messages" aria-live="polite"></div>
            <div class="vera-chips"></div>
            <form class="chat-input-area">
                <input type="text" id="chat-input" placeholder="Ask about Saravana's work" autocomplete="off" maxlength="500" aria-label="Your question">
                <button id="chat-send" type="submit">Send</button>
            </form>
        </div>`;

    const fab = document.getElementById("chat-fab");
    const chatWindow = document.getElementById("chat-window");
    const headerMark = container.querySelector(".chat-header-mark");
    const closeBtn = container.querySelector(".close-chat");
    const form = container.querySelector(".chat-input-area");
    const input = document.getElementById("chat-input");
    const sendBtn = document.getElementById("chat-send");
    const messages = document.getElementById("chat-messages");
    const chips = container.querySelector(".vera-chips");
    let busy = false;

    // Avatar states: idle, listening (visitor is typing), thinking (waiting for an answer)
    function setState(state) {
        headerMark.classList.toggle("vera-listening", state === "listening");
        headerMark.classList.toggle("vera-thinking", state === "thinking");
    }

    function addMessage(role, text, extraClass) {
        const msg = document.createElement("div");
        msg.className = `message ${role}-message${extraClass ? " " + extraClass : ""}`;
        msg.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
        messages.appendChild(msg);
        messages.scrollTop = messages.scrollHeight;
        return msg;
    }

    // "See experience" link plus chips naming the records the answer came from
    function addSources(msg, sources) {
        if (!Array.isArray(sources) || !sources.length) return;
        const first = sources[0];
        // Pages answer at both /experience/ and /experience.html; no link to the page you're on
        const page = (path) => path.replace(/\/$/, "").replace(/\.html$/, "");
        const here = page(window.location.pathname) === page(first.url);
        if (first.url && !here) {
            const link = document.createElement("a");
            link.className = "vera-link";
            link.href = first.url;
            link.textContent = `See ${first.section.toLowerCase()}`;
            msg.appendChild(document.createElement("br"));
            msg.appendChild(link);
        }
        const labels = [];
        sources.forEach((s) => {
            [s.section, s.item].forEach((label) => { if (label && !labels.includes(label)) labels.push(label); });
        });
        const row = document.createElement("div");
        row.className = "vera-sources";
        row.innerHTML = labels.slice(0, 4).map((l) => `<span>${escapeHtml(l)}</span>`).join("");
        msg.appendChild(row);
        messages.scrollTop = messages.scrollHeight;
    }

    // Loader: a status line plus the agent row. While routing the highlight sweeps the row; once an agent
    // is picked it stays lit.
    function addLoader() {
        const msg = document.createElement("div");
        msg.className = "message bot-message thinking vera-loader";
        msg.innerHTML = `<div class="vera-step"><span class="vera-step-text"></span><span class="vera-dots"><i></i><i></i><i></i></span></div>
            <div class="vera-agents">${AGENTS.map((a) => `<span data-agent="${a.id}">${a.name}</span>`).join("")}</div>`;
        messages.appendChild(msg);
        messages.scrollTop = messages.scrollHeight;
        const text = msg.querySelector(".vera-step-text");
        const row = msg.querySelector(".vera-agents");
        let shownAt = 0;
        const loader = {
            el: msg,
            step(agent, stage) {
                text.textContent = STEP_LINES[`${agent}:${stage}`] || LINES.thinking.replace(/\.$/, "");
                const routing = agent === "router";
                row.classList.toggle("routing", routing);
                row.querySelectorAll("span").forEach((s) => s.classList.toggle("active", s.dataset.agent === agent));
                msg.setAttribute("aria-label", text.textContent);
                if (!routing) shownAt = Date.now();
            },
            // Resolves once the picked agent has been visible for MIN_STEP_MS
            settle: () => new Promise((resolve) => setTimeout(resolve, shownAt ? Math.max(0, MIN_STEP_MS - (Date.now() - shownAt)) : 0)),
        };
        loader.step("router", "routing");
        return loader;
    }

    // Reads the NDJSON stream ({"type": "step"} lines, then one {"type": "answer"}); plain JSON otherwise
    async function readAnswer(response, onStep) {
        const type = response.headers.get("Content-Type") || "";
        if (!type.includes("ndjson") || !response.body) return response.json().catch(() => null);
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "", answer = null;
        const handle = (line) => {
            if (!line.trim()) return;
            let event;
            try { event = JSON.parse(line); } catch (e) { return; }
            if (event.type === "step") onStep(event.agent, event.stage);
            else if (event.type === "answer") answer = event;
        };
        for (;;) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop();
            lines.forEach(handle);
        }
        handle(buffer + decoder.decode());
        return answer;
    }

    function renderChips() {
        chips.innerHTML = SUGGESTIONS.map((s) => `<button type="button">${escapeHtml(s)}</button>`).join("");
    }

    async function ask(text) {
        if (busy || !text) return;
        busy = true;
        sendBtn.disabled = true;
        addMessage("user", text);
        const loader = addLoader();
        setState("thinking");

        let data = null;
        try {
            const response = await fetch(API_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json", "Accept": "application/x-ndjson, application/json" },
                body: JSON.stringify({ message: text }),
            });
            data = await readAnswer(response, (agent, stage) => loader.step(agent, stage));
        } catch (e) {
            console.error("V.E.R.A. connection error:", e);
        }
        await loader.settle();
        loader.el.remove();

        if (data && data.response) {
            addSources(addMessage("bot", data.response), data.sources);
        } else if (data && data.error) {
            addMessage("bot", data.error);
        } else {
            addMessage("bot", LINES.error);
        }
        busy = false;
        sendBtn.disabled = false;
        setState(document.activeElement === input && input.value ? "listening" : "idle");
    }

    function open(isOpen) {
        chatWindow.classList.toggle("active", isOpen);
        fab.setAttribute("aria-expanded", String(isOpen));
        if (isOpen) {
            input.focus();
            try { localStorage.setItem(VISITED_KEY, "1"); } catch (e) {}
        }
    }

    addMessage("bot", returning ? LINES.returning : GREETING);
    renderChips();

    fab.addEventListener("click", () => open(!chatWindow.classList.contains("active")));
    closeBtn.addEventListener("click", () => open(false));
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && chatWindow.classList.contains("active")) open(false);
    });
    form.addEventListener("submit", (e) => {
        e.preventDefault();
        const text = input.value.trim();
        input.value = "";
        ask(text);
    });
    chips.addEventListener("click", (e) => {
        const chip = e.target.closest("button");
        if (!chip) return;
        chip.remove();  // each suggestion is offered once
        ask(chip.textContent);
    });
    input.addEventListener("input", () => { if (!busy) setState(input.value ? "listening" : "idle"); });
    input.addEventListener("blur", () => { if (!busy) setState("idle"); });

    // Space Grotesk for the wordmark only; loaded lazily so it never blocks the page
    const font = document.createElement("link");
    font.rel = "stylesheet";
    font.href = "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@700&display=swap";
    document.head.appendChild(font);
})();
