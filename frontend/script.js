// ---------- Static homepage / cards / tips ----------

const servicesData = [
  {
    title: "Heart Disease Prediction",
    desc: "Evaluate cardiovascular risk with cholesterol, ECG, and lifestyle markers.",
  },
  {
    title: "Diabetes Check",
    desc: "Assess glucose trends, BMI, insulin, and pedigree factors to classify risk.",
  },
  {
    title: "Blood Pressure Check",
    desc: "Log systolic/diastolic values plus habits to pinpoint hypertension stages.",
  },
  {
    title: "BMI & Body Composition",
    desc: "Monitor weight trends with contextual coaching and habit reminders.",
  },
  {
    title: "Cholesterol Profile",
    desc: "Track HDL, LDL, triglycerides and receive actionable nutrition tips.",
  },
  {
    title: "Liver Function",
    desc: "Spot liver stress early through ILPD markers and probability insights.",
  },
];

const timelineFeed = [
  { test: "Kidney Function", region: "Pune, IN", movement: "+42%", status: "Spike" },
  { test: "Heart Disease", region: "Doha, QA", movement: "+18%", status: "Trending" },
  { test: "Diabetes Panel", region: "Bengaluru, IN", movement: "-9%", status: "Stabilizing" },
  { test: "Thyroid Function", region: "Singapore", movement: "+22%", status: "Rising" },
];

const healthTips = [
  "Hydrate before every fasting test for accurate readings.",
  "Pair every report with 10 minutes of reflection to plan next steps.",
  "Consistency beats intensity—track metrics weekly instead of sporadically.",
  "Sleep quality changes most blood biomarker trends. Target 7+ hours.",
  "Share your dashboard with a clinician to co-create lifestyle nudges.",
];

// Backend API base URLs (override via window.SUSWASTHA_CONFIG)
const API_CONFIG = window.SUSWASTHA_CONFIG || {};

const FASTAPI_BASE = API_CONFIG.fastapiBaseUrl;
const NODE_API_BASE = API_CONFIG.nodeBaseUrl || "";

// Safety check (VERY IMPORTANT)
if (!FASTAPI_BASE) {
  console.error("FASTAPI_BASE missing — config.js not loaded");
}

// Temporary debug log (remove after verification)
console.log("API BASE:", FASTAPI_BASE);

const USERS_KEY = "suswastha_users";
const REPORTS_KEY = "suswastha_reports";
const OTP_STORE_KEY = "suswastha_pending_otps";
const TOKEN_KEY = "suswastha_token";

// Theme key for dark/light mode
const THEME_KEY = "suswastha_theme";

// ---------- Helpers ----------

function getCurrentUserEmail() {
  return localStorage.getItem("suswastha_email") || null;
}

function setCurrentUserEmail(email) {
  localStorage.setItem("suswastha_email", email);
}

function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

function buildAuthHeaders(extra = {}) {
  const headers = { ...extra };
  const token = getAuthToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

// ✅ NEW: store full profile (name, email, dob)
function getCurrentUserProfile() {
  const raw = localStorage.getItem("suswastha_profile");
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function setCurrentUserProfile(profile) {
  localStorage.setItem("suswastha_profile", JSON.stringify(profile));
}

function validEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((email || "").trim());
}

function validPassword(password) {
  return /^(?=.*\d).{6,}$/.test(password || "");
}

function getUsers() {
  try {
    return JSON.parse(localStorage.getItem(USERS_KEY) || "[]");
  } catch {
    return [];
  }
}

function setUsers(users) {
  localStorage.setItem(USERS_KEY, JSON.stringify(users));
}

function getReports() {
  try {
    return JSON.parse(localStorage.getItem(REPORTS_KEY) || "[]");
  } catch {
    return [];
  }
}

function getReportsForEmail(email) {
  return getReports().filter((report) => report.email === email);
}

function getOtpStore() {
  try {
    return JSON.parse(localStorage.getItem(OTP_STORE_KEY) || "{}");
  } catch {
    return {};
  }
}

function setOtpStore(store) {
  localStorage.setItem(OTP_STORE_KEY, JSON.stringify(store));
}

// ---------- Scroll animations ----------

function setupScrollAnimations() {
  const elements = document.querySelectorAll("[data-animate]");
  if (!elements.length) return;

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );
    elements.forEach((el) => observer.observe(el));
  } else {
    elements.forEach((el) => el.classList.add("visible"));
  }
}

// ---------- Dark mode ----------

function applyTheme(theme) {
  const body = document.body;
  if (theme === "dark") body.classList.add("dark");
  else body.classList.remove("dark");
  const btn = document.getElementById("theme-toggle");
  if (btn) btn.textContent = theme === "dark" ? "☀️" : "🌙";
}

function initTheme() {
  let theme = localStorage.getItem(THEME_KEY) || "light";
  applyTheme(theme);
  const toggle = document.getElementById("theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", () => {
      const next = document.body.classList.contains("dark") ? "light" : "dark";
      localStorage.setItem(THEME_KEY, next);
      applyTheme(next);
    });
  }
}

// ---------- Ask SuSwastha widget ----------

function setupAskWidget() {
  const toggleBtn = document.getElementById("ask-toggle");
  const closeBtn = document.getElementById("ask-close");
  const panel = document.getElementById("ask-panel");
  const form = document.getElementById("ask-form");
  const input = document.getElementById("ask-input");
  const messages = document.getElementById("ask-messages");

  if (!toggleBtn || !panel || !form || !input || !messages) return;

  const openPanel = () => panel.classList.add("open");
  const closePanel = () => panel.classList.remove("open");

  toggleBtn.addEventListener("click", () =>
    panel.classList.contains("open") ? closePanel() : openPanel()
  );
  if (closeBtn) closeBtn.addEventListener("click", closePanel);

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    const userDiv = document.createElement("div");
    userDiv.className = "msg msg-user";
    userDiv.textContent = text;
    messages.appendChild(userDiv);

    const botDiv = document.createElement("div");
    botDiv.className = "msg msg-bot";
    botDiv.textContent =
      "Thanks for your question! SuSwastha can help you run screenings and generate reports. " +
      "For personal medical advice or emergencies, please consult a doctor or hospital.";
    messages.appendChild(botDiv);

    messages.scrollTop = messages.scrollHeight;
    input.value = "";
  });
}

// ---------- MAIN INIT ----------

document.addEventListener("DOMContentLoaded", () => {
  const yearTarget = document.getElementById("year");
  if (yearTarget) yearTarget.textContent = new Date().getFullYear();

  // Smooth scroll
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", (event) => {
      const targetId = anchor.getAttribute("href");
      const targetElement = document.querySelector(targetId);
      if (targetElement) {
        event.preventDefault();
        targetElement.scrollIntoView({ behavior: "smooth" });
      }
    });
  });

  // Simple forms
  document.querySelectorAll("[data-simple-submit]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      alert("Thanks! Our care team will respond shortly.");
      form.reset();
    });
  });

  // Home page cards
  const servicesGrid = document.getElementById("services-grid");
  if (servicesGrid) {
    servicesGrid.innerHTML = servicesData
      .map(
        (s) => `<article class="service-card"><h3>${s.title}</h3><p>${s.desc}</p></article>`
      )
      .join("");
  }

  // Timeline
  const timelineTarget = document.getElementById("timeline-feed");
  if (timelineTarget) {
    timelineTarget.innerHTML = timelineFeed
      .map(
        (e) => `
        <div class="timeline-item">
          <div class="timeline-meta">
            <h4>${e.test}</h4>
            <p class="muted">${e.region}</p>
          </div>
          <span class="pill">${e.status} · ${e.movement}</span>
        </div>`
      )
      .join("");
  }

  // Health tips
  const tipTarget = document.getElementById("health-tip");
  const shuffleTipBtn = document.getElementById("shuffle-tip");
  if (tipTarget && shuffleTipBtn) {
    shuffleTipBtn.addEventListener("click", () => {
      tipTarget.textContent = healthTips[Math.floor(Math.random() * healthTips.length)];
    });
  }

  // ✅ Auto-fill report email with logged-in email
  const reportEmailInput = document.querySelector('#report-generator input[name="email"]');
  if (reportEmailInput) {
    const loggedEmail = getCurrentUserEmail();
    if (loggedEmail) reportEmailInput.value = loggedEmail;
  }

  setupScrollAnimations();
  initTheme();
  setupAskWidget();
  setupTestPrediction();
  setupAuthForms();
  setupDashboardReports();
  setupHistoryPage();
});

// ---------- Report History Page ----------

function setupHistoryPage() {
  if (!window.location.pathname.includes("report-history.html")) return;
  const tbody = document.querySelector(".history-table table tbody");
  if (!tbody) return;

  const email = getCurrentUserEmail();
  if (!email) {
    tbody.innerHTML = `<tr><td colspan="5">Please <a href="login.html">login</a> to see your history.</td></tr>`;
    return;
  }

  const loadHistory = async () => {
    try {
      const response = await fetch(`${FASTAPI_BASE}/api/user/reports`, { headers: buildAuthHeaders() });
      if (!response.ok) throw new Error(`Failed to load history (${response.status})`);
      const data = await response.json();
      
      if (!Array.isArray(data) || data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5">No reports found in your archive.</td></tr>`;
        return;
      }

      const sorted = [...data].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      tbody.innerHTML = sorted
        .map((row) => {
          const date = new Date(row.created_at);
          const formattedDate = date.toLocaleDateString("en-GB", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            hour12: true,
          });
          return `
            <tr>
              <td>${row.test_type ? row.test_type.replace("_", " ").toUpperCase() : "-"}</td>
              <td>${formattedDate}</td>
              <td>${row.risk_score ? row.risk_score.toFixed(1) + "%" : "-"}</td>
              <td><span class="badge">${row.label || "-"}</span></td>
              <td>${
                row.pdf_url
                  ? `<a href="${row.pdf_url}" class="btn ghost sm" target="_blank" rel="noopener">View Report</a>`
                  : `<span class="muted">Generating...</span>`
              }</td>
            </tr>`;
        })
        .join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5">${err.message || "Could not load history."}</td></tr>`;
    }
  };
  loadHistory();
}

// ---------- TEST PREDICTION (ALL MODULE PAGES) ----------

function setupTestPrediction() {
  const form = document.querySelector(".test-form");
  const outputBox = document.querySelector(".output-box");
  if (!form || !outputBox) return;

  if (!FASTAPI_BASE) {
    alert("Backend configuration missing. Please refresh and try again.");
    return;
  }

  let pathname = window.location.pathname;
  if (pathname.includes("/")) {
    pathname = pathname.split("/").pop();
  }

  let testType = null;

  if (pathname.includes("diabetes")) testType = "diabetes";
  else if (pathname.includes("cholesterol")) testType = "cholesterol";
  else if (pathname.includes("kidney")) testType = "kidney";
  else if (pathname.includes("liver")) testType = "liver";
  else if (pathname.includes("heart")) testType = "heart";
  else if (pathname.includes("blood-pressure")) testType = "blood_pressure";
  else if (pathname.includes("thyroid")) testType = "thyroid";

  if (!testType) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = getCurrentUserEmail();
    if (!email) {
      alert("Please login first to run predictions.");
      window.location.href = "login.html";
      return;
    }

    const inputs = Array.from(form.querySelectorAll("input"));
    const selects = Array.from(form.querySelectorAll("select"));

    const getNumber = (idx, fallback = 0) => {
      const el = inputs[idx];
      if (!el) return fallback;
      const v = parseFloat(el.value);
      return isNaN(v) ? fallback : v;
    };

    const getSelectIndex = (idx) => {
      const el = selects[idx];
      if (!el) return 0;
      return el.selectedIndex;
    };

    let payload = null;

    switch (testType) {
      case "diabetes":
        payload = {
          glucose: getNumber(0),
          blood_pressure: getNumber(1),
          skin_thickness: getNumber(2),
          bmi: getNumber(3),
          age: getNumber(4),
          insulin: getNumber(5),
          pedigree: getNumber(6),
          email,
        };
        break;

      case "cholesterol":
        payload = {
          total_cholesterol: getNumber(0),
          hdl: getNumber(1),
          ldl: getNumber(2),
          triglycerides: getNumber(3),
          age: getNumber(4),
          bmi: getNumber(5),
          blood_pressure: getNumber(6),
          smoking_status: getSelectIndex(0),
          family_history: getSelectIndex(1),
          email,
        };
        break;

      case "kidney":
        payload = {
          age: getNumber(0),
          blood_pressure: getNumber(1),
          specific_gravity: getNumber(2),
          albumin: getNumber(3),
          sugar: getNumber(4),
          blood_glucose_random: getNumber(5),
          blood_urea: getNumber(6),
          serum_creatinine: getNumber(7),
          sodium: getNumber(8),
          potassium: getNumber(9),
          hemoglobin: getNumber(10),
          packed_cell_volume: getNumber(11),
          white_blood_cell_count: getNumber(12),
          red_blood_cell_count: getNumber(13),
          email,
        };
        break;

      case "liver": {
        const genderIndex = getSelectIndex(0);
        payload = {
          age: getNumber(0),
          gender: genderIndex,
          total_bilirubin: getNumber(1),
          direct_bilirubin: getNumber(2),
          alkaline_phosphatase: getNumber(3),
          alt: getNumber(4),
          ast: getNumber(5),
          total_proteins: getNumber(6),
          albumin: getNumber(7),
          ag_ratio: getNumber(8),
          email,
        };
        break;
      }

      case "heart": {
        const sexIndex = getSelectIndex(0);
        const chestPainIndex = getSelectIndex(1);
        const fbsIndex = getSelectIndex(2);
        const restecgIndex = getSelectIndex(3);
        const exangIndex = getSelectIndex(4);
        const slopeIndex = getSelectIndex(5);
        const thalIndex = getSelectIndex(6);

        payload = {
          age: getNumber(0),
          sex: sexIndex,
          cp: chestPainIndex,
          trestbps: getNumber(2),
          chol: getNumber(3),
          fbs: fbsIndex,
          restecg: restecgIndex,
          thalach: getNumber(4),
          exang: exangIndex,
          oldpeak: getNumber(5),
          slope: slopeIndex,
          ca: getNumber(6),
          thal: thalIndex,
          email,
        };
        break;
      }

      case "blood_pressure": {
        const stressIndex = getSelectIndex(0);
        const activityIndex = getSelectIndex(1);
        payload = {
          systolic: getNumber(0),
          diastolic: getNumber(1),
          age: getNumber(2),
          weight: getNumber(3),
          height: getNumber(4),
          stress_level: stressIndex,
          activity_level: activityIndex,
          email,
        };
        break;
      }

      case "thyroid": {
        const sexIndex = getSelectIndex(0);
        const medIndex = getSelectIndex(1);
        const pregIndex = getSelectIndex(2);
        const goitreIndex = getSelectIndex(3);
        payload = {
          age: getNumber(0),
          sex: sexIndex,
          tsh: getNumber(1),
          t3: getNumber(2),
          t4: getNumber(3),
          free_t4_index: getNumber(4),
          free_t3_index: getNumber(5),
          medication_status: medIndex,
          pregnancy_status: pregIndex,
          goitre_status: goitreIndex,
          email,
        };
        break;
      }

      default:
        alert("Unknown test type.");
        return;
    }

    try {
      outputBox.innerHTML = "<p>Running prediction...</p>";
      outputBox.scrollIntoView({ behavior: "smooth", block: "nearest" });

      const controller = new AbortController();
      const timeoutMs = 40000;
      const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

      const response = await fetch(`${FASTAPI_BASE}/api/predict/${testType}`, {
        method: "POST",
        headers: buildAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      const rawText = await response.text();
      if (!response.ok) {
        console.error(rawText);
        outputBox.innerHTML = `
          <h3>Prediction failed</h3>
          <p>Server error (${response.status}). Check console for details.</p>
        `;
        return;
      }

      let data;
      try {
        data = JSON.parse(rawText);
      } catch (parseErr) {
        console.error("Response was not JSON:", rawText);
        outputBox.innerHTML = `
          <h3>Prediction failed</h3>
          <p>Invalid response from server. Check console.</p>
        `;
        return;
      }

      const labelText = data.label || data.status || "N/A";
      const riskNum = Number(data.risk_score);
      const riskScore = Number.isFinite(riskNum) ? riskNum.toFixed(1) : null;

      let pdfLinkHtml = "";
      if (data.pdf_url) {
        const pdfUrl = String(data.pdf_url).startsWith("http")
          ? data.pdf_url
          : `${FASTAPI_BASE}${data.pdf_url}`;
        pdfLinkHtml = `
          <p>
            <a href="${pdfUrl}" target="_blank" class="btn primary">
              Download PDF Report
            </a>
          </p>`;
      }

      outputBox.innerHTML = `
        <h3>Prediction result</h3>
        <p><strong>Status:</strong> ${labelText}</p>
        ${riskScore != null ? `<p><strong>Risk Score:</strong> ${riskScore}%</p>` : ""}
        ${data.message ? `<p>${data.message}</p>` : ""}
        ${pdfLinkHtml || `<p class="muted"><i>Report is being generated. You can view it in your <a href="report-history.html">History</a> in a few moments.</i></p>`}
      `;
      outputBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (err) {
      console.error(err);
      if (err?.name === "AbortError") {
        outputBox.innerHTML = `
          <h3>Prediction timed out</h3>
          <p>
            The server took too long to respond (>${timeoutMs / 1000}s).
            If you're running locally, make sure the backend is running at <code>${FASTAPI_BASE}</code>.
          </p>
        `;
        return;
      }
      outputBox.innerHTML = `
        <h3>Prediction failed</h3>
        <p>${err.message || "Could not connect to the server. Make sure the backend (FastAPI) is running."}</p>
      `;
    }
  });
}

// ---------- AUTH (signup/login) ----------

function setupAuthForms() {
  const safeError = async (response) => {
    const body = await response.text();
    try {
      const parsed = JSON.parse(body);
      return parsed.detail || parsed.error || parsed.message || `Request failed (${response.status})`;
    } catch {
      return body || `Request failed (${response.status})`;
    }
  };
  const setFormMsg = (target, message, ok = false) => {
    if (!target) return;
    target.textContent = message || "";
    target.style.color = ok ? "#0c8a43" : "#d93025";
  };

  if (!FASTAPI_BASE) {
    alert("Backend configuration missing (config.js not loaded). Please refresh and try again.");
    return;
  }

  const requestOtp = async (url, payload, errorTarget) => {
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const msg = await safeError(res);
        if (errorTarget) setFormMsg(errorTarget, msg);
        alert(msg);
        return false;
      }
      return true;
    } catch (err) {
      const msg = err?.message || "Could not contact auth service.";
      if (errorTarget) setFormMsg(errorTarget, msg);
      alert(msg);
      return false;
    }
  };

  const verifyOtp = async (url, payload, errorTarget) => {
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const msg = await safeError(res);
        if (errorTarget) setFormMsg(errorTarget, msg);
        alert(msg);
        return null;
      }
      return await res.json();
    } catch (err) {
      const msg = err?.message || "Could not contact auth service.";
      if (errorTarget) setFormMsg(errorTarget, msg);
      alert(msg);
      return null;
    }
  };

  const signupForm = document.querySelector("form#signup-form");
  if (signupForm) {
    const signupError = document.getElementById("signup-error");
    const sendSignupOtpBtn = document.getElementById("send-signup-otp");
    if (sendSignupOtpBtn) {
      sendSignupOtpBtn.addEventListener("click", async () => {
        const formData = new FormData(signupForm);
        const name = String(formData.get("name") || "").trim();
        const email = String(formData.get("email") || "").trim().toLowerCase();
        const password = String(formData.get("password") || "");
        if (!name) return setFormMsg(signupError, "Name is required.");
        if (!validEmail(email)) return setFormMsg(signupError, "Enter a valid email address.");
        if (!validPassword(password)) return setFormMsg(signupError, "Password must be at least 6 chars and include a number.");
        setFormMsg(signupError, "Sending OTP...");
        sendSignupOtpBtn.disabled = true;
        const ok = await requestOtp(
          `${FASTAPI_BASE}/api/auth/signup/request-otp`,
          { name, email, password, dob: String(formData.get("dob") || "") || null },
          signupError
        );
        if (ok) setFormMsg(signupError, "OTP sent. Check your email.", true);
        setTimeout(() => (sendSignupOtpBtn.disabled = false), 30000);
      });
    }
    signupForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(signupForm);
      const name = String(formData.get("name") || "").trim();
      const email = String(formData.get("email") || "").trim().toLowerCase();
      const password = String(formData.get("password") || "");
      const dob = String(formData.get("dob") || "") || null;
      if (!name) return setFormMsg(signupError, "Name is required.");
      if (!validEmail(email)) return setFormMsg(signupError, "Enter a valid email address.");
      if (!validPassword(password))
        return setFormMsg(signupError, "Password must be at least 6 chars and include a number.");

      try {
        const otpInput = signupForm.querySelector('input[name="otp"]');
        const otp =
          (otpInput && String(otpInput.value || "").trim()) ||
          String(prompt("Enter the OTP sent to your email:") || "").trim();
        if (!/^\d{6}$/.test(otp)) return setFormMsg(signupError, "Enter a valid 6-digit OTP.");
        if (otpInput) otpInput.value = otp;

        const data = await verifyOtp(
          `${FASTAPI_BASE}/api/auth/signup/verify`,
          { name, email, password, dob, otp },
          signupError
        );
        if (!data) return;

        localStorage.setItem(TOKEN_KEY, data.access_token || "");
        setCurrentUserEmail(email);
        setCurrentUserProfile({ name, email, dob: dob || "" });
        if (typeof window.loginUser === "function") {
          window.loginUser({ email, name, access_token: data.access_token });
          return;
        }
        window.location.href = "dashboard.html";
      } catch (err) {
        setFormMsg(signupError, err.message || "Could not complete signup.");
      }
    });
  }

  const loginForm = document.querySelector("form#login-form");
  if (loginForm) {
    const loginError = document.getElementById("login-error");
    const sendLoginOtpBtn = document.getElementById("send-login-otp");
    if (sendLoginOtpBtn) {
      sendLoginOtpBtn.addEventListener("click", async () => {
        const formData = new FormData(loginForm);
        const email = String(formData.get("email") || "").trim().toLowerCase();
        const password = String(formData.get("password") || "");
        if (!validEmail(email)) return setFormMsg(loginError, "Enter a valid email address.");
        if (!password) return setFormMsg(loginError, "Password is required to request OTP.");
        setFormMsg(loginError, "Sending OTP...");
        sendLoginOtpBtn.disabled = true;
        const ok = await requestOtp(
          `${FASTAPI_BASE}/api/auth/login/request-otp`,
          { email, password, purpose: "login" },
          loginError
        );
        if (ok) setFormMsg(loginError, "OTP sent. Check your email.", true);
        setTimeout(() => (sendLoginOtpBtn.disabled = false), 30000);
      });
    }
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(loginForm);
      const email = String(formData.get("email") || "").trim().toLowerCase();
      if (!validEmail(email)) return setFormMsg(loginError, "Enter a valid email address.");
      try {
        const otpInput = loginForm.querySelector('input[name="otp"]');
        const otp =
          (otpInput && String(otpInput.value || "").trim()) ||
          String(prompt("Enter the OTP sent to your email:") || "").trim();
        if (!/^\d{6}$/.test(otp)) return setFormMsg(loginError, "Enter a valid 6-digit OTP.");
        if (otpInput) otpInput.value = otp;

        const data = await verifyOtp(
          `${FASTAPI_BASE}/api/auth/login/verify`,
          { email, otp },
          loginError
        );
        if (!data) return;

        localStorage.setItem(TOKEN_KEY, data.access_token || "");
        setCurrentUserEmail(email);
        const meRes = await fetch(`${FASTAPI_BASE}/api/me`, { headers: buildAuthHeaders() });
        if (meRes.ok) {
          const me = await meRes.json();
          setCurrentUserProfile({ name: me.name || "", email: me.email || email, dob: me.dob || "" });
          if (typeof window.loginUser === "function") {
            window.loginUser({ email: me.email || email, name: me.name || "", access_token: data.access_token });
            return;
          }
        } else if (typeof window.loginUser === "function") {
          window.loginUser({ email, access_token: data.access_token });
          return;
        }
        window.location.href = "dashboard.html";
      } catch (err) {
        setFormMsg(loginError, err.message || "Could not complete login.");
      }
    });
  }
}

// ---------- Dashboard (load user reports + fill profile) ----------

function setupDashboardReports() {
  if (!window.location.pathname.includes("dashboard.html")) return;
  const tbody = document.querySelector("#reports table tbody");
  if (!tbody) return;

  const email = getCurrentUserEmail();

  // If not logged in, show message and stop
  if (!email) {
    tbody.innerHTML = `
      <tr><td colspan="4">Please <a href="login.html">login</a> to see your reports.</td></tr>
    `;
    const greetingEl = document.getElementById("dashboard-greeting");
    const subtitleEl = document.getElementById("dashboard-subtitle");
    if (greetingEl) greetingEl.textContent = "Hello, Guest";
    if (subtitleEl) subtitleEl.textContent = "Please login to view your dashboard.";
    return;
  }

  // ✅ Fill basic profile info from localStorage
  const profile = getCurrentUserProfile();
  const greetingEl = document.getElementById("dashboard-greeting");
  const subtitleEl = document.getElementById("dashboard-subtitle");
  const nameEl = document.getElementById("dashboard-name");
  const emailEl = document.getElementById("dashboard-email");
  const dobEl = document.getElementById("dashboard-dob");

  if (greetingEl) greetingEl.textContent = `Hello, ${profile?.name || email}`;
  if (subtitleEl) subtitleEl.textContent = `Logged in as ${email}`;
  if (nameEl) nameEl.textContent = `Name: ${profile?.name || "-"}`;
  if (emailEl) emailEl.textContent = `Email: ${email}`;
  if (dobEl) dobEl.textContent = `Date of Birth: ${profile?.dob || "-"}`;

  // Elements for cards
  const savedCountEl = document.getElementById("dashboard-saved-count");
  const savedBadgeEl = document.getElementById("dashboard-saved-badge");
  const lastTestEl = document.getElementById("dashboard-last-test");
  const lastStatusEl = document.getElementById("dashboard-last-status");

  const loadReports = async () => {
    try {
      const response = await fetch(`${FASTAPI_BASE}/api/user/reports`, { headers: buildAuthHeaders() });
      if (!response.ok) throw new Error(`Failed to load reports (${response.status})`);
      const data = await response.json();
      if (!Array.isArray(data) || data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4">No reports found yet.</td></tr>`;
        if (savedCountEl) savedCountEl.textContent = "0 total reports";
        if (savedBadgeEl) savedBadgeEl.textContent = "No reports yet";
        if (lastTestEl) lastTestEl.textContent = "Last test: -";
        if (lastStatusEl) lastStatusEl.textContent = "Status: -";
        return;
      }

      const sorted = [...data].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      if (savedCountEl) savedCountEl.textContent = `${sorted.length} total reports`;
      if (savedBadgeEl) savedBadgeEl.textContent = "Synced from cloud";
      const latest = sorted[0];
      if (lastTestEl) lastTestEl.textContent = `Last test: ${new Date(latest.created_at).toLocaleString()}`;
      if (lastStatusEl) lastStatusEl.textContent = `Status: ${latest.label || "-"}`;
      tbody.innerHTML = sorted
        .map(
          (row) => {
            const date = new Date(row.created_at);
            const formattedDate = date.toLocaleDateString('en-GB', {
              day: '2-digit',
              month: '2-digit',
              year: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
              hour12: true
            });
            const actionLink = row.pdf_url 
              ? `<a href="${row.pdf_url}" target="_blank" rel="noopener" class="view-link">View</a>` 
              : `<span class="processing-text">Generating...</span>`;
            return `
        <tr>
          <td>${row.test_type || "-"}</td>
          <td>${formattedDate}</td>
          <td><span class="badge ${row.label?.toLowerCase().includes('high') ? 'risk-high' : 'risk-low'}">${row.label || "-"}</span></td>
          <td>${actionLink}</td>
        </tr>`;
          }
        )
        .join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="4">${err.message || "Could not load reports."}</td></tr>`;
    }
  };
  loadReports();
}
