import { api } from "./api.js";
import { fmtTime, pacificDay } from "./format.js";
import { renderBanners, renderHero, renderRiver, renderWaterTemp } from "./hero.js";
import { renderForecast } from "./forecast.js";
import { initTheme } from "./theme.js";
import { createChart, retheme, updateChart } from "./windchart.js";

const $ = (id) => document.getElementById(id);
const DAY_RE = /^\d{4}-\d{2}-\d{2}$/;

const params = new URLSearchParams(location.search);
const state = {
  hours: 6,
  date: DAY_RE.test(params.get("date") || "") ? params.get("date") : null, // null = live
  firstDate: null,
};
const savedOverlays = JSON.parse(localStorage.getItem("overlays") || "{}");

let chart;

function addDays(day, n) {
  const d = new Date(`${day}T12:00:00Z`); // noon UTC avoids any DST edge
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

function windowParam() {
  return state.date ? { date: state.date } : { hours: state.hours };
}

function syncControls() {
  const today = pacificDay();
  const day = state.date || today;
  document.querySelectorAll("#hours-buttons button").forEach((b) => {
    b.setAttribute("aria-pressed", String(!state.date && Number(b.dataset.hours) === state.hours));
  });
  const input = $("day");
  input.value = day;
  input.max = today;
  if (state.firstDate) input.min = state.firstDate;
  $("next-day").disabled = day >= today;
  $("prev-day").disabled = !!state.firstDate && day <= state.firstDate;
  $("live-btn").hidden = !state.date;
  const url = new URL(location.href);
  if (state.date) url.searchParams.set("date", state.date);
  else url.searchParams.delete("date");
  history.replaceState(null, "", url);
}

async function refreshCurrent() {
  try {
    const [status, current] = await Promise.all([api.status(), api.current()]);
    renderBanners(status);
    renderHero(current);
    renderRiver(current);
    renderWaterTemp(current);
  } catch (err) {
    console.error(err);
  }
}

async function refreshChart() {
  const stations = ["annie"];
  if ($("ov-st_helens_model").checked) stations.push("st_helens_model");
  if ($("ov-kspb").checked) stations.push("kspb");
  if ($("ov-kkls").checked) stations.push("kkls");
  try {
    const [series, tides] = await Promise.all([api.series(windowParam(), stations), api.tides(windowParam())]);
    $("chart-empty").hidden = series.stations.annie.t.length > 0;
    updateChart(chart, series, tides.events);
  } catch (err) {
    console.error(err);
  }
}

async function refreshForecast() {
  try {
    renderForecast(await api.forecast());
  } catch (err) {
    console.error(err);
    $("forecast").innerHTML = `<p class="muted">Forecast is not available right now.</p>`;
  }
}

async function refreshTidesToday() {
  try {
    const data = await api.tides({ date: pacificDay() });
    const rows = data.events
      .filter((e) => e.t >= data.start && e.t < data.end)
      .map((e) => `<tr><td>${e.kind === "H" ? "High" : "Low"}</td><td>${fmtTime(e.t)}</td><td>${e.height.toFixed(1)} ft</td></tr>`)
      .join("");
    $("tides").innerHTML = rows ? `<table>${rows}</table>` : `<p class="muted">No tide data.</p>`;
  } catch (err) {
    console.error(err);
  }
}

function setDate(day) {
  state.date = day;
  syncControls();
  refreshChart();
}

function wireControls() {
  document.querySelectorAll("#hours-buttons button").forEach((b) =>
    b.addEventListener("click", () => {
      state.hours = Number(b.dataset.hours);
      state.date = null;
      syncControls();
      refreshChart();
    }),
  );
  $("day").addEventListener("change", (e) => {
    if (DAY_RE.test(e.target.value)) setDate(e.target.value === pacificDay() ? null : e.target.value);
  });
  $("prev-day").addEventListener("click", () => setDate(addDays(state.date || pacificDay(), -1)));
  $("next-day").addEventListener("click", () => {
    const next = addDays(state.date || pacificDay(), 1);
    setDate(next >= pacificDay() ? null : next);
  });
  $("live-btn").addEventListener("click", () => setDate(null));

  for (const key of ["st_helens_model", "kspb", "kkls"]) {
    const box = $(`ov-${key}`);
    box.checked = !!savedOverlays[key];
    box.addEventListener("change", () => {
      savedOverlays[key] = box.checked;
      localStorage.setItem("overlays", JSON.stringify(savedOverlays));
      refreshChart();
    });
  }
}

async function start() {
  initTheme(() => retheme(chart));
  chart = createChart($("wind-chart"));
  wireControls();
  syncControls();

  api.firstDate().then((d) => {
    state.firstDate = d.first_date;
    syncControls();
  }).catch(console.error);

  await Promise.all([refreshCurrent(), refreshChart(), refreshForecast(), refreshTidesToday()]);

  setInterval(refreshCurrent, 60e3);
  setInterval(() => { if (!state.date) refreshChart(); }, 300e3);
  setInterval(refreshForecast, 600e3);
  setInterval(refreshTidesToday, 1800e3);
  setInterval(() => { $("cam-preview").src = `/roostercam?t=${Date.now()}`; }, 120e3);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) { refreshCurrent(); if (!state.date) refreshChart(); }
  });
}

start();
