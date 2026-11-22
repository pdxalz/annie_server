const $ = (id) => document.getElementById(id);

const fmtStamp = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/Los_Angeles",
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

const PLAY_INTERVAL_MS = 350;
const POLL_INTERVAL_MS = 30_000;

let frames = [];
let idx = 0;
let playTimer = null;

function isLiveIndex() {
  return frames.length > 0 && idx === frames.length - 1;
}

function stopPlay() {
  if (playTimer !== null) {
    clearInterval(playTimer);
    playTimer = null;
  }
  const btn = $("play-btn");
  btn.textContent = "\u25B6";
  btn.setAttribute("aria-label", "Play timelapse");
  btn.title = "Play timelapse";
}

function startPlay() {
  if (frames.length < 2) return;
  if (idx >= frames.length - 1) idx = 0;
  renderFrame();
  const btn = $("play-btn");
  btn.textContent = "\u23F8";
  btn.setAttribute("aria-label", "Pause timelapse");
  btn.title = "Pause timelapse";
  playTimer = setInterval(() => {
    idx = (idx + 1) % frames.length;
    renderFrame();
  }, PLAY_INTERVAL_MS);
}

function preload(i) {
  if (i >= 0 && i < frames.length) {
    const img = new Image();
    img.src = frames[i].url;
  }
}

function renderFrame() {
  const cam = $("cam");
  const badge = $("frame-badge");
  const timeEl = $("frame-time");
  const scrubber = $("scrubber");
  const prevBtn = $("prev-btn");
  const nextBtn = $("next-btn");
  const playBtn = $("play-btn");
  const liveBtn = $("live-btn");

  if (!frames.length) {
    cam.src = `/roostercam?t=${Date.now()}`;
    badge.textContent = "LIVE";
    badge.className = "badge live";
    timeEl.textContent = "Live camera";
    scrubber.disabled = true;
    prevBtn.disabled = true;
    nextBtn.disabled = true;
    playBtn.disabled = true;
    liveBtn.disabled = true;
    liveBtn.classList.remove("primary");
    return;
  }

  idx = Math.max(0, Math.min(idx, frames.length - 1));
  const f = frames[idx];
  if (cam.dataset.frameId !== f.id) {
    cam.src = f.url;
    cam.dataset.frameId = f.id;
  }

  const live = isLiveIndex();
  badge.textContent = live ? "LIVE" : `${idx + 1} / ${frames.length}`;
  badge.className = live ? "badge live" : "badge";
  timeEl.textContent = fmtStamp.format(new Date(f.t * 1000));

  scrubber.min = "0";
  scrubber.max = String(frames.length - 1);
  scrubber.value = String(idx);
  scrubber.disabled = frames.length < 2;

  prevBtn.disabled = idx <= 0;
  nextBtn.disabled = idx >= frames.length - 1;
  playBtn.disabled = frames.length < 2;
  liveBtn.disabled = live;
  liveBtn.classList.toggle("primary", !live);

  preload(idx + 1);
  if (idx > 0) preload(idx - 1);
}

async function fetchFrames(initial = false) {
  const wasLive = initial || isLiveIndex();
  const currentId = frames[idx]?.id;
  try {
    const res = await fetch("/api/v1/roostercam/frames", { cache: "no-store" });
    if (!res.ok) throw new Error(`${res.status}`);
    const data = await res.json();
    frames = data.frames || [];
    if (!frames.length) {
      idx = 0;
    } else if (wasLive && playTimer === null) {
      idx = frames.length - 1;
    } else if (currentId) {
      const found = frames.findIndex((f) => f.id === currentId);
      idx = found >= 0 ? found : frames.length - 1;
    }
    renderFrame();
  } catch (err) {
    console.error(err);
    if (initial) renderFrame();
  }
}

$("prev-btn").addEventListener("click", () => {
  stopPlay();
  if (idx > 0) {
    idx -= 1;
    renderFrame();
  }
});

$("next-btn").addEventListener("click", () => {
  stopPlay();
  if (idx < frames.length - 1) {
    idx += 1;
    renderFrame();
  }
});

$("play-btn").addEventListener("click", () => {
  if (playTimer !== null) stopPlay();
  else startPlay();
});

$("scrubber").addEventListener("input", (e) => {
  stopPlay();
  idx = Number(e.target.value);
  renderFrame();
});

$("live-btn").addEventListener("click", () => {
  stopPlay();
  if (frames.length) {
    idx = frames.length - 1;
    renderFrame();
  }
});

// Fullscreen toggle (hide gracefully on browsers like iOS Safari that lack the API)
const fsBtn = $("fs-btn");
const stage = $("stage");
if (!stage.requestFullscreen) {
  fsBtn.hidden = true;
} else {
  fsBtn.addEventListener("click", () => {
    if (document.fullscreenElement) document.exitFullscreen();
    else stage.requestFullscreen().catch(() => {});
  });
}

fetchFrames(true);
setInterval(() => fetchFrames(false), POLL_INTERVAL_MS);
