export const TZ = "America/Los_Angeles";

const timeFmt = new Intl.DateTimeFormat("en-US", { timeZone: TZ, hour: "numeric", minute: "2-digit" });
const hourFmt = new Intl.DateTimeFormat("en-US", { timeZone: TZ, hour: "numeric" });
const dayFmt = new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" });

const POINTS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];

/** "3:45 PM" in Pacific time. `sec` is a unix timestamp in seconds. */
export const fmtTime = (sec) => timeFmt.format(new Date(sec * 1000));
/** "3 PM" */
export const fmtHour = (sec) => hourFmt.format(new Date(sec * 1000));
/** "2026-11-13" for the Pacific calendar day containing `sec` (en-CA gives ISO order). */
export const pacificDay = (sec = Date.now() / 1000) => dayFmt.format(new Date(sec * 1000));

export const compass = (deg) => (deg == null ? "--" : POINTS[Math.round(((deg % 360) + 360) % 360 / 22.5) % 16]);

export function ageText(minutes) {
  if (minutes == null) return "";
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const h = Math.floor(minutes / 60);
  if (h < 48) return `${h} h ${minutes % 60} min ago`;
  return `${Math.floor(h / 24)} days ago`;
}

export const num = (v) => (v == null ? "--" : String(Math.round(v)));

/** Small SVG arrow that points where the wind is blowing TOWARD (meteorological "from" + 180). */
export function arrowSvg(fromDeg) {
  if (fromDeg == null) return "";
  const rot = (fromDeg + 180) % 360;
  return `<svg viewBox="-12 -12 24 24" aria-hidden="true"><g transform="rotate(${rot})"><path d="M0 9V-9M0-9L-5-3M0-9L5-3" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></g></svg>`;
}

/** UTC offset (ms) of the Pacific zone at time `ms`, used to align chart ticks to local hours. */
export function pacificOffsetMs(ms) {
  const asLocal = new Date(new Date(ms).toLocaleString("en-US", { timeZone: TZ }));
  const asUtc = new Date(new Date(ms).toLocaleString("en-US", { timeZone: "UTC" }));
  return asLocal - asUtc;
}
