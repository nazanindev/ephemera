const API = "http://localhost:8000";
const POLL_INTERVAL = 1500;

const promptScreen = document.getElementById("prompt-screen");
const canvasScreen = document.getElementById("canvas-screen");
const canvas = document.getElementById("canvas");
const input = document.getElementById("topic-input");
const btn = document.getElementById("generate-btn");
const statusText = document.getElementById("status-text");
const resetBtn = document.getElementById("reset-btn");
const progressWrap = document.getElementById("progress-wrap");
const progressBar = document.getElementById("progress-bar");

btn.addEventListener("click", onGenerate);
input.addEventListener("keydown", (e) => { if (e.key === "Enter") onGenerate(); });
resetBtn.addEventListener("click", onReset);

async function onGenerate() {
  const topic = input.value.trim();
  if (!topic) return;

  btn.disabled = true;
  progressWrap.hidden = false;
  setProgress(0);
  setStatus("gathering fragments...");

  try {
    const res = await fetch(`${API}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic }),
    });
    if (!res.ok) throw new Error("generate failed");
    const { job_id } = await res.json();
    pollJob(job_id);
  } catch (err) {
    setStatus("something went wrong. try again.");
    btn.disabled = false;
  }
}

function pollJob(jobId) {
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`${API}/job/${jobId}`);
      if (!res.ok) throw new Error();
      const { status, progress } = await res.json();

      setProgress(progress);
      const labels = {
        pending: "waiting...",
        running: progressLabel(progress),
        done: "rendering...",
        failed: "pipeline failed. try again.",
      };
      setStatus(labels[status] ?? status);

      if (status === "done") {
        clearInterval(interval);
        await renderCollage(jobId);
      } else if (status === "failed") {
        clearInterval(interval);
        btn.disabled = false;
      }
    } catch {
      clearInterval(interval);
      setStatus("lost connection.");
      btn.disabled = false;
    }
  }, POLL_INTERVAL);
}

function progressLabel(p) {
  if (p < 30) return "scraping images...";
  if (p < 60) return "pulling archive fragments...";
  if (p < 80) return "extracting metadata...";
  if (p < 95) return "composing collage...";
  return "almost there...";
}

async function renderCollage(jobId) {
  const res = await fetch(`${API}/collage/${jobId}`);
  const data = await res.json();

  canvas.innerHTML = "";
  canvas.style.width = `${data.canvas.width}px`;
  canvas.style.height = `${data.canvas.height}px`;

  for (const frag of data.fragments) {
    const el = buildFragment(frag);
    if (el) canvas.appendChild(el);
  }

  promptScreen.hidden = true;
  canvasScreen.hidden = false;
}

function buildFragment(frag) {
  const { layout, type, content, source_url, og, captured_at } = frag;
  if (!layout) return null;

  const { x, y, width, rotation, z_index, css_filter, blend_mode } = layout;

  const wrapper = document.createElement("div");
  wrapper.className = "fragment";
  wrapper.style.cssText = [
    `left: ${x}px`,
    `top: ${y}px`,
    `width: ${width}px`,
    `transform: rotate(${rotation}deg)`,
    `z-index: ${z_index}`,
    css_filter ? `filter: ${css_filter}` : "",
    blend_mode && blend_mode !== "normal" ? `mix-blend-mode: ${blend_mode}` : "",
  ].filter(Boolean).join(";");

  if (type === "image") {
    const img = document.createElement("img");
    img.className = "fragment-image";
    img.src = content;
    img.alt = "";
    img.loading = "lazy";
    img.crossOrigin = "anonymous";
    img.style.width = `${width}px`;
    img.style.height = `${layout.height ?? Math.round(width * 0.7)}px`;
    img.style.objectFit = "cover";
    img.onerror = () => wrapper.remove();
    wrapper.appendChild(img);

  } else if (type === "archive_screenshot") {
    const fig = document.createElement("figure");
    fig.className = "fragment-archive";
    fig.style.width = `${width}px`;

    const img = document.createElement("img");
    img.src = content;
    img.alt = "";
    img.loading = "lazy";
    img.crossOrigin = "anonymous";
    img.style.width = `${width}px`;
    img.style.height = `${layout.height ?? Math.round(width * 0.65)}px`;
    img.style.objectFit = "cover";
    img.onerror = () => wrapper.remove();

    const cap = document.createElement("figcaption");
    const year = (og && og.year) ? og.year : (captured_at ? captured_at.slice(0, 4) : "");
    cap.textContent = [year, source_url].filter(Boolean).join("  ");

    fig.appendChild(img);
    fig.appendChild(cap);
    wrapper.appendChild(fig);

  } else if (type === "headline") {
    const div = document.createElement("div");
    div.className = "fragment-headline";
    div.style.width = `${width}px`;
    div.textContent = content;
    wrapper.appendChild(div);

  } else if (type === "snippet") {
    const div = document.createElement("div");
    div.className = "fragment-snippet";
    div.style.width = `${width}px`;
    div.textContent = content;
    wrapper.appendChild(div);

  } else if (type === "metadata") {
    const span = document.createElement("span");
    span.className = "fragment-metadata";
    span.textContent = content;
    wrapper.appendChild(span);

  } else {
    return null;
  }

  return wrapper;
}

function onReset() {
  canvasScreen.hidden = true;
  promptScreen.hidden = false;
  canvas.innerHTML = "";
  input.value = "";
  btn.disabled = false;
  progressWrap.hidden = true;
  setProgress(0);
  setStatus("");
}

function setProgress(pct) {
  progressBar.style.width = `${pct}%`;
}

function setStatus(msg) {
  statusText.textContent = msg;
}
