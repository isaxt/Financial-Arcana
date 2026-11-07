// Ledger charts (Chart.js, bundled in js/vendor). Data is injected by ledger.html as window.LEDGER_DATA.
(function () {
  if (typeof Chart === "undefined" || !window.LEDGER_DATA) return;
  var D = window.LEDGER_DATA;
  var GOLD = "#B49A62", BURG = "#642E42", BLUE = "#697C8C", CREAM = "#E8DFC9", OLIVE = "#73775E";

  Chart.defaults.color = CREAM;
  Chart.defaults.font.family = "'DM Mono', monospace";
  Chart.defaults.borderColor = "rgba(155,149,140,0.25)";

  function el(id) { return document.getElementById(id); }
  function col(rows, key) { return rows.map(function (r) { return r[key]; }); }
  function axisTitle(text) { return { display: true, text: text }; }

  if (el("chart-format")) {
    new Chart(el("chart-format"), {
      type: "bar",
      data: { labels: col(D.aml_format, "payment_format"),
              datasets: [{ label: "Flagged share (%)", backgroundColor: BURG, borderColor: GOLD, borderWidth: 1,
                           data: col(D.aml_format, "flagged_rate") }] },
      options: { plugins: { legend: { display: false } },
                 scales: { y: { title: axisTitle("% flagged"), beginAtZero: true } } }
    });
  }

  if (el("chart-hist")) {
    new Chart(el("chart-hist"), {
      type: "bar",
      data: { labels: D.histogram.map(function (r) { return Number(r.bin_start).toFixed(1); }),
              datasets: [
                { label: "Not flagged", backgroundColor: BLUE, data: col(D.histogram, "nonflagged") },
                { label: "Flagged", backgroundColor: BURG, borderColor: GOLD, borderWidth: 1, data: col(D.histogram, "flagged") }] },
      options: { scales: { x: { title: axisTitle("log10(amount + 1)") },
                           y: { type: "logarithmic", title: axisTitle("transactions (log scale)") } } }
    });
  }

  if (el("chart-daily")) {
    new Chart(el("chart-daily"), {
      type: "line",
      data: { labels: col(D.daily, "date"),
              datasets: [
                { label: "All transactions", borderColor: BLUE, backgroundColor: BLUE, pointRadius: 2, tension: 0.2,
                  data: col(D.daily, "count"), yAxisID: "y" },
                { label: "Flagged", borderColor: GOLD, backgroundColor: GOLD, pointRadius: 2, tension: 0.2,
                  data: col(D.daily, "flagged"), yAxisID: "y1" }] },
      options: { scales: { y: { beginAtZero: true, title: axisTitle("all transactions") },
                           y1: { beginAtZero: true, position: "right", grid: { drawOnChartArea: false },
                                 title: axisTitle("flagged") } } }
    });
  }

  if (el("chart-cats")) {
    new Chart(el("chart-cats"), {
      type: "bar",
      data: { labels: col(D.categories, "category"),
              datasets: [{ label: "Share of transactions (%)", backgroundColor: GOLD, data: col(D.categories, "share_pct") }] },
      options: { indexAxis: "y", plugins: { legend: { display: false } },
                 scales: { x: { title: axisTitle("% of all transactions"), beginAtZero: true } } }
    });
  }

  if (el("chart-fraud")) {
    new Chart(el("chart-fraud"), {
      type: "bar",
      data: { labels: col(D.fraud, "category"),
              datasets: [{ label: "Fraud rate (%)", backgroundColor: BURG, borderColor: GOLD, borderWidth: 1,
                           data: col(D.fraud, "fraud_rate_pct") }] },
      options: { indexAxis: "y", plugins: { legend: { display: false } },
                 scales: { x: { title: axisTitle("% of labelled transactions flagged as fraud"), beginAtZero: true } } }
    });
  }

  if (el("chart-users")) {
    new Chart(el("chart-users"), {
      type: "bar",
      data: { labels: col(D.users, "bucket"),
              datasets: [{ label: "Clients", backgroundColor: OLIVE, data: col(D.users, "users") }] },
      options: { plugins: { legend: { display: false } },
                 scales: { x: { title: axisTitle("transactions per client") },
                           y: { title: axisTitle("clients"), beginAtZero: true } } }
    });
  }
})();
