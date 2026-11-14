export function initTheme(onChange) {
  const root = document.documentElement;
  document.getElementById("theme-toggle").addEventListener("click", () => {
    const next = root.dataset.theme === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    localStorage.setItem("theme", next);
    onChange?.(next);
  });
}
