// ============================================================================
// static/script.js  —  Parho (پڑھو)  —  all the browser-side logic
// ============================================================================
// This file does five jobs:
//   1) VIEW ROUTING  — show one of #view-landing / #view-auth / #view-app.
//   2) AUTH          — sign up / log in against the FastAPI backend, and keep
//                      the login token in localStorage so a refresh stays in.
//   3) PDF + CHAT    — upload a PDF and chat about it (matches the API exactly).
//   4) HERO          — a Three.js particle field that drifts outward (space
//                      /explosion feel) behind the glowing Urdu logo.
//   5) POLISH        — scroll reveals, the frosted nav, and the motion bands.
//
// The API endpoints and field names below MUST match the backend:
//   POST /auth/signup {name,email,password} -> {access_token, name}
//   POST /auth/login  {email,password}      -> {access_token, name}
//   GET  /pdf/quota                         -> {remaining, max_per_day}
//   POST /pdf/upload  (multipart field "file") -> {message, remaining_today}
//   POST /chat        {question, history:[{role,content}]} -> {answer, sources}
// ============================================================================

// ┌──────────────────────────────────────────────────────────────────────────┐
// │  EDIT ME AFTER YOU DEPLOY  —  where is the backend (API) server?           │
// └──────────────────────────────────────────────────────────────────────────┘
// When the frontend and backend run together (locally with `uvicorn`), leave
// this as "" — the browser then calls the SAME server that served the page.
//
// When you host the FRONTEND on Vercel and the BACKEND on Railway, they live on
// different addresses, so the frontend must be told the backend's URL. Paste
// your Railway URL here (NO trailing slash), for example:
//   const API = "https://parho-production.up.railway.app";
//
// Tip: keep "" while testing locally; set the Railway URL right before (or just
// after) you deploy the frontend to Vercel.
const API = "";

// Does the user prefer reduced motion? We check this once and dial animations
// down everywhere (hero drift, typewriter) so we never cause discomfort.
const REDUCED_MOTION =
  window.matchMedia &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// ---- Login state (restored from localStorage so refresh keeps you signed in).
let token = localStorage.getItem("parho_token") || null;
let userName = localStorage.getItem("parho_name") || "";

// The running conversation. Each item is {role:"user"|"assistant", content}.
// We send this to /chat so the backend can understand follow-up questions.
let chatHistory = [];

// Tiny helper so we type less. $("#id") returns that element.
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// Build the "Authorization: Bearer <token>" header every protected call needs.
function authHeader() {
  return { Authorization: "Bearer " + token };
}


// ============================================================================
// 1) VIEW ROUTING
// ============================================================================
// Only one <div class="view"> is visible at a time. showView hides all three,
// then shows the one asked for.
function showView(name) {
  ["landing", "auth", "app"].forEach((v) => {
    $("#view-" + v).classList.toggle("hidden", v !== name);
  });
  // Scroll landing/auth back to the top when we switch to them.
  if (name !== "app") window.scrollTo(0, 0);
}

// Any element with data-goto="auth|landing|app" becomes a navigation button.
// If it also has data-mode="login|signup" we pre-select that auth tab.
function wireNavButtons() {
  $$("[data-goto]").forEach((el) => {
    el.addEventListener("click", () => {
      const target = el.getAttribute("data-goto");
      const mode = el.getAttribute("data-mode");
      if (target === "auth" && mode) setAuthMode(mode);
      showView(target);
    });
  });
}

// Frost the nav bar once the user scrolls a little way down the hero.
function wireNavScroll() {
  const nav = $("#nav");
  if (!nav) return;
  const onScroll = () => nav.classList.toggle("scrolled", window.scrollY > 40);
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });
}

// ============================================================================
// 2) AUTH  (sign up / log in)
// ============================================================================

// Switch the auth card between "login" and "signup": show the right form,
// mark the active tab, and slide the glowing pill under it.
function setAuthMode(mode) {
  const isLogin = mode === "login";
  $("#login-form").classList.toggle("hidden", !isLogin);
  $("#signup-form").classList.toggle("hidden", isLogin);
  $("#tab-login").classList.toggle("active", isLogin);
  $("#tab-signup").classList.toggle("active", !isLogin);
  // The pill slides right for signup, left for login.
  $(".auth-tab-glider").classList.toggle("right", !isLogin);
  $("#auth-message").textContent = "";
}

function wireAuth() {
  // Tab buttons.
  $("#tab-login").addEventListener("click", () => setAuthMode("login"));
  $("#tab-signup").addEventListener("click", () => setAuthMode("signup"));

  // Sign-up form submit.
  $("#signup-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    await authRequest("/auth/signup", {
      name: $("#signup-name").value,
      email: $("#signup-email").value,
      password: $("#signup-password").value,
    });
  });

  // Login form submit.
  $("#login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    await authRequest("/auth/login", {
      email: $("#login-email").value,
      password: $("#login-password").value,
    });
  });
}

// Shared network code for both signup and login. On success we save the token
// and drop the user straight into the chat app.
async function authRequest(path, body) {
  const msg = $("#auth-message");
  msg.className = "auth-message";      // reset any error/ok styling
  msg.textContent = "Please wait…";
  try {
    const res = await fetch(API + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) {
      // The backend puts a friendly reason in "detail".
      msg.textContent = data.detail || "Something went wrong.";
      return;
    }
    // Success: remember who we are and enter the app.
    token = data.access_token;
    userName = data.name;
    localStorage.setItem("parho_token", token);
    localStorage.setItem("parho_name", userName);
    chatHistory = [];
    enterApp();
  } catch (err) {
    msg.textContent = "Cannot reach the server. Is it running?";
  }
}

// Log out: forget everything and return to the landing page.
function logout() {
  token = null;
  userName = "";
  chatHistory = [];
  localStorage.removeItem("parho_token");
  localStorage.removeItem("parho_name");
  // Clear the chat area back to its empty state on next entry.
  const win = $("#chat-window");
  win.innerHTML = "";
  showView("landing");
}

// Enter the chat app: greet the user, show remaining quota, reveal the view.
function enterApp() {
  $("#welcome").textContent = "Hi, " + userName;
  showView("app");
  refreshQuota();
  $("#question-input").focus();
}

// Ask the backend how many uploads remain today and show it as a pill.
async function refreshQuota() {
  try {
    const res = await fetch(API + "/pdf/quota", { headers: authHeader() });
    if (!res.ok) return;
    const data = await res.json();
    $("#quota").textContent = `${data.remaining}/${data.max_per_day} uploads left`;
  } catch (_) {
    /* quota is non-critical; ignore errors */
  }
}

// ============================================================================
// 3) PDF UPLOAD  (the "+" button on the left, plus drag-and-drop)
// ============================================================================
function wireUpload() {
  const btn = $("#upload-btn");
  const input = $("#pdf-input");

  // Clicking the round "+" opens the hidden native file picker.
  btn.addEventListener("click", () => input.click());
  // When a file is chosen, upload it.
  input.addEventListener("change", () => {
    if (input.files.length) uploadPdf(input.files[0]);
    input.value = ""; // reset so the same file can be picked again later
  });

  // --- Drag and drop anywhere on the app screen ---
  const overlay = $("#drop-overlay");
  const appView = $("#view-app");
  // A counter avoids flicker: dragenter/dragleave fire for child elements too.
  let dragDepth = 0;

  appView.addEventListener("dragenter", (e) => {
    e.preventDefault();
    dragDepth++;
    overlay.classList.remove("hidden");
  });
  appView.addEventListener("dragover", (e) => e.preventDefault());
  appView.addEventListener("dragleave", (e) => {
    e.preventDefault();
    dragDepth = Math.max(0, dragDepth - 1);
    if (dragDepth === 0) overlay.classList.add("hidden");
  });
  appView.addEventListener("drop", (e) => {
    e.preventDefault();
    dragDepth = 0;
    overlay.classList.add("hidden");
    const file = e.dataTransfer.files[0];
    if (file) uploadPdf(file);
  });
}

// Send one PDF to the backend and show a small status toast.
async function uploadPdf(file) {
  const toast = $("#upload-toast");

  // Friendly client-side check before spending a network round-trip.
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    return showToast("Please choose a PDF file.", "err");
  }

  showToast(`Uploading “${file.name}” — this can take a few seconds…`, "");

  // FormData sends the file. The field name "file" MUST match pdf_routes.py
  // (upload_pdf(file: UploadFile = File(...))).
  const form = new FormData();
  form.append("file", file);

  try {
    const res = await fetch(API + "/pdf/upload", {
      method: "POST",
      headers: authHeader(), // NOTE: never set Content-Type for FormData; the
                             // browser adds the correct multipart boundary itself.
      body: form,
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.detail || "Upload failed.", "err");
    } else {
      showToast(data.message || "PDF processed. Ask away!", "ok");
    }
    refreshQuota(); // uploads-left number changed
  } catch (err) {
    showToast("Cannot reach the server.", "err");
  }
}

// Show a message above the composer; auto-hide the happy ones after a while.
let toastTimer = null;
function showToast(text, kind) {
  const toast = $("#upload-toast");
  toast.textContent = text;
  toast.className = "upload-toast" + (kind ? " " + kind : "");
  toast.classList.remove("hidden");
  clearTimeout(toastTimer);
  if (kind === "ok") {
    toastTimer = setTimeout(() => toast.classList.add("hidden"), 6000);
  }
}


// ============================================================================
// 4) CHAT
// ============================================================================
function wireChat() {
  const form = $("#chat-form");
  const inputEl = $("#question-input");

  // Auto-grow the textarea as the user types (up to the CSS max-height).
  inputEl.addEventListener("input", () => {
    inputEl.style.height = "auto";
    inputEl.style.height = Math.min(inputEl.scrollHeight, 160) + "px";
  });

  // Enter = send, Shift+Enter = newline (just like ChatGPT).
  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    sendQuestion();
  });

  $("#logout-btn").addEventListener("click", logout);
}

// Send the typed question to /chat, showing a typing indicator while we wait,
// then a typewriter reveal of the answer.
async function sendQuestion() {
  const inputEl = $("#question-input");
  const question = inputEl.value.trim();
  if (!question) return;

  // Reset the textarea height and show the user's message immediately.
  inputEl.value = "";
  inputEl.style.height = "auto";
  addBubble("user", question);

  // Show the animated "…" typing bubble while the backend thinks.
  const typingEl = addTyping();
  const send = $("#send-btn");
  send.disabled = true;

  try {
    const res = await fetch(API + "/chat", {
      method: "POST",
      headers: { ...authHeader(), "Content-Type": "application/json" },
      // Send the question AND the running history so follow-ups make sense.
      body: JSON.stringify({ question, history: chatHistory }),
    });
    const data = await res.json();
    typingEl.remove(); // stop the typing dots

    if (!res.ok) {
      addBubble("ai", data.detail || "Something went wrong.");
      return;
    }

    // Reveal the answer with a typewriter effect, then show its sources.
    await addBubble("ai", data.answer, data.sources, /*typewriter=*/true);

    // Remember both turns so the next question has context.
    chatHistory.push({ role: "user", content: question });
    chatHistory.push({ role: "assistant", content: data.answer });
  } catch (err) {
    typingEl.remove();
    addBubble("ai", "Cannot reach the server.");
  } finally {
    send.disabled = false;
  }
}

// Remove the empty-state greeting the first time a message appears.
function clearEmptyState() {
  const empty = $("#chat-empty");
  if (empty) empty.remove();
}

// Add a message bubble. role is "user" or "ai". If typewriter is true we reveal
// the text character-by-character (skipped when the user prefers reduced motion).
function addBubble(role, text, sources, typewriter) {
  clearEmptyState();
  const win = $("#chat-window");

  const row = document.createElement("div");
  row.className = "msg " + (role === "user" ? "user" : "ai");

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  row.appendChild(bubble);
  win.appendChild(row);

  // Helper to keep the newest message in view as it grows.
  const stick = () => { win.scrollTop = win.scrollHeight; };

  // Build the sources footer (shown after the text finishes).
  const addSources = () => {
    if (sources && sources.length) {
      const src = document.createElement("div");
      src.className = "sources";
      src.innerHTML = "<b>Sources</b><br>" +
        sources.map((s) => escapeHtml(s)).join("<br>");
      bubble.appendChild(src);
      stick();
    }
  };

  if (typewriter && !REDUCED_MOTION) {
    // Return a promise that resolves once the whole answer is typed out.
    return new Promise((resolve) => {
      let i = 0;
      const speed = 12; // ms per character — fast but visible
      (function typeNext() {
        bubble.textContent = text.slice(0, i);
        stick();
        if (i < text.length) {
          i += Math.max(1, Math.round(text.length / 400)); // step for long text
          setTimeout(typeNext, speed);
        } else {
          bubble.textContent = text;
          addSources();
          resolve();
        }
      })();
    });
  }

  // No typewriter: set the text at once.
  bubble.textContent = text;
  addSources();
  stick();
  return Promise.resolve();
}

// The animated three-dot "AI is typing" bubble. Returns the row so we can remove it.
function addTyping() {
  clearEmptyState();
  const win = $("#chat-window");
  const row = document.createElement("div");
  row.className = "msg ai";
  row.innerHTML = '<div class="bubble"><span class="typing"><span></span><span></span><span></span></span></div>';
  win.appendChild(row);
  win.scrollTop = win.scrollHeight;
  return row;
}

// Escape text before we ever put it inside innerHTML (safety against odd
// characters in PDF source snippets breaking the markup).
function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

// ============================================================================
// 5) POLISH  (scroll reveals + the motion.dev-style color bands)
// ============================================================================

// Fade + rise each .reveal element in as it scrolls into view.
function wireReveals() {
  const els = $$(".reveal");
  if (!("IntersectionObserver" in window)) {
    // Very old browser: just show everything.
    els.forEach((el) => el.classList.add("in"));
    return;
  }
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("in");
          io.unobserve(entry.target); // reveal once, then stop watching
        }
      });
    },
    { threshold: 0.16 }
  );
  els.forEach((el) => io.observe(el));
}

// Fill each .band with a row of fast-moving rectangles built from its two
// colors (data-c1 / data-c2), then sweep them in when the band scrolls into
// view. This is the "pixels / bars / fast rectangles" transition feel.
function wireBands() {
  const bands = $$(".band");

  bands.forEach((band) => {
    const c1 = band.getAttribute("data-c1") || "#7c8cff";
    const c2 = band.getAttribute("data-c2") || "#7fe3dd";
    const COUNT = 22; // number of vertical bars across the strip

    for (let i = 0; i < COUNT; i++) {
      const bar = document.createElement("span");
      bar.className = "band-bar";
      const t = i / (COUNT - 1);                 // 0 → 1 across the strip
      bar.style.left = (t * 100).toFixed(2) + "%";
      bar.style.width = 100 / COUNT + 1 + "%";   // slight overlap, no gaps
      bar.style.background = mixColors(c1, c2, t); // gradient c1 → c2
      // Stagger the sweep so bars arrive in a quick wave.
      bar.style.animationDelay = (i * 28) + "ms";
      bar.style.setProperty("--dur", (700 + i * 12) + "ms");
      band.appendChild(bar);
    }
  });

  if (!("IntersectionObserver" in window)) {
    bands.forEach((b) => b.classList.add("in"));
    return;
  }
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        // Toggle so the sweep replays each time the band re-enters view.
        e.target.classList.toggle("in", e.isIntersecting);
      });
    },
    { threshold: 0.3 }
  );
  bands.forEach((b) => io.observe(b));
}

// Blend two "#rrggbb" colors. t=0 → c1, t=1 → c2. Used for the band gradient.
function mixColors(c1, c2, t) {
  const a = hexToRgb(c1), b = hexToRgb(c2);
  const r = Math.round(a.r + (b.r - a.r) * t);
  const g = Math.round(a.g + (b.g - a.g) * t);
  const bl = Math.round(a.b + (b.b - a.b) * t);
  return `rgb(${r}, ${g}, ${bl})`;
}
function hexToRgb(hex) {
  const h = hex.replace("#", "");
  return {
    r: parseInt(h.slice(0, 2), 16),
    g: parseInt(h.slice(2, 4), 16),
    b: parseInt(h.slice(4, 6), 16),
  };
}

// ── Portfolio + LinkedIn links ──────────────────────────────────────────────
// If you'd rather set these URLs here in JS instead of editing index.html,
// paste them below. Leaving one as "" keeps whatever is in index.html
// (currently "#"). Examples:
//   const PORTFOLIO_URL = "https://your-name.dev";
//   const LINKEDIN_URL  = "https://www.linkedin.com/in/your-name";
const PORTFOLIO_URL = "";
const LINKEDIN_URL = "";
function wirePortfolio() {
  if (PORTFOLIO_URL) {
    const link = $("#portfolio-link");
    if (link) link.href = PORTFOLIO_URL;
  }
  if (LINKEDIN_URL) {
    const li = $("#linkedin-link");
    if (li) li.href = LINKEDIN_URL;
  }
}

// ============================================================================
// 6) THREE.JS HERO  —  particles drifting outward (space / explosion feel)
// ============================================================================
// This builds a cloud of glowing points around the center of the hero. Every
// frame, each point moves a little further out along its own direction; when it
// drifts too far it respawns near the middle. The result is a gentle, endless
// outward drift — like stars streaming past, or a slow explosion. A faint slow
// rotation of the whole cloud adds depth.
//
// If Three.js failed to load (e.g. offline), we skip this quietly — the hero
// still looks great thanks to the CSS glow behind the logo.
function initHero() {
  const canvas = document.getElementById("hero-canvas");
  if (!canvas || typeof THREE === "undefined") return;

  const scene = new THREE.Scene();

  // A perspective camera looking at the center from a little way back.
  const camera = new THREE.PerspectiveCamera(70, 1, 0.1, 1000);
  camera.position.z = 60;

  const renderer = new THREE.WebGLRenderer({
    canvas,
    alpha: true,        // transparent background so the CSS gradient shows
    antialias: true,
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  // ---- Build the particles ----
  const COUNT = 1400;                       // how many points
  const positions = new Float32Array(COUNT * 3);
  const velocities = new Float32Array(COUNT * 3); // per-point outward direction
  const colors = new Float32Array(COUNT * 3);

  // Two brand colors we tint particles between: cyan-teal and indigo.
  const cyan = new THREE.Color("#7fe3dd");
  const indigo = new THREE.Color("#7c8cff");

  // Place each particle at a random point and give it an outward velocity.
  function seedParticle(i, nearCenter) {
    // Random direction on a sphere.
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    const dx = Math.sin(phi) * Math.cos(theta);
    const dy = Math.sin(phi) * Math.sin(theta);
    const dz = Math.cos(phi);

    // Start radius: near the center when respawning, spread out at first seed.
    const r = nearCenter ? Math.random() * 6 : Math.random() * 70;
    positions[i * 3] = dx * r;
    positions[i * 3 + 1] = dy * r;
    positions[i * 3 + 2] = dz * r;

    // Outward velocity (a little randomised so they don't move in lockstep).
    const speed = 0.05 + Math.random() * 0.13;
    velocities[i * 3] = dx * speed;
    velocities[i * 3 + 1] = dy * speed;
    velocities[i * 3 + 2] = dz * speed;

    // Color: blend between cyan and indigo per particle.
    const c = cyan.clone().lerp(indigo, Math.random());
    colors[i * 3] = c.r;
    colors[i * 3 + 1] = c.g;
    colors[i * 3 + 2] = c.b;
  }
  for (let i = 0; i < COUNT; i++) seedParticle(i, false);

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

  const material = new THREE.PointsMaterial({
    size: 0.55,
    vertexColors: true,
    transparent: true,
    opacity: 0.9,
    blending: THREE.AdditiveBlending, // glowing look where points overlap
    depthWrite: false,
  });

  const points = new THREE.Points(geometry, material);
  scene.add(points);

  // ---- Keep the canvas sized to the hero, on load and on resize ----
  function resize() {
    const w = canvas.clientWidth || window.innerWidth;
    const h = canvas.clientHeight || window.innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  resize();
  window.addEventListener("resize", resize);

  // Gentle parallax: the cloud leans slightly toward the mouse.
  let targetRotX = 0, targetRotY = 0;
  if (!REDUCED_MOTION) {
    window.addEventListener("mousemove", (e) => {
      targetRotY = (e.clientX / window.innerWidth - 0.5) * 0.4;
      targetRotX = (e.clientY / window.innerHeight - 0.5) * 0.4;
    });
  }

  // ---- Animation loop ----
  const RESPAWN_AT = 78; // distance from center at which a point resets
  function animate() {
    requestAnimationFrame(animate);

    const pos = geometry.attributes.position.array;

    // Move every particle outward; respawn the ones that drift too far.
    // (When reduced motion is on we skip the drift and just render a still field.)
    if (!REDUCED_MOTION) {
      for (let i = 0; i < COUNT; i++) {
        pos[i * 3] += velocities[i * 3];
        pos[i * 3 + 1] += velocities[i * 3 + 1];
        pos[i * 3 + 2] += velocities[i * 3 + 2];

        const x = pos[i * 3], y = pos[i * 3 + 1], z = pos[i * 3 + 2];
        if (x * x + y * y + z * z > RESPAWN_AT * RESPAWN_AT) {
          seedParticle(i, true); // reset near the center to keep the flow endless
        }
      }
      geometry.attributes.position.needsUpdate = true;

      // Ease the whole cloud toward the mouse-driven target + a slow auto spin.
      points.rotation.y += (targetRotY - points.rotation.y) * 0.03 + 0.0006;
      points.rotation.x += (targetRotX - points.rotation.x) * 0.03;
    }

    renderer.render(scene, camera);
  }
  animate();
}


// ============================================================================
// 7) STARTUP  —  wire everything up when the page loads
// ============================================================================
function init() {
  wireNavButtons();
  wireNavScroll();
  wireAuth();
  wireUpload();
  wireChat();
  wireReveals();
  wireBands();
  wirePortfolio();
  initHero();

  // Decide the first screen: if a saved token exists, go straight to the app;
  // otherwise show the landing page. (We do NOT verify the token here — the
  // first protected request will bounce us out if it has expired.)
  if (token) {
    enterApp();
  } else {
    showView("landing");
  }
}

// Run init once the HTML is parsed. (This script is loaded at the end of <body>,
// so the elements already exist, but DOMContentLoaded is a safe belt-and-braces.)
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}

