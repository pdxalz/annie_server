import { fmtHour, fmtTime, pacificOffsetMs } from "./format.js";
import { initTheme } from "./theme.js";

const $ = (id) => document.getElementById(id);
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const fmtDay = new Intl.DateTimeFormat("en-US", { timeZone: "America/Los_Angeles", month: "numeric", day: "numeric" });

let healthHours = 24;
let healthChart;

function fmtBytes(bytes) {
  if (bytes == null) return "--";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let val = Number(bytes);
  let i = 0;
  while (val >= 1024 && i < units.length - 1) {
    val /= 1024;
    i++;
  }
  return `${val.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function fmtDuration(sec) {
  if (sec == null) return "--";
  const d = Math.floor(sec / 86400);
  const h = Math.floor((sec % 86400) / 3600);
  const m = Math.floor((sec % 3600) / 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function fmtAge(tsUtc) {
  if (!tsUtc) return "Never";
  const mins = Math.max(0, Math.floor((Date.now() / 1000 - tsUtc) / 60));
  if (mins < 60) return `${mins}m ago (${fmtTime(tsUtc)})`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 48) return `${hrs}h ${mins % 60}m ago (${fmtTime(tsUtc)})`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function statBox(label, value, sub = "") {
  return `<div class="stat-box"><div class="stat-label">${label}</div><div class="stat-val">${value}</div>${sub ? `<div class="stat-sub">${sub}</div>` : ""}</div>`;
}

function createHealthChart(canvas) {
  return new Chart(canvas, {
    type: "line",
    data: { datasets: [] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      spanGaps: true,
      parsing: false,
      interaction: { mode: "nearest", axis: "x", intersect: false },
      scales: {
        x: {
          type: "linear",
          grid: { color: css("--border") },
          ticks: {
            color: css("--muted"),
            maxRotation: 0,
            callback: (v) => (healthHours > 24 ? fmtDay.format(new Date(v)) : fmtHour(v / 1000)),
          },
          afterBuildTicks(scale) {
            const step = (healthHours > 24 ? 24 : 3) * 3600e3;
            const off = pacificOffsetMs(scale.min);
            const ticks = [];
            for (let t = Math.ceil((scale.min + off) / step) * step - off; t <= scale.max; t += step) {
              ticks.push({ value: t });
            }
            scale.ticks = ticks;
          },
        },
        yMv: {
          type: "linear",
          position: "left",
          suggestedMin: 3400,
          suggestedMax: 4300,
          grid: { color: css("--border") },
          ticks: { color: css("--speed") },
          title: { display: true, text: "Battery (mV)", color: css("--speed") },
        },
        yTemp: {
          type: "linear",
          position: "right",
          grid: { drawOnChartArea: false },
          ticks: { color: css("--gust") },
          title: { display: true, text: "Temp (°F)", color: css("--gust") },
        },
      },
      plugins: {
        legend: { position: "bottom", labels: { color: css("--text"), usePointStyle: true, boxWidth: 8 } },
        tooltip: {
          callbacks: {
            title: (items) => (items.length ? fmtTime(items[0].parsed.x / 1000) : ""),
            label: (item) => `${item.dataset.label}: ${item.parsed.y}${item.dataset.yAxisID === "yMv" ? " mV" : " °F"}`,
          },
        },
      },
    },
  });
}

function rethemeChart() {
  if (!healthChart) return;
  healthChart.options.scales.x.grid.color = css("--border");
  healthChart.options.scales.x.ticks.color = css("--muted");
  healthChart.options.scales.yMv.grid.color = css("--border");
  healthChart.options.scales.yMv.ticks.color = css("--speed");
  healthChart.options.scales.yMv.title.color = css("--speed");
  healthChart.options.scales.yTemp.ticks.color = css("--gust");
  healthChart.options.scales.yTemp.title.color = css("--gust");
  healthChart.options.plugins.legend.labels.color = css("--text");
  healthChart.update();
}

function renderSensorHealth(data) {
  const latest = data.sensor_health.latest;
  const lastWind = data.server.last_updates_utc.annie_wind;
  if (latest) {
    $("sensor-stats").innerHTML = [
      statBox("Battery", `${latest.volts.toFixed(2)} V`, `${latest.mv} mV`),
      statBox("Enclosure Temp", `${latest.temp_f.toFixed(1)} °F`, fmtTime(latest.ts_utc)),
      statBox("Last Health Msg", fmtAge(latest.ts_utc)),
      statBox("Last Wind Msg", fmtAge(lastWind)),
    ].join("");
  } else {
    $("sensor-stats").innerHTML = [
      statBox("Battery", "--", "Waiting for zimbuktu/health"),
      statBox("Enclosure Temp", "--"),
      statBox("Last Wind Msg", fmtAge(lastWind)),
    ].join("");
  }

  const s = data.sensor_health.series;
  $("health-empty").hidden = s.t.length > 0;
  const nowMs = Date.now();
  healthChart.options.scales.x.min = nowMs - healthHours * 3600e3;
  healthChart.options.scales.x.max = nowMs;
  healthChart.data.datasets = [
    {
      label: "Battery (mV)",
      yAxisID: "yMv",
      data: s.t.map((t, i) => ({ x: t * 1000, y: s.mv[i] })),
      borderColor: css("--speed"),
      backgroundColor: css("--speed"),
      borderWidth: 2.2,
      pointRadius: 0,
      pointHoverRadius: 4,
      tension: 0.2,
    },
    {
      label: "Temp (°F)",
      yAxisID: "yTemp",
      data: s.t.map((t, i) => ({ x: t * 1000, y: s.temp_f[i] })),
      borderColor: css("--gust"),
      backgroundColor: css("--gust"),
      borderWidth: 1.8,
      pointRadius: 0,
      pointHoverRadius: 4,
      tension: 0.2,
    },
  ];
  healthChart.update();
}

function renderHits(hits) {
  $("hits-stats").innerHTML = [
    statBox("Today Total", hits.today.total ?? 0, hits.today_day),
    statBox("Today /", hits.today["/"] ?? 0, "Main page"),
    statBox("Today RoosterCam", hits.today["/roostercam.php"] ?? 0, "/roostercam.php"),
    statBox("All-Time Total", hits.all_time.total ?? 0, `/ ${hits.all_time["/"] ?? 0} · cam ${hits.all_time["/roostercam.php"] ?? 0}`),
  ].join("");

  if (!hits.daily.length) {
    $("hits-table").innerHTML = `<tr><td class="muted">No page hits recorded yet.</td></tr>`;
    return;
  }
  const rows = hits.daily
    .map((d) => `<tr><td>${d.day}</td><td>${d.total ?? 0}</td><td>${d["/"] ?? 0}</td><td>${d["/roostercam.php"] ?? 0}</td></tr>`)
    .join("");
  $("hits-table").innerHTML = `<thead><tr><th>Date</th><th>Total</th><th>/</th><th>/roostercam.php</th></tr></thead><tbody>${rows}</tbody>`;
}

function renderServer(srv) {
  const pct = srv.disk.total_bytes ? Math.round((srv.disk.used_bytes / srv.disk.total_bytes) * 100) : 0;
  const camStr = srv.roostercam.exists
    ? `${fmtBytes(srv.roostercam.size_bytes)} · ${fmtAge(srv.roostercam.mtime_utc)}`
    : "Missing";
  $("server-stats").innerHTML = `
    <div class="disk-bar-wrap">
      <div class="small"><strong>Disk:</strong> ${fmtBytes(srv.disk.free_bytes)} free of ${fmtBytes(srv.disk.total_bytes)} (${pct}% used)</div>
      <div class="disk-bar"><div class="disk-bar-fill" style="width:${pct}%"></div></div>
    </div>
    <table class="status-table">
      <tr><td>Uptime</td><td>${fmtDuration(srv.uptime_seconds)}</td></tr>
      <tr><td>SQLite DB</td><td>${fmtBytes(srv.db_bytes)}</td></tr>
      <tr><td>RoosterCam</td><td>${camStr}</td></tr>
      <tr><td>Observations</td><td>${srv.counts.observations.toLocaleString()}</td></tr>
      <tr><td>Forecasts</td><td>${srv.counts.forecasts.toLocaleString()}</td></tr>
      <tr><td>Tide Events</td><td>${srv.counts.tide_events.toLocaleString()}</td></tr>
      <tr><td>Health Rows</td><td>${srv.counts.sensor_health.toLocaleString()}</td></tr>
    </table>
  `;

  const u = srv.last_updates_utc;
  $("freshness-stats").innerHTML = `
    <table class="status-table">
      <tr><td>Sauvie Wind (Annie)</td><td>${fmtAge(u.annie_wind)}</td></tr>
      <tr><td>Sauvie Health (Annie)</td><td>${fmtAge(u.annie_health)}</td></tr>
      <tr><td>Scappoose (KSPB)</td><td>${fmtAge(u.kspb)}</td></tr>
      <tr><td>St. Helens (Model)</td><td>${fmtAge(u.st_helens_model)}</td></tr>
      <tr><td>Longview (KKLS)</td><td>${fmtAge(u.kkls)}</td></tr>
      <tr><td>Forecasts</td><td>${fmtAge(u.forecast)}</td></tr>
    </table>
  `;
}

async function refresh() {
  try {
    const res = await fetch(`/api/v1/system_status?hours=${healthHours}`);
    if (!res.ok) throw new Error(`${res.status}`);
    const data = await res.json();
    renderSensorHealth(data);
    renderHits(data.hits);
    renderServer(data.server);
  } catch (err) {
    console.error(err);
  }
}

initTheme(rethemeChart);
healthChart = createHealthChart($("health-chart"));
document.querySelectorAll("#health-hours button").forEach((b) =>
  b.addEventListener("click", () => {
    healthHours = Number(b.dataset.hours);
    document.querySelectorAll("#health-hours button").forEach((btn) =>
      btn.setAttribute("aria-pressed", String(btn === b)),
    );
    refresh();
  }),
);
refresh();
setInterval(refresh, 60_000);
