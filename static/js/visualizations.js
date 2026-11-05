// Ledger charts (Chart.js). Data is injected by ledger.html as window.LEDGER_DATA.
(function () {
  if (typeof Chart === "undefined" || !window.LEDGER_DATA) return;
  var D = window.LEDGER_DATA;
  var GOLD = "#B49A62", BURG = "#642E42", BLUE = "#697C8C", CREAM = "#E8DFC9", GRAY = "#9B958C";

  Chart.defaults.color = CREAM;
  Chart.defaults.font.family = "'DM Mono', monospace";
  Chart.defaults.borderColor = "rgba(155,149,140,0.25)";

  function el(id) { return document.getElementById(id); }

  if (el("chart-format")) {
    new Chart(el("chart-format"), {
      type: "bar",
      data: {
        labels: D.aml_format.map(function (r) { return r.payment_format; }),
        datasets: [{ label: "Flagged share (%)", backgroundColor: BURG, borderColor: GOLD, borderWidth: 1,
                     data: D.aml_format.map(function (r) { return r.flagged_rate; }) }]
      },
      options: { plugins: { legend: { display: false } },
                 scales: { y: { title: { display: true, text: "% flagged" }, beginAtZero: true } } }
    });
  }

  if (el("chart-hist")) {
    new Chart(el("chart-hist"), {
      type: "bar",
      data: {
        labels: D.histogram.map(function (r) { return Number(r.bin_start).toFixed(1); }),
        datasets: [
          { label: "Not flagged", backgroundColor: BLUE, data: D.histogram.map(function (r) { return r.nonflagged; }) },
          { label: "Flagged", backgroundColor: BURG, borderColor: GOLD, borderWidth: 1, data: D.histogram.map(function (r) { return r.flagged; }) }
        ]
      },
      options: { scales: { x: { title: { display: true, text: "log10(amount + 1)" } },
                           y: { type: "logarithmic", title: { display: true, text: "transactions (log scale)" } } } }
    });
  }

  if (el("chart-cats")) {
    new Chart(el("chart-cats"), {
      type: "bar",
      data: {
        labels: D.categories.map(function (r) { return r.category; }),
        datasets: [{ label: "Share of transactions (%)", backgroundColor: GOLD, data: D.categories.map(function (r) { return r.share_pct; }) }]
      },
      options: { indexAxis: "y", plugins: { legend: { display: false } },
                 scales: { x: { title: { display: true, text: "% of all transactions" }, beginAtZero: true } } }
    });
  }
})();
