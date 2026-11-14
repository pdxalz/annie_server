async function getJson(url) {
  const resp = await fetch(url, { cache: "no-store" });
  if (!resp.ok) throw new Error(`${url} -> HTTP ${resp.status}`);
  return resp.json();
}

const qs = (params) =>
  Object.entries(params)
    .filter(([, v]) => v != null)
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
    .join("&");

export const api = {
  status: () => getJson("/api/v1/status"),
  current: () => getJson("/api/v1/current"),
  forecast: () => getJson("/api/v1/forecast?hours=8"),
  firstDate: () => getJson("/api/v1/first_date"),
  /** window = {hours} or {date}; stations = ["annie", ...] */
  series: (window, stations) => getJson(`/api/v1/series?${qs({ ...window, stations: stations.join(",") })}`),
  tides: (window) => getJson(`/api/v1/tides?${qs(window)}`),
};
