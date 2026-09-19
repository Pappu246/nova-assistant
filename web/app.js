/* ============ NOVA Dashboard Logic ============ */

// ---------- CLOCK ----------
function updateClock() {
  const now = new Date();
  const h = now.getHours();
  let greet = "Good Evening";
  if (h < 12) greet = "Good Morning";
  else if (h < 17) greet = "Good Afternoon";

  const timeStr = now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
  const dateStr = now.toLocaleDateString("en-US", { weekday: "short", day: "numeric", month: "short", year: "numeric" });

  document.getElementById("greetTime").textContent = greet + ",";
  document.getElementById("wTime").textContent = timeStr;
  document.getElementById("wDate").textContent = dateStr;
}
setInterval(updateClock, 1000);
updateClock();

// ---------- WEATHER ----------
async function loadWeather() {
  try {
    const r = await fetch("/api/weather?city=Jaipur");
    const d = await r.json();
    if (d.temp !== undefined) {
      document.getElementById("wTemp").textContent = Math.round(d.temp) + "\u00B0C";
      document.getElementById("wCity").textContent = d.city + ", India";
      const codes = {
        0: "Clear Sky", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
        45: "Fog", 51: "Light Drizzle", 61: "Rain", 71: "Snow",
        80: "Rain Showers", 95: "Thunderstorm"
      };
      document.getElementById("wCond").textContent = codes[d.code] || "Clear Sky";
    }
  } catch (e) { console.log("weather fail", e); }
}
loadWeather();
setInterval(loadWeather, 600000);

// ---------- SYSTEM STATS ----------
async function loadStatus() {
  try {
    const r = await fetch("/api/status");
    const d = await r.json();

    setRing("Cpu", d.cpu || 0);
    setRing("Ram", d.ram || 0);
    setRing("Disk", d.storage || 0);
    setRing("Net", Math.min(d.network || 0, 100));
  } catch (e) { /* silent */ }
}

function setRing(id, pct) {
  const c = document.getElementById("ring" + id);
  const v = document.getElementById("val" + id);
  if (!c || !v) return;
  const circumference = 2 * Math.PI * 16;  // r=16
  const dash = (pct / 100) * circumference;
  c.setAttribute("stroke-dasharray", dash + " " + (circumference - dash));
  v.textContent = pct + "%";
}

loadStatus();
setInterval(loadStatus, 3000);

// ---------- CHAT ----------
const chatInput = document.getElementById("chatInput");
const sendBtn = document.getElementById("sendBtn");
const convList = document.getElementById("convList");

async function sendMessage(text) {
  if (!text || !text.trim()) return;
  const msg = text.trim();
  chatInput.value = "";

  // Show user message locally
  addConversation("user", msg);

  // Send to server
  showChatLoading();
  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg }),
    });
    const d = await r.json();
    hideChatLoading();
    let reply = d.reply || "...";
    // Filter out raw JSON if brain returned it
    if (reply.trim().startsWith("{") && reply.includes("tool")) {
      try {
        const p = JSON.parse(reply);
        reply = p.reply || "Kaam kar diya Boss.";
      } catch (e) {
        // keep as is
      }
    }
    addConversation("nova", reply);

    // Speak reply
    if (d.reply) {
      fetch("/api/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: d.reply }),
      });
    }
  } catch (e) {
    addConversation("nova", "Error: " + e.message);
  }
}

function addConversation(who, text) {
  // 1) Add to sidebar recent conversations
  const li = document.createElement("li");
  li.className = "conv-item";
  const ico = who === "user" ? "\u{1F464}" : "\u{1F916}";
  li.innerHTML = `<span>${ico}</span> <span>${escapeHtml(text).slice(0, 50)}</span> <span class="conv-time">just now</span>`;
  convList.insertBefore(li, convList.firstChild);
  if (convList.children.length > 8) {
    convList.removeChild(convList.lastChild);
  }

  // 2) Add to chat window
  addChatMessage(who, text);
}

function addChatMessage(who, text) {
  const win = document.getElementById("chatWindow");
  if (!win) return;
  const empty = document.getElementById("chatEmpty");
  if (empty) empty.remove();

  const div = document.createElement("div");
  div.className = "chat-msg " + who;

  const avatar = document.createElement("div");
  avatar.className = "chat-avatar";
  avatar.textContent = who === "user" ? "P" : "N";

  const bubbleWrap = document.createElement("div");
  const bubble = document.createElement("div");
  bubble.className = "chat-bubble";
  bubble.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
  const time = document.createElement("div");
  time.className = "chat-time";
  time.textContent = new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
  bubbleWrap.appendChild(bubble);
  bubbleWrap.appendChild(time);

  div.appendChild(avatar);
  div.appendChild(bubbleWrap);
  win.appendChild(div);
  win.scrollTop = win.scrollHeight;
}

function showChatLoading() {
  const win = document.getElementById("chatWindow");
  if (!win) return;
  const empty = document.getElementById("chatEmpty");
  if (empty) empty.remove();

  const div = document.createElement("div");
  div.className = "chat-msg nova";
  div.id = "chatLoading";
  div.innerHTML = `
    <div class="chat-avatar">N</div>
    <div class="chat-loading"><span></span><span></span><span></span></div>
  `;
  win.appendChild(div);
  win.scrollTop = win.scrollHeight;
}

function hideChatLoading() {
  const el = document.getElementById("chatLoading");
  if (el) el.remove();
}

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;",
    '"': "&quot;", "'": "&#39;"
  }[c]));
}

sendBtn.addEventListener("click", () => sendMessage(chatInput.value));
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendMessage(chatInput.value);
});

// ---------- QUICK ACTIONS ----------
document.querySelectorAll(".quick-action, .card, .prompt-chip").forEach(el => {
  el.addEventListener("click", () => {
    const cmd = el.dataset.cmd;
    if (cmd) {
      chatInput.value = cmd;
      sendMessage(cmd);
    }
  });
});

// ---------- CHIPS (mode) ----------
document.querySelectorAll(".chip").forEach(el => {
  el.addEventListener("click", () => {
    document.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
    el.classList.add("active");
  });
});

// ---------- NAV (complete view switcher) ----------
document.querySelectorAll(".nav-item").forEach(el => {
  el.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
    el.classList.add("active");

    const view = el.dataset.view || "dashboard";

    // Remove all view classes
    document.body.className = document.body.className.replace(/\bview-\S+/g, "").trim();
    document.body.classList.add("view-" + view);

    // Panels
    const panels = {
      dashboard: null,
      chat: showChatView,
      voice: showChatView,
      apps: showAppsView,
      files: showFilesView,
      automation: showAutomationView,
      devices: showDevicesView,
      tasks: showTasksView,
      memory: showMemoryView,
      notes: showNotesView,
      settings: showSettingsView,
    };

    // Hide all custom panels first
    document.querySelectorAll(".custom-panel").forEach(p => p.remove());

    const fn = panels[view];
    if (fn) fn();

    // Scroll chat if that view
    if (view === "chat" || view === "voice") {
      setTimeout(() => {
        const w = document.getElementById("chatWindow");
        if (w) w.scrollTop = w.scrollHeight;
        const inp = document.getElementById("chatInput");
        if (inp) inp.focus();
      }, 100);
    }
  });
});

function _newPanel(title, contentHtml) {
  const main = document.querySelector(".main");
  const div = document.createElement("div");
  div.className = "custom-panel";
  div.innerHTML = `
    <div class="panel-head">
      <h1 class="panel-title">${title}</h1>
    </div>
    <div class="panel-body">${contentHtml}</div>
  `;
  main.appendChild(div);
  return div;
}

function showChatView() {
  // Uses default chat UI (hero hidden via CSS)
}

function showAppsView() {
  _newPanel("Apps & Tools", `
    <div class="panel-grid">
      <div class="panel-card" data-cmd="chrome kholo"><div class="pc-title">Chrome</div><div class="pc-sub">Browser kholo</div></div>
      <div class="panel-card" data-cmd="youtube kholo"><div class="pc-title">YouTube</div><div class="pc-sub">Video dekho</div></div>
      <div class="panel-card" data-cmd="notepad kholo"><div class="pc-title">Notepad</div><div class="pc-sub">Notes likho</div></div>
      <div class="panel-card" data-cmd="calculator kholo"><div class="pc-title">Calculator</div><div class="pc-sub">Hisab karo</div></div>
      <div class="panel-card" data-cmd="file explorer kholo"><div class="pc-title">File Explorer</div><div class="pc-sub">Files dekho</div></div>
      <div class="panel-card" data-cmd="vs code kholo"><div class="pc-title">VS Code</div><div class="pc-sub">Code likho</div></div>
      <div class="panel-card" data-cmd="terminal kholo"><div class="pc-title">Terminal</div><div class="pc-sub">Commands chalao</div></div>
      <div class="panel-card" data-cmd="task manager kholo"><div class="pc-title">Task Manager</div><div class="pc-sub">Process dekho</div></div>
    </div>
  `);
  _bindPanelCards();
}

function showFilesView() {
  _newPanel("Files", `
    <div class="panel-grid">
      <div class="panel-card" data-cmd="downloads kholo"><div class="pc-title">Downloads</div><div class="pc-sub">Downloaded files</div></div>
      <div class="panel-card" data-cmd="documents kholo"><div class="pc-title">Documents</div><div class="pc-sub">Docs folder</div></div>
      <div class="panel-card" data-cmd="pictures kholo"><div class="pc-title">Pictures</div><div class="pc-sub">Photos</div></div>
      <div class="panel-card" data-cmd="desktop kholo"><div class="pc-title">Desktop</div><div class="pc-sub">Desktop folder</div></div>
      <div class="panel-card" data-cmd="videos kholo"><div class="pc-title">Videos</div><div class="pc-sub">Videos folder</div></div>
      <div class="panel-card" data-cmd="music kholo"><div class="pc-title">Music</div><div class="pc-sub">Music folder</div></div>
    </div>
  `);
  _bindPanelCards();
}

function showAutomationView() {
  _newPanel("Automation", `
    <div class="panel-grid">
      <div class="panel-card" data-cmd="volume badhao"><div class="pc-title">Volume Up</div><div class="pc-sub">5 step up</div></div>
      <div class="panel-card" data-cmd="volume kam karo"><div class="pc-title">Volume Down</div><div class="pc-sub">5 step down</div></div>
      <div class="panel-card" data-cmd="mute karo"><div class="pc-title">Mute</div><div class="pc-sub">Sound off</div></div>
      <div class="panel-card" data-cmd="screenshot lo"><div class="pc-title">Screenshot</div><div class="pc-sub">Screen capture</div></div>
      <div class="panel-card" data-cmd="lock karo"><div class="pc-title">Lock PC</div><div class="pc-sub">Lock screen</div></div>
      <div class="panel-card" data-cmd="browser band karo"><div class="pc-title">Close Browser</div><div class="pc-sub">Chromium close</div></div>
    </div>
  `);
  _bindPanelCards();
}

function showDevicesView() {
  _newPanel("Devices", `
    <div class="panel-empty">Abhi koi device connected nahi hai.</div>
  `);
}

function showTasksView() {
  _newPanel("Tasks", `
    <div class="panel-body-inner">
      <button class="panel-action" id="panelAddTask">+ Add Task</button>
      <div id="panelTaskList" class="panel-list"></div>
    </div>
  `);
  const btn = document.getElementById("panelAddTask");
  if (btn) {
    btn.addEventListener("click", async () => {
      const t = prompt("Task?");
      if (!t) return;
      await fetch("/api/tasks", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({title: t}),
      });
      renderPanelTasks();
    });
  }
  renderPanelTasks();
}

async function renderPanelTasks() {
  const list = document.getElementById("panelTaskList");
  if (!list) return;
  try {
    const r = await fetch("/api/tasks");
    const tasks = await r.json();
    list.innerHTML = tasks.length ? "" : "<div class='panel-empty'>Koi task nahi</div>";
    tasks.forEach((t, i) => {
      const d = document.createElement("div");
      d.className = "panel-list-item" + (t.done ? " done" : "");
      d.innerHTML = `<span>${t.done ? "\u2713" : "\u25CB"}</span> <span>${t.title}</span>`;
      d.addEventListener("click", async () => {
        await fetch(`/api/tasks/${i}/toggle`, {method: "POST"});
        renderPanelTasks();
      });
      list.appendChild(d);
    });
  } catch (e) {}
}

async function showMemoryView() {
  _newPanel("Memory", `<div class="panel-empty">Loading...</div>`);
  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({message: "recall sab batao"}),
    });
    const d = await r.json();
    const panel = document.querySelector(".custom-panel");
    if (panel) panel.querySelector(".panel-body").innerHTML =
      `<div class="panel-memory">${escapeHtml(d.reply || "Kuch yaad nahi")}</div>`;
  } catch (e) {}
}

function showNotesView() {
  _newPanel("Notes", `
    <div class="panel-body-inner">
      <button class="panel-action" id="panelAddNote">+ Add Note</button>
      <div id="panelNoteList" class="panel-list"></div>
    </div>
  `);
  const btn = document.getElementById("panelAddNote");
  if (btn) {
    btn.addEventListener("click", async () => {
      const t = prompt("Note?");
      if (!t) return;
      await fetch("/api/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message: "note karo " + t}),
      });
      showNotesView();
    });
  }
  (async () => {
    try {
      const r = await fetch("/api/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message: "mere notes dikhao"}),
      });
      const d = await r.json();
      const list = document.getElementById("panelNoteList");
      if (list) list.innerHTML = `<div class="panel-memory">${escapeHtml(d.reply || "Koi note nahi")}</div>`;
    } catch (e) {}
  })();
}

function showSettingsView() {
  _newPanel("Settings", `
    <div class="panel-body-inner">
      <div class="panel-setting">
        <label>Voice</label>
        <div class="panel-value">Madhur (Hindi male)</div>
      </div>
      <div class="panel-setting">
        <label>Wake Word</label>
        <div class="panel-value">"Hey Jarvis"</div>
      </div>
      <div class="panel-setting">
        <label>Brain</label>
        <div class="panel-value">Groq gpt-oss-120b</div>
      </div>
      <div class="panel-setting">
        <label>Whisper</label>
        <div class="panel-value">base model</div>
      </div>
    </div>
  `);
}

function _bindPanelCards() {
  document.querySelectorAll(".panel-card").forEach(el => {
    el.addEventListener("click", () => {
      const cmd = el.dataset.cmd;
      if (cmd) {
        // Switch to chat, then send
        document.querySelectorAll(".nav-item").forEach(n => {
          if (n.dataset.view === "chat") n.classList.add("active");
          else n.classList.remove("active");
        });
        document.querySelectorAll(".custom-panel").forEach(p => p.remove());
        document.body.className = document.body.className.replace(/\bview-\S+/g, "").trim();
        document.body.classList.add("view-chat");
        setTimeout(() => {
          const inp = document.getElementById("chatInput");
          if (inp) inp.value = cmd;
          sendMessage(cmd);
        }, 200);
      }
    });
  });
}

// ---------- MIC BUTTON ----------
document.getElementById("micBtn").addEventListener("click", () => {
  fetch("/api/voice/start", { method: "POST" })
    .then(() => {
      document.getElementById("statusText").textContent = "Voice mode started (check terminal)";
      setTimeout(() => {
        document.getElementById("statusText").textContent = "Ready";
      }, 3000);
    })
    .catch(e => console.log(e));
});

// ---------- SEARCH ----------
document.getElementById("searchInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const q = e.target.value.trim();
    if (q) sendMessage("browser me google pe " + q + " search karo");
    e.target.value = "";
  }
});

// Ctrl+K focus
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "k") {
    e.preventDefault();
    document.getElementById("searchInput").focus();
  }
});

// ---------- TASKS ----------
const taskList = document.getElementById("taskList");
document.getElementById("addTaskBtn").addEventListener("click", async () => {
  const t = prompt("Task kya hai?");
  if (!t) return;
  try {
    await fetch("/api/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: t }),
    });
    loadTasks();
  } catch (e) { console.log(e); }
});

async function loadTasks() {
  try {
    const r = await fetch("/api/tasks");
    const tasks = await r.json();
    taskList.innerHTML = "";
    tasks.forEach((t, i) => {
      const li = document.createElement("li");
      li.className = "task-item" + (t.done ? " done" : "");
      li.innerHTML = `<span class="task-check" data-i="${i}">${t.done ? "\u2713" : ""}</span> <span>${escapeHtml(t.title)}</span>`;
      taskList.appendChild(li);
    });
    document.getElementById("taskCount").textContent =
      tasks.filter(t => t.done).length + "/" + tasks.length;
    document.querySelectorAll(".task-check").forEach(c => {
      c.addEventListener("click", async (e) => {
        const i = parseInt(e.target.dataset.i);
        await fetch(`/api/tasks/${i}/toggle`, { method: "POST" });
        loadTasks();
      });
    });
  } catch (e) { /* silent */ }
}
loadTasks();

// ---------- WEBSOCKET LIVE STATUS ----------
function connectWS() {
  try {
    const ws = new WebSocket("ws://" + location.host + "/ws");
    ws.onmessage = (evt) => {
      const d = JSON.parse(evt.data);
      if (d.status) document.getElementById("statusText").textContent = d.status;
      if (d.cpu !== undefined) setRing("Cpu", d.cpu);
      if (d.ram !== undefined) setRing("Ram", d.ram);
      if (d.storage !== undefined) setRing("Disk", d.storage);
      if (d.voice_active !== undefined) setOrbActive(d.voice_active);
      if (d.wake_detected) flashOrb();
    };
    ws.onclose = () => setTimeout(connectWS, 5000);
    ws.onerror = () => ws.close();
  } catch (e) { /* silent */ }
}
connectWS();

console.log("NOVA dashboard loaded");


// ---------- ORB ACTIVE STATE ----------
const orb = document.getElementById("novaOrb");
let orbActiveTimer = null;

function setOrbActive(active) {
  if (!orb) return;
  if (active) {
    orb.classList.add("active");
    document.body.classList.add("voice-active");
  } else {
    orb.classList.remove("active");
    document.body.classList.remove("voice-active");
  }
}

// Wake word detected - flash orb
function flashOrb() {
  if (!orb) return;
  orb.classList.add("active");
  document.body.classList.add("voice-active");
  clearTimeout(orbActiveTimer);
  orbActiveTimer = setTimeout(() => {
    orb.classList.remove("active");
    document.body.classList.remove("voice-active");
  }, 2000);
}

// Click orb -> activate voice (handled in inline script, but also here for safety)
if (orb) {
  orb.addEventListener("click", () => {
    setOrbActive(true);
    fetch("/api/voice/activate", { method: "POST" })
      .finally(() => {
        setTimeout(() => setOrbActive(false), 1500);
      });
  });
}

