const form = document.getElementById("uploadForm");
const result = document.getElementById("result");
const apiBaseInput = document.getElementById("apiBase");
const apiDocsLink = document.getElementById("apiDocsLink");
const tenderIdLabel = document.getElementById("tenderId");
const recordStatusLabel = document.getElementById("recordStatus");
const ocrUsedLabel = document.getElementById("ocrUsed");
const saveDraftBtn = document.getElementById("saveDraftBtn");
const saveFinalBtn = document.getElementById("saveFinalBtn");
const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");
const historyList = document.getElementById("historyList");

const authUsername = document.getElementById("authUsername");
const authPassword = document.getElementById("authPassword");
const registerBtn = document.getElementById("registerBtn");
const loginBtn = document.getElementById("loginBtn");
const logoutBtn = document.getElementById("logoutBtn");
const authState = document.getElementById("authState");

const companyDetails = document.getElementById("companyDetails");
const paymentTerms = document.getElementById("paymentTerms");
const complianceRequirements = document.getElementById("complianceRequirements");
const serviceScope = document.getElementById("serviceScope");
const submissionFormats = document.getElementById("submissionFormats");
const notes = document.getElementById("notes");
const needsReview = document.getElementById("needsReview");
const finalOutput = document.getElementById("finalOutput");
const reviewerNotes = document.getElementById("reviewerNotes");

const tabs = Array.from(document.querySelectorAll(".tab"));
const panels = Array.from(document.querySelectorAll(".panel"));

const state = {
  tenderId: null,
  username: null,
  csrfToken: null,
};

const sameOriginApi = `${window.location.origin}`;
if (window.location.pathname.startsWith("/demo")) {
  apiBaseInput.value = sameOriginApi;
}
apiDocsLink.href = `${apiBaseInput.value}/docs`;

function linesToText(lines) {
  return (lines || []).join("\n");
}

function textToLines(value) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function setResult(payload) {
  result.textContent = JSON.stringify(payload, null, 2);
}

function getErrorMessage(payload, fallback) {
  if (!payload) return fallback;
  if (payload.error && payload.error.message) return payload.error.message;
  if (payload.detail) return payload.detail;
  return fallback;
}

function getCookie(name) {
  const token = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(`${name}=`));
  if (!token) return null;
  return decodeURIComponent(token.split("=")[1]);
}

function setAuthState(username, csrfToken) {
  state.username = username;
  state.csrfToken = csrfToken || getCookie("csrf_token");
}

function clearAuthState() {
  state.username = null;
  state.csrfToken = null;
}

function setWorkflow(payload) {
  state.tenderId = payload.tender_id;
  tenderIdLabel.textContent = payload.tender_id;
  recordStatusLabel.textContent = "processed";
  ocrUsedLabel.textContent = String(payload.ocr_used);

  companyDetails.value = linesToText(payload.extracted.company_details);
  paymentTerms.value = linesToText(payload.extracted.payment_terms);
  complianceRequirements.value = linesToText(payload.extracted.compliance_requirements);
  serviceScope.value = linesToText(payload.extracted.service_scope);
  submissionFormats.value = linesToText(payload.extracted.submission_formats);
  notes.value = linesToText(payload.extracted.notes);
  needsReview.value = linesToText(payload.needs_human_review);
  finalOutput.value = payload.final_output || "";
  updateAuthUi();
}

function updateAuthUi() {
  const loggedIn = Boolean(state.username);
  authState.textContent = loggedIn
    ? `Authenticated as ${state.username}`
    : "Not authenticated";
  if (logoutBtn) {
    logoutBtn.disabled = !loggedIn;
  }
  saveDraftBtn.disabled = !loggedIn || !state.tenderId;
  saveFinalBtn.disabled = !loggedIn || !state.tenderId;
  refreshHistoryBtn.disabled = !loggedIn;
}

async function authRequest(path, body) {
  const response = await fetch(`${apiBaseInput.value}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(getErrorMessage(data, "Auth request failed"));
  }
  return data;
}

function authHeaders(extra = {}) {
  const headers = {
    ...extra,
  };
  const csrfToken = state.csrfToken || getCookie("csrf_token");
  if (csrfToken) {
    headers["X-CSRF-Token"] = csrfToken;
  }
  return headers;
}

async function loadRecord(tenderId) {
  const response = await fetch(`${apiBaseInput.value}/api/tenders/${tenderId}`, {
    credentials: "include",
    headers: authHeaders(),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(getErrorMessage(data, "Failed to load record"));
  }
  setWorkflow({
    tender_id: data.tender_id,
    ocr_used: data.ocr_used,
    extracted: data.extracted,
    needs_human_review: data.needs_human_review,
    final_output: data.final_output,
  });
  recordStatusLabel.textContent = data.status;
  reviewerNotes.value = data.reviewer_notes || "";
  setResult(data);
  updateAuthUi();
}

async function loadHistory() {
  if (!state.username) {
    historyList.innerHTML = "";
    return;
  }

  const response = await fetch(`${apiBaseInput.value}/api/tenders/history?limit=40`, {
    credentials: "include",
    headers: authHeaders(),
  });
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthState();
      updateAuthUi();
    }
    throw new Error(getErrorMessage(data, "Failed to load history"));
  }

  historyList.innerHTML = "";
  if (!data.length) {
    const li = document.createElement("li");
    li.textContent = "No records yet for this reviewer.";
    historyList.appendChild(li);
    return;
  }

  data.forEach((record) => {
    const li = document.createElement("li");
    const info = document.createElement("span");
    info.textContent = `${record.tender_id} | ${record.source_filename} | ${record.status}`;
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Open";
    button.addEventListener("click", () => {
      loadRecord(record.tender_id).catch((error) => setResult({ error: error.message }));
    });
    li.appendChild(info);
    li.appendChild(button);
    historyList.appendChild(li);
  });
}

function getPayload(status) {
  return {
    extracted: {
      company_details: textToLines(companyDetails.value),
      payment_terms: textToLines(paymentTerms.value),
      compliance_requirements: textToLines(complianceRequirements.value),
      service_scope: textToLines(serviceScope.value),
      submission_formats: textToLines(submissionFormats.value),
      notes: textToLines(notes.value),
    },
    needs_human_review: textToLines(needsReview.value),
    final_output: finalOutput.value.trim(),
    reviewer_notes: reviewerNotes.value.trim(),
    status,
  };
}

async function saveReview(status) {
  if (!state.tenderId) {
    setResult({ error: "Process a tender first." });
    return;
  }

  try {
    const response = await fetch(`${apiBaseInput.value}/api/tenders/${state.tenderId}/save`, {
      method: "POST",
      credentials: "include",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(getPayload(status)),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(getErrorMessage(data, "Save failed"));
    }

    recordStatusLabel.textContent = data.status;
    setResult(data);
    await loadHistory();
  } catch (error) {
    setResult({ error: error.message });
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setResult({ status: "Processing..." });

  const formData = new FormData(form);

  try {
    const response = await fetch(`${apiBaseInput.value}/api/tenders/process`, {
      method: "POST",
      credentials: "include",
      headers: authHeaders(),
      body: formData,
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(getErrorMessage(data, "Request failed"));
    }

    setWorkflow(data);
    setResult(data);
    updateAuthUi();
    await loadHistory();
  } catch (error) {
    setResult({ error: error.message });
  }
});

registerBtn.addEventListener("click", async () => {
  try {
    const data = await authRequest("/api/auth/register", {
      username: authUsername.value.trim(),
      password: authPassword.value,
    });
    setResult(data);
  } catch (error) {
    setResult({ error: error.message });
  }
});

loginBtn.addEventListener("click", async () => {
  try {
    const data = await authRequest("/api/auth/login", {
      username: authUsername.value.trim(),
      password: authPassword.value,
    });
    setAuthState(data.username, data.csrf_token);
    updateAuthUi();
    await loadHistory();
    setResult({ message: "Login successful", username: data.username });
  } catch (error) {
    setResult({ error: error.message });
  }
});

if (logoutBtn) {
  logoutBtn.addEventListener("click", async () => {
    try {
      const response = await fetch(`${apiBaseInput.value}/api/auth/logout`, {
        method: "POST",
        credentials: "include",
        headers: authHeaders(),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(getErrorMessage(data, "Logout failed"));
      }
      clearAuthState();
      updateAuthUi();
      historyList.innerHTML = "";
      setResult(data);
    } catch (error) {
      setResult({ error: error.message });
    }
  });
}

refreshHistoryBtn.addEventListener("click", () => {
  loadHistory().catch((error) => setResult({ error: error.message }));
});

apiBaseInput.addEventListener("change", () => {
  apiDocsLink.href = `${apiBaseInput.value}/docs`;
});

saveDraftBtn.addEventListener("click", () => saveReview("draft"));
saveFinalBtn.addEventListener("click", () => saveReview("final"));

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((item) => item.classList.remove("active"));
    panels.forEach((item) => item.classList.remove("active"));
    tab.classList.add("active");
    const target = document.getElementById(`panel-${tab.dataset.tab}`);
    if (target) {
      target.classList.add("active");
    }
  });
});

updateAuthUi();

async function bootstrapSession() {
  try {
    const response = await fetch(`${apiBaseInput.value}/api/auth/me`, {
      credentials: "include",
      headers: authHeaders(),
    });
    const data = await response.json();
    if (!response.ok) {
      clearAuthState();
      updateAuthUi();
      return;
    }
    setAuthState(data.username, getCookie("csrf_token"));
    updateAuthUi();
    await loadHistory();
  } catch (_error) {
    clearAuthState();
    updateAuthUi();
  }
}

bootstrapSession().catch(() => {});
