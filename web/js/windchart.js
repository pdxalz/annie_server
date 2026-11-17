import { compass, fmtHour, fmtTime, pacificOffsetMs } from "./format.js";

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const isCompact = () => window.matchMedia("(max-width: 640px), (hover: none)").matches;

const OVERLAYS = {
  st_helens_model: { label: "St. Helens (Model)", color: "rgba(23, 162, 184, 0.52)", dash: [5, 4] },
  kspb: { label: "Scappoose (KSPB)", color: "rgba(217, 130, 43, 0.52)", dash: [8, 4] },
  kkls: { label: "Longview (KKLS)", color: "rgba(155, 89, 182, 0.52)", dash: [3, 3] },
};

/** Convert a column series into chart points, skipping missing values so lines connect. */
function toPoints(series, field, withDir = false) {
  const pts = [];
  for (let i = 0; i < series.t.length; i++) {
    const y = series[field][i];
    if (y == null) continue;
    const p = { x: series.t[i] * 1000, y };
    if (withDir) p.d = series.dir[i];
    pts.push(p);
  }
  return pts;
}

/** Wind-direction arrows along the top of the plot. They point where the wind blows toward. */
const arrowsPlugin = {
  id: "windArrows",
  afterDatasetsDraw(chart) {
    const dirs = chart.$dirs;
    if (!dirs || !dirs.length) return;
    const { ctx, chartArea, scales } = chart;
    ctx.save();
    ctx.strokeStyle = css("--text");
    ctx.lineWidth = 1.7;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    let lastX = -Infinity;
    for (const d of dirs) {
      const px = scales.x.getPixelForValue(d.x);
      if (px < chartArea.left + 8 || px > chartArea.right - 8 || px - lastX < 34) continue;
      lastX = px;
      ctx.save();
      ctx.translate(px, chartArea.top - 17);
      ctx.rotate((((d.dir + 180) % 360) * Math.PI) / 180);
      ctx.beginPath();
      ctx.moveTo(0, 9);
      ctx.lineTo(0, -9);
      ctx.moveTo(-4.5, -3.5);
      ctx.lineTo(0, -9);
      ctx.lineTo(4.5, -3.5);
      ctx.stroke();
      ctx.restore();
    }
    ctx.restore();
  },
};

/** Flood/ebb shading with High/Low markers. Low->High is flood (rising), High->Low is ebb. */
const tidePlugin = {
  id: "tideBands",
  beforeDatasetsDraw(chart) {
    const ev = chart.$tides;
    if (!ev || ev.length < 2) return;
    const { ctx, chartArea, scales } = chart;
    ctx.save();
    for (let i = 0; i < ev.length - 1; i++) {
      const x0 = Math.max(scales.x.getPixelForValue(ev[i].t * 1000), chartArea.left);
      const x1 = Math.min(scales.x.getPixelForValue(ev[i + 1].t * 1000), chartArea.right);
      if (x1 <= x0) continue;
      ctx.fillStyle = ev[i].kind === "L" ? css("--flood") : css("--ebb");
      ctx.fillRect(x0, chartArea.top, x1 - x0, chartArea.bottom - chartArea.top);
    }
    ctx.restore();
  },
  afterDatasetsDraw(chart) {
    const ev = chart.$tides;
    if (!ev) return;
    const { ctx, chartArea, scales } = chart;
    ctx.save();
    ctx.font = "11px system-ui, sans-serif";
    ctx.fillStyle = css("--muted");
    ctx.strokeStyle = css("--muted");
    ctx.setLineDash([3, 4]);
    ctx.textAlign = "center";
    for (const e of ev) {
      const px = scales.x.getPixelForValue(e.t * 1000);
      if (px < chartArea.left || px > chartArea.right) continue;
      ctx.beginPath();
      ctx.moveTo(px, chartArea.top);
      ctx.lineTo(px, chartArea.bottom);
      ctx.stroke();
      const label = `${e.kind === "H" ? "High" : "Low"} ${fmtTime(e.t)}`;
      const half = ctx.measureText(label).width / 2 + 2;
      ctx.fillText(label, Math.min(Math.max(px, chartArea.left + half), chartArea.right - half), chartArea.bottom - 5);
    }
    ctx.restore();
  },
};

function applyTheme(chart) {
  const text = css("--muted");
  const grid = css("--border");
  chart.options.scales.x.ticks.color = text;
  chart.options.scales.x.grid.color = grid;
  chart.options.scales.y.ticks.color = text;
  chart.options.scales.y.grid.color = grid;
  chart.options.scales.y.title.color = text;
  chart.options.plugins.legend.labels.color = css("--text");
}

function clearTooltip(chart) {
  chart.setActiveElements([]);
  chart.tooltip.setActiveElements([], { x: 0, y: 0 });
  chart.update("none");
  const readout = document.getElementById("chart-readout");
  if (readout) readout.hidden = true;
}

function renderExternalReadout(context) {
  const readout = document.getElementById("chart-readout");
  const textEl = document.getElementById("chart-readout-text");
  if (!readout || !textEl) return;
  const { tooltip } = context;
  if (!isCompact() || tooltip.opacity === 0 || !tooltip.dataPoints || !tooltip.dataPoints.length) {
    readout.hidden = true;
    return;
  }
  textEl.textContent = "";
  const timeEl = document.createElement("strong");
  timeEl.textContent = fmtTime(tooltip.dataPoints[0].parsed.x / 1000);
  textEl.appendChild(timeEl);
  for (const item of tooltip.dataPoints) {
    const span = document.createElement("span");
    span.className = "chart-readout-item";
    const swatch = document.createElement("span");
    swatch.className = "chart-readout-swatch";
    swatch.style.backgroundColor = item.dataset.borderColor;
    const dir = item.raw && item.raw.d != null ? ` ${compass(item.raw.d)}` : "";
    span.appendChild(swatch);
    span.appendChild(document.createTextNode(`${item.dataset.label} ${item.parsed.y} mph${dir}`));
    textEl.appendChild(span);
  }
  readout.hidden = false;
}

export function createChart(canvas) {
  const chart = new Chart(canvas, {
    type: "line",
    data: { datasets: [] },
    plugins: [tidePlugin, arrowsPlugin],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      spanGaps: true,
      parsing: false,
      normalized: true,
      layout: { padding: { top: 36 } },
      interaction: { mode: "nearest", axis: "x", intersect: false },
      scales: {
        x: {
          type: "linear",
          grid: {},
          ticks: { maxRotation: 0, callback: (v) => fmtHour(v / 1000) },
          afterBuildTicks(scale) {
            const step = (scale.chart.$stepHours || 1) * 3600e3;
            const off = pacificOffsetMs(scale.min);
            const ticks = [];
            for (let t = Math.ceil((scale.min + off) / step) * step - off; t <= scale.max; t += step) {
              ticks.push({ value: t });
            }
            scale.ticks = ticks;
          },
        },
        y: { min: 0, suggestedMax: 25, grid: {}, ticks: {}, title: { display: true, text: "mph" } },
      },
      plugins: {
        legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 8 } },
        tooltip: {
          enabled: !isCompact(),
          external: renderExternalReadout,
          callbacks: {
            title: (items) => (items.length ? fmtTime(items[0].parsed.x / 1000) : ""),
            label: (item) => {
              const dir = item.raw && item.raw.d != null ? `  from ${compass(item.raw.d)}` : "";
              return `${item.dataset.label}: ${item.parsed.y} mph${dir}`;
            },
          },
        },
      },
    },
  });
  applyTheme(chart);

  const readout = document.getElementById("chart-readout");
  const closeBtn = document.getElementById("chart-readout-close");
  if (closeBtn) closeBtn.addEventListener("click", () => clearTooltip(chart));
  document.addEventListener("pointerdown", (e) => {
    if (e.target !== canvas && (!readout || !readout.contains(e.target))) {
      clearTooltip(chart);
    }
  });
  window.addEventListener("resize", () => {
    const enabled = !isCompact();
    if (chart.options.plugins.tooltip.enabled !== enabled) {
      chart.options.plugins.tooltip.enabled = enabled;
      clearTooltip(chart);
    }
  });

  return chart;
}

export function retheme(chart) {
  applyTheme(chart);
  chart.update();
}

/**
 * @param chart   Chart.js instance
 * @param data    { start, end, stations: {annie:{t,speed,gust,lull,dir}, kspb:..., kkls:...} }
 * @param tides   array of {t, kind}
 */
export function updateChart(chart, data, tides) {
  const annie = data.stations.annie;
  const datasets = [
    { label: "Wind", data: toPoints(annie, "speed", true), borderColor: css("--speed"), backgroundColor: css("--speed"), borderWidth: 3, pointRadius: 0, pointHoverRadius: 4, tension: 0.25, cubicInterpolationMode: "monotone" },
    { label: "Gust", data: toPoints(annie, "gust"), borderColor: css("--gust"), backgroundColor: css("--gust"), borderWidth: 1.6, pointRadius: 0, pointHoverRadius: 4, tension: 0.25, cubicInterpolationMode: "monotone" },
    { label: "Lull", data: toPoints(annie, "lull"), borderColor: css("--lull"), backgroundColor: css("--lull"), borderWidth: 1.2, pointRadius: 0, pointHoverRadius: 4, tension: 0.25, cubicInterpolationMode: "monotone" },
  ];
  for (const [key, meta] of Object.entries(OVERLAYS)) {
    const s = data.stations[key];
    if (!s) continue;
    datasets.push({
      label: meta.label,
      data: toPoints(s, "speed"),
      borderColor: meta.color,
      backgroundColor: meta.color,
      borderWidth: 1.6,
      borderDash: meta.dash,
      pointRadius: 0,
      pointHoverRadius: 4,
      tension: 0.2,
      cubicInterpolationMode: "monotone",
    });
  }

  const hoursSpan = (data.end - data.start) / 3600;
  chart.$stepHours = hoursSpan <= 4 ? 0.5 : hoursSpan <= 7 ? 1 : hoursSpan <= 13 ? 2 : 3;
  chart.$tides = tides;
  chart.$dirs = annie.t.map((t, i) => ({ x: t * 1000, dir: annie.dir[i] })).filter((d) => d.dir != null);
  chart.data.datasets = datasets;
  chart.options.scales.x.min = data.start * 1000;
  chart.options.scales.x.max = data.end * 1000;
  chart.update();
}
