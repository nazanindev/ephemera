const API = window.SCRAPEBOOK_API_URL || "http://localhost:8000";
const POLL_INTERVAL = 1500;
const ENRICH_POLL_INTERVAL = 3000;

const promptScreen = document.getElementById("prompt-screen");
const canvasScreen = document.getElementById("canvas-screen");
const canvas = document.getElementById("canvas");
const input = document.getElementById("topic-input");
const btn = document.getElementById("generate-btn");
const statusText = document.getElementById("status-text");
const resetBtn = document.getElementById("reset-btn");
const exportBtn = document.getElementById("export-btn");
const rearrangeBtn = document.getElementById("rearrange-btn");
const progressWrap = document.getElementById("progress-wrap");
const progressBar = document.getElementById("progress-bar");

let lastCollageData = null;

btn.addEventListener("click", onGenerate);
input.addEventListener("keydown", (e) => { if (e.key === "Enter") onGenerate(); });
resetBtn.addEventListener("click", onReset);
exportBtn.addEventListener("click", onExport);
rearrangeBtn.addEventListener("click", onRearrange);

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
  let phase1Done = false;

  async function tick() {
    try {
      const res = await fetch(`${API}/job/${jobId}`);
      if (!res.ok) throw new Error();
      const { status, progress } = await res.json();

      if (!phase1Done) {
        setProgress(progress);
        setStatus(progressLabel(progress));
      }

      if (status === "done" && !phase1Done) {
        phase1Done = true;
        await renderCollage(jobId);
        setTimeout(tick, ENRICH_POLL_INTERVAL);
      } else if (status === "enriched") {
        if (!phase1Done) {
          // Pipeline finished before we polled — render everything at once
          phase1Done = true;
          await renderCollage(jobId);
        } else {
          await enrichCollage(jobId);
          setStatus("");
          progressWrap.hidden = true;
        }
      } else if (status === "failed") {
        btn.disabled = false;
        setStatus("pipeline failed. try again.");
      } else if (status === "running" && phase1Done) {
        setStatus("adding more...");
        setTimeout(tick, ENRICH_POLL_INTERVAL);
      } else {
        setTimeout(tick, POLL_INTERVAL);
      }
    } catch {
      if (!phase1Done) {
        setStatus("lost connection.");
        btn.disabled = false;
      }
    }
  }

  setTimeout(tick, POLL_INTERVAL);
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

  lastCollageData = data;

  canvas.innerHTML = "";
  canvas.style.width = `${data.canvas.width}px`;
  canvas.style.height = `${data.canvas.height}px`;

  for (const frag of data.fragments) {
    const el = buildFragment(frag);
    if (el) canvas.appendChild(el);
  }

  promptScreen.hidden = true;
  canvasScreen.hidden = false;
  progressWrap.hidden = true;
  setStatus("");
}

async function enrichCollage(jobId) {
  const res = await fetch(`${API}/collage/${jobId}`);
  const data = await res.json();
  lastCollageData = data;

  const existingIds = new Set(
    [...canvas.querySelectorAll(".fragment[data-id]")].map((el) => el.dataset.id)
  );

  for (const frag of data.fragments) {
    if (existingIds.has(frag.id)) continue;
    const el = buildFragment(frag);
    if (!el) continue;
    el.classList.add("fragment--incoming");
    canvas.appendChild(el);
  }
}

function buildFragment(frag) {
  const { id, layout, type, content, source_url, og, captured_at } = frag;
  if (!layout) return null;

  const { x, y, width, rotation, z_index, css_filter, blend_mode } = layout;

  const wrapper = document.createElement("div");
  wrapper.className = "fragment";
  wrapper.dataset.id = id;
  wrapper.style.cssText = [
    `left: ${x}px`,
    `top: ${y}px`,
    `width: ${width}px`,
    `--frag-rotation: ${rotation}deg`,
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
    const origDomain = (og && og.original_url) ? new URL(og.original_url).hostname.replace(/^www\./, "") : "";
    cap.textContent = [year, origDomain].filter(Boolean).join(" · ");

    fig.appendChild(img);
    fig.appendChild(cap);
    wrapper.appendChild(fig);

  } else if (type === "headline") {
    const div = document.createElement("div");
    div.className = "fragment-headline";
    div.style.width = `${width}px`;
    if (layout.text_color) {
      div.style.color = layout.text_color;
      if (layout.text_color === "#ffffff" || layout.text_color === "#f0e6d3") {
        div.style.textShadow = "0 1px 3px rgba(0,0,0,0.6)";
      }
    }
    div.textContent = content;
    wrapper.appendChild(div);

  } else if (type === "snippet") {
    const div = document.createElement("div");
    div.className = "fragment-snippet";
    div.style.width = `${width}px`;
    if (layout.text_color) {
      div.style.color = layout.text_color;
      if (layout.text_color === "#ffffff" || layout.text_color === "#f0e6d3") {
        div.style.textShadow = "0 1px 2px rgba(0,0,0,0.5)";
      }
    }
    div.textContent = content;
    wrapper.appendChild(div);

  } else if (type === "metadata") {
    const span = document.createElement("span");
    span.className = "fragment-metadata";
    if (layout.text_color) span.style.color = layout.text_color;
    span.textContent = content;
    wrapper.appendChild(span);

  } else {
    return null;
  }

  return wrapper;
}

function onRearrange() {
  if (!lastCollageData) return;
  rearrangeBtn.disabled = true;

  const cw = lastCollageData.canvas.width;
  const ch = lastCollageData.canvas.height;

  const reshuffled = {
    ...lastCollageData,
    fragments: lastCollageData.fragments.map((frag) => {
      if (!frag.layout) return frag;
      const w = frag.layout.width;
      const h = frag.layout.height ?? Math.round(w * 0.7);
      const maxX = Math.max(0, cw - w);
      const maxY = Math.max(0, ch - h);
      return {
        ...frag,
        layout: {
          ...frag.layout,
          x: Math.round(Math.random() * maxX),
          y: Math.round(Math.random() * maxY),
          rotation: (Math.random() * 16 - 8).toFixed(2) * 1,
          z_index: Math.floor(Math.random() * 20) + 1,
        },
      };
    }),
  };

  lastCollageData = reshuffled;
  canvas.innerHTML = "";

  for (const frag of reshuffled.fragments) {
    const el = buildFragment(frag);
    if (el) {
      el.classList.add("fragment--incoming");
      canvas.appendChild(el);
    }
  }

  setTimeout(() => { rearrangeBtn.disabled = false; }, 600);
}

function onReset() {
  canvasScreen.hidden = true;
  promptScreen.hidden = false;
  canvas.innerHTML = "";
  input.value = "";
  btn.disabled = false;
  progressWrap.hidden = true;
  lastCollageData = null;
  setProgress(0);
  setStatus("");
}

async function onExport() {
  exportBtn.disabled = true;
  exportBtn.textContent = "rendering...";
  try {
    const canvasEl = await html2canvas(canvas, {
      backgroundColor: getComputedStyle(document.documentElement).getPropertyValue("--bg").trim() || "#ede5d8",
      useCORS: true,
      allowTaint: false,
      scale: 1,
      width: canvas.offsetWidth,
      height: canvas.offsetHeight,
    });
    const topic = (input.value.trim() || "scrapebook").replace(/\s+/g, "-").toLowerCase();
    const link = document.createElement("a");
    link.download = `${topic}.png`;
    link.href = canvasEl.toDataURL("image/png");
    link.click();
  } catch (err) {
    console.error("export failed", err);
  } finally {
    exportBtn.disabled = false;
    exportBtn.textContent = "↓ save png";
  }
}

function setProgress(pct) {
  progressBar.style.width = `${pct}%`;
}

function setStatus(msg) {
  statusText.textContent = msg;
}
