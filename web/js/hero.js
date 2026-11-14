import { ageText, arrowSvg, compass, fmtTime, num } from "./format.js";

export function renderBanners(status) {
  const banner = document.getElementById("banner");
  const b = status.banner;
  if (b.enabled) {
    banner.className = `banner banner-${b.level}`;
    banner.textContent = b.message; // textContent: the message comes from a file, never inject as HTML
    banner.hidden = false;
  } else {
    banner.hidden = true;
  }

  // Automatic notice for outages nobody announced. Hidden when a manual banner is already up.
  const offline = document.getElementById("offline");
  const s = status.sensor;
  if (s.offline && !b.enabled) {
    offline.textContent = s.last_reading_utc
      ? `Annie is offline. Last reading ${ageText(s.age_minutes)}.`
      : "Annie has not reported any data yet.";
    offline.hidden = false;
  } else {
    offline.hidden = true;
  }
}

export function renderHero(current) {
  const hero = document.getElementById("hero");
  const a = current.stations.annie;
  if (!a || !a.available) {
    hero.className = "card hero stale";
    hero.innerHTML = `<div><p class="label">Sauvie Island</p><p class="muted">No wind data yet.</p></div>`;
    return;
  }
  hero.className = `card hero${a.stale ? " stale" : ""}`;
  hero.innerHTML = `
    <div>
      <div class="readout">
        <div><div class="label">Wind</div><span class="speed">${num(a.speed)}</span></div>
        <div><div class="label">Gust</div><span class="gust">${num(a.gust)}</span></div>
        <span class="unit">mph</span>
      </div>
      <div class="secondary">Lull <strong>${num(a.lull)}</strong> mph
        <span class="muted"> &middot; ${fmtTime(a.ts_utc)} (${ageText(a.age_minutes)})</span></div>
    </div>
    <div class="compass" style="color:var(--accent)">
      <svg viewBox="-50 -50 100 100" aria-hidden="true">
        <circle class="ring" r="44"/>
        <text class="north" y="-33">N</text>
        <g transform="rotate(${(((a.dir ?? 0) + 180) % 360)})">
          <path class="needle" d="M0 -30 L9 14 L0 8 L-9 14 Z"/>
        </g>
      </svg>
      <div class="dirtext" style="color:var(--text)">${a.dir == null ? "--" : `from ${compass(a.dir)} ${a.dir}&deg;`}</div>
    </div>`;
}

export function renderRiver(current) {
  const el = document.getElementById("river");
  // Upriver sensors first, so you read left to right in the direction a sea breeze travels.
  const order = ["kkls", "kspb", "annie"];
  el.innerHTML = order
    .map((key) => {
      const s = current.stations[key];
      if (!s || !s.available) {
        return `<div class="stn stale"><div class="name">${s?.label ?? key}</div><div class="vals">--</div></div>`;
      }
      const gust = s.gust != null ? ` <span class="g">g${num(s.gust)}</span>` : "";
      return `<div class="stn${s.stale ? " stale" : ""}">
        <div class="name">${s.label}</div>
        <div class="vals">${num(s.speed)}${gust} ${arrowSvg(s.dir)}</div>
        <div class="when">${compass(s.dir)} &middot; ${ageText(s.age_minutes)}</div>
      </div>`;
    })
    .join("");
}

export function renderWaterTemp(current) {
  const el = document.getElementById("water-temp");
  el.textContent = current.water_temp_f == null ? "--" : `${Math.round(current.water_temp_f)} \u00B0F`;
}
