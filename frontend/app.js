const API_BASE = "";

const healthDot = document.getElementById("health-dot");
const healthText = document.getElementById("health-text");

const tabs = document.querySelectorAll(".tab");
const panels = {
  upload: document.getElementById("panel-upload"),
  url: document.getElementById("panel-url"),
  text: document.getElementById("panel-text"),
};

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const dropzoneText = document.getElementById("dropzone-text");
const uploadForm = document.getElementById("upload-form");
const uploadSubmit = document.getElementById("upload-submit");

const urlForm = document.getElementById("url-form");
const urlInput = document.getElementById("url-input");
const urlSubmit = document.getElementById("url-submit");

const textForm = document.getElementById("text-form");
const textInput = document.getElementById("text-input");
const textSubmit = document.getElementById("text-submit");

const results = document.getElementById("results");
const loading = document.getElementById("loading");
const loadingText = document.getElementById("loading-text");
const errorBanner = document.getElementById("error-banner");
const resultCards = document.getElementById("result-cards");
const outTranscript = document.getElementById("out-transcript");
const outSw = document.getElementById("out-sw");
const outEn = document.getElementById("out-en");

async function checkHealth() {
  try {
    const resp = await fetch(`${API_BASE}/health`);
    if (!resp.ok) throw new Error();
    healthDot.className = "status-dot ok";
    healthText.textContent = "Backend online";
  } catch {
    healthDot.className = "status-dot down";
    healthText.textContent = "Backend unreachable";
  }
}
checkHealth();
setInterval(checkHealth, 15000);

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((t) => {
      t.classList.remove("active");
      t.setAttribute("aria-selected", "false");
    });
    tab.classList.add("active");
    tab.setAttribute("aria-selected", "true");
    Object.values(panels).forEach((p) => p.classList.remove("active"));
    panels[tab.dataset.tab].classList.add("active");
  });
});

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  dropzoneText.textContent = file ? file.name : "Choose an audio/video file, or drag one here";
  uploadSubmit.disabled = !file;
});

["dragover", "dragenter"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("drag-over");
  })
);
["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("drag-over");
  })
);
dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) {
    fileInput.files = e.dataTransfer.files;
    dropzoneText.textContent = file.name;
    uploadSubmit.disabled = false;
  }
});

function showLoading(text) {
  results.hidden = false;
  loading.hidden = false;
  loadingText.textContent = text;
  errorBanner.hidden = true;
  resultCards.hidden = true;
}

function showError(message) {
  loading.hidden = true;
  errorBanner.hidden = false;
  errorBanner.textContent = message;
  resultCards.hidden = true;
}

function renderTranslation(el, value) {
  if (value) {
    el.textContent = value;
    el.classList.remove("unavailable");
  } else {
    el.textContent = "Not available (translation is not configured on this backend right now).";
    el.classList.add("unavailable");
  }
}

function showResult(data) {
  loading.hidden = true;
  errorBanner.hidden = true;
  resultCards.hidden = false;
  const sourceText = data.transcript ?? data.text;
  outTranscript.textContent = sourceText || "(empty)";
  renderTranslation(outSw, data.translation_sw);
  renderTranslation(outEn, data.translation_en);
}

async function handleResponse(resp) {
  if (!resp.ok) {
    let message = `Request failed (HTTP ${resp.status}).`;
    try {
      const body = await resp.json();
      if (body.detail) message = body.detail;
    } catch {
      /* ignore parse errors, use default message */
    }
    showError(message);
    return;
  }
  const data = await resp.json();
  showResult(data);
}

uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = fileInput.files[0];
  if (!file) return;

  uploadSubmit.disabled = true;
  showLoading("Uploading and transcribing… this can take a while on first run (model download).");

  const formData = new FormData();
  formData.append("file", file);

  try {
    const resp = await fetch(`${API_BASE}/transcribe`, {
      method: "POST",
      body: formData,
    });
    await handleResponse(resp);
  } catch (err) {
    showError(`Network error: ${err.message}`);
  } finally {
    uploadSubmit.disabled = false;
  }
});

urlForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const url = urlInput.value.trim();
  if (!url) return;

  urlSubmit.disabled = true;
  showLoading("Downloading audio and transcribing… this can take a while for longer videos.");

  try {
    const resp = await fetch(`${API_BASE}/transcribe-url`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    await handleResponse(resp);
  } catch (err) {
    showError(`Network error: ${err.message}`);
  } finally {
    urlSubmit.disabled = false;
  }
});

textForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = textInput.value.trim();
  if (!text) return;

  textSubmit.disabled = true;
  showLoading("Translating…");

  try {
    const resp = await fetch(`${API_BASE}/translate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    await handleResponse(resp);
  } catch (err) {
    showError(`Network error: ${err.message}`);
  } finally {
    textSubmit.disabled = false;
  }
});
