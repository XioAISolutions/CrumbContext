(() => {
  "use strict";

  const body = document.body;
  const basePath = body.dataset.basePath || "/";
  const dialog = document.getElementById("search-panel");
  const toggle = document.getElementById("search-toggle");
  const input = document.getElementById("search-input");
  const status = document.getElementById("search-status");
  const results = document.getElementById("search-results");

  if (!dialog || !toggle || !input || !status || !results) {
    return;
  }

  let indexPromise;

  const loadIndex = () => {
    if (!indexPromise) {
      indexPromise = fetch(`${basePath}search.json`, { credentials: "same-origin" })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`search index request failed: ${response.status}`);
          }
          return response.json();
        });
    }
    return indexPromise;
  };

  const normalize = (value) => value.toLocaleLowerCase().replace(/\s+/g, " ").trim();

  const score = (entry, terms) => {
    const title = normalize(entry.title || "");
    const headings = normalize((entry.headings || []).join(" "));
    const description = normalize(entry.description || "");
    const text = normalize(entry.text || "");
    let total = 0;
    for (const term of terms) {
      if (!text.includes(term) && !title.includes(term) && !headings.includes(term)) {
        return 0;
      }
      if (title.includes(term)) total += 24;
      if (headings.includes(term)) total += 12;
      if (description.includes(term)) total += 7;
      total += Math.min(6, text.split(term).length - 1);
    }
    return total;
  };

  const clearResults = () => {
    while (results.firstChild) results.removeChild(results.firstChild);
  };

  const render = (entries, query) => {
    clearResults();
    const terms = normalize(query).split(" ").filter(Boolean);
    if (!terms.length) {
      status.textContent = "Type at least one word.";
      return;
    }
    const matches = entries
      .map((entry) => ({ entry, score: score(entry, terms) }))
      .filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score || a.entry.title.localeCompare(b.entry.title))
      .slice(0, 12);

    status.textContent = matches.length
      ? `${matches.length} result${matches.length === 1 ? "" : "s"}`
      : "No matching documentation found.";

    for (const { entry } of matches) {
      const item = document.createElement("li");
      const link = document.createElement("a");
      link.href = entry.url;
      const title = document.createElement("strong");
      title.textContent = entry.title;
      const detail = document.createElement("span");
      detail.textContent = `${entry.section} · ${entry.description}`;
      link.append(title, detail);
      item.appendChild(link);
      results.appendChild(item);
    }
  };

  const openSearch = () => {
    if (!dialog.open) dialog.showModal();
    toggle.setAttribute("aria-expanded", "true");
    status.textContent = "Loading search index…";
    loadIndex()
      .then((entries) => {
        status.textContent = "Type at least one word.";
        input.focus();
        if (input.value) render(entries, input.value);
      })
      .catch(() => {
        status.textContent = "Search is temporarily unavailable.";
      });
  };

  toggle.addEventListener("click", openSearch);
  dialog.addEventListener("close", () => {
    toggle.setAttribute("aria-expanded", "false");
    toggle.focus();
  });
  dialog.addEventListener("click", (event) => {
    const bounds = dialog.getBoundingClientRect();
    const outside =
      event.clientX < bounds.left ||
      event.clientX > bounds.right ||
      event.clientY < bounds.top ||
      event.clientY > bounds.bottom;
    if (outside) dialog.close();
  });
  input.addEventListener("input", () => {
    loadIndex().then((entries) => render(entries, input.value)).catch(() => {});
  });

  document.addEventListener("keydown", (event) => {
    const target = event.target;
    const typing = target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement;
    if (event.key === "/" && !typing && !event.metaKey && !event.ctrlKey && !event.altKey) {
      event.preventDefault();
      openSearch();
    }
    if (event.key === "Escape" && dialog.open) {
      dialog.close();
    }
  });
})();
