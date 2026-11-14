import { compass, fmtHour, fmtTime, pacificOffsetMs } from "./format.js";

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const GAP_SEC = 45 * 60; // break the line if a sensor goes quiet for this long

const OVERLAYS = {
  kspb: { label: "St. Helens", color: "#e8890c" },
  kkls: { label: "Longview", color: "#9b59b6" },
};

/** Convert a column series into chart points, inserting a null point at gaps so lines break. */
function toPoints(series, field, withDir = false) {
  const pts = [];
  for (let i = 0; i < series.t.length; i++) {
    if (i > 0 && series.t[i] - series.t[i - 1] > GAP_SEC) {
      pts.push({ x: ((series.t[i] + series.t[i - 1]) / 2) * 1000, y: null });
    }
    const p = { x: series.t[i] * 1000, y: series[field][i] };
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

export function createChart(canvas) {
  const chart = new Chart(canvas, {
    type: "line",
    data: { datasets: [] },
    plugins: [tidePlugin, arrowsPlugin],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
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
    { label: "Wind", data: toPoints(annie, "speed", true), borderColor: css("--speed"), backgroundColor: css("--speed"), borderWidth: 3, pointRadius: 0, pointHoverRadius: 4, tension: 0.25 },
    { label: "Gust", data: toPoints(annie, "gust"), borderColor: css("--gust"), backgroundColor: css("--gust"), borderWidth: 1.6, pointRadius: 0, pointHoverRadius: 4, tension: 0.25 },
    { label: "Lull", data: toPoints(annie, "lull"), borderColor: css("--lull"), backgroundColor: css("--lull"), borderWidth: 1.2, borderDash: [4, 3], pointRadius: 0, pointHoverRadius: 4, tension: 0.25 },
  ];
  for (const [key, meta] of Object.entries(OVERLAYS)) {
    const s = data.stations[key];
    if (!s) continue;
    datasets.push({ label: meta.label, data: toPoints(s, "speed"), borderColor: meta.color, backgroundColor: meta.color, borderWidth: 2, pointRadius: 3, pointHoverRadius: 5, tension: 0.2 });
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
