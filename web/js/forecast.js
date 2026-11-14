import { ageText, arrowSvg, fmtHour, num } from "./format.js";

const MODELS = [
  { key: "hrrr", name: "HRRR", note: "hourly, high-res" },
  { key: "rrfs", name: "RRFS", note: "NOAA short-range" },
];

export function renderForecast(data) {
  const el = document.getElementById("forecast");
  const nowSec = Date.now() / 1000;
  const times = [...new Set(MODELS.flatMap((m) => data.models[m.key].points.map((p) => p.t)))].sort((a, b) => a - b);
  if (times.length === 0) {
    el.innerHTML = `<p class="muted">Forecast is not available right now.</p>`;
    return;
  }

  const header = times.map((t) => `<th>${fmtHour(t)}</th>`).join("");
  const rows = MODELS.map((m) => {
    const model = data.models[m.key];
    const byTime = new Map(model.points.map((p) => [p.t, p]));
    const cells = times
      .map((t) => {
        const p = byTime.get(t);
        if (!p) return `<td class="muted">--</td>`;
        return `<td>${num(p.speed)}<span class="g"> g${num(p.gust)}</span><br>${arrowSvg(p.dir)}</td>`;
      })
      .join("");
    const issued = model.issued_utc ? ageText(Math.floor((nowSec - model.issued_utc) / 60)) : "";
    return `<tr><td><strong>${m.name}</strong><span class="sub">${m.note}${issued ? `, run ${issued}` : ""}</span></td>${cells}</tr>`;
  }).join("");

  el.innerHTML = `<table><thead><tr><th>mph</th>${header}</tr></thead><tbody>${rows}</tbody></table>
    <p class="muted small">Model output for Sauvie Island, not measured wind. Arrows show where the wind blows toward.</p>`;
}
