/**
 * Customer Segmentation Tool – Frontend Application
 * Handles file upload, API communication, chart rendering,
 * table population, search, filter, sort, pagination, and CSV download.
 */

(function () {
  "use strict";

  // ─── DOM References ───
  const uploadZone = document.getElementById("uploadZone");
  const fileInput = document.getElementById("fileInput");
  const fileInfo = document.getElementById("fileInfo");
  const fileName = document.getElementById("fileName");
  const fileSize = document.getElementById("fileSize");
  const removeFileBtn = document.getElementById("removeFileBtn");
  const clusterSlider = document.getElementById("clusterSlider");
  const clusterValue = document.getElementById("clusterValue");
  const runBtn = document.getElementById("runBtn");
  const loadingOverlay = document.getElementById("loadingOverlay");
  const resultsSection = document.getElementById("resultsSection");
  const errorToast = document.getElementById("errorToast");

  const statRows = document.getElementById("statRows");
  const statCleaned = document.getElementById("statCleaned");
  const statCustomers = document.getElementById("statCustomers");
  const statClusters = document.getElementById("statClusters");

  const profilesGrid = document.getElementById("profilesGrid");
  const clusterChartCanvas = document.getElementById("clusterChart");
  const searchInput = document.getElementById("searchInput");
  const segmentFilter = document.getElementById("segmentFilter");
  const downloadBtn = document.getElementById("downloadBtn");
  const tableBody = document.getElementById("tableBody");
  const paginationEl = document.getElementById("pagination");

  // ─── State ───
  let selectedFile = null;
  let allCustomers = [];
  let filteredCustomers = [];
  let profiles = [];
  let chartInstance = null;
  let elbowChartInstance = null;
  let currentPage = 1;
  const PAGE_SIZE = 15;
  let sortField = "monetary";
  let sortAsc = false;
  const scatter3dEl = document.getElementById("scatter3d");

  const API_URL = "http://localhost:5000/api/segment";

  // ─── Utility ───
  function formatNumber(n) {
    if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
    if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
    return n.toLocaleString();
  }

  function formatCurrency(n) {
    return "$" + Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function showError(msg) {
    errorToast.textContent = msg;
    errorToast.classList.add("visible");
    setTimeout(() => errorToast.classList.remove("visible"), 6000);
  }

  // ─── File Upload ───
  // The uploadZone div click is a direct user gesture → fileInput.click() is allowed.
  uploadZone.addEventListener("click", function (e) {
    // Prevent any parent elements from re-triggering this
    e.stopPropagation();
    fileInput.click();
  });

  // Keyboard accessibility: Enter or Space opens the picker
  uploadZone.addEventListener("keydown", function (e) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fileInput.click();
    }
  });

  // Drag and drop
  uploadZone.addEventListener("dragover", function (e) {
    e.preventDefault();
    e.stopPropagation();
    uploadZone.classList.add("dragover");
  });
  uploadZone.addEventListener("dragleave", function (e) {
    e.stopPropagation();
    uploadZone.classList.remove("dragover");
  });
  uploadZone.addEventListener("drop", function (e) {
    e.preventDefault();
    e.stopPropagation();
    uploadZone.classList.remove("dragover");
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
  });

  // File selected from dialog
  fileInput.addEventListener("change", function () {
    if (fileInput.files.length) handleFile(fileInput.files[0]);
  });

  function handleFile(file) {
    const name = file.name.toLowerCase();
    const validExtensions = [".csv", ".xlsx", ".xls", ".zip"];
    const isValid = validExtensions.some((ext) => name.endsWith(ext));
    if (!isValid) {
      showError("Please upload a .csv, .xlsx, .xls, or .zip file.");
      return;
    }
    selectedFile = file;
    fileName.textContent = file.name;
    if (file.size >= 1024 * 1024) {
      fileSize.textContent = (file.size / (1024 * 1024)).toFixed(1) + " MB";
    } else {
      fileSize.textContent = (file.size / 1024).toFixed(1) + " KB";
    }
    fileInfo.classList.add("visible");
    uploadZone.style.display = "none";
    runBtn.disabled = false;
  }

  removeFileBtn.addEventListener("click", () => {
    selectedFile = null;
    fileInput.value = "";
    fileInfo.classList.remove("visible");
    uploadZone.style.display = "";
    runBtn.disabled = true;
  });

  // ─── Cluster Slider ───
  clusterSlider.addEventListener("input", () => {
    clusterValue.textContent = clusterSlider.value;
  });

  // ─── Run Segmentation ───
  runBtn.addEventListener("click", async () => {
    if (!selectedFile) return;

    // Show loading
    loadingOverlay.classList.add("active");
    resultsSection.classList.remove("visible");

    // Animate loading steps
    const steps = ["step-clean", "step-rfm", "step-cluster", "step-profile"];
    let stepIdx = 0;
    const stepInterval = setInterval(() => {
      if (stepIdx > 0) {
        document.getElementById(steps[stepIdx - 1]).classList.remove("active");
        document.getElementById(steps[stepIdx - 1]).classList.add("done");
        document.getElementById(steps[stepIdx - 1]).textContent =
          "✅ " + document.getElementById(steps[stepIdx - 1]).textContent.slice(2);
      }
      if (stepIdx < steps.length) {
        document.getElementById(steps[stepIdx]).classList.add("active");
        document.getElementById(steps[stepIdx]).textContent =
          "▶ " + document.getElementById(steps[stepIdx]).textContent.slice(2);
      }
      stepIdx++;
      if (stepIdx > steps.length) clearInterval(stepInterval);
    }, 600);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("clusters", clusterSlider.value);

      const response = await fetch(API_URL, { method: "POST", body: formData });
      const data = await response.json();

      clearInterval(stepInterval);

      if (!response.ok || data.error) {
        throw new Error(data.error || "Unknown server error");
      }

      // Reset loading step icons
      steps.forEach((s) => {
        const el = document.getElementById(s);
        el.classList.remove("active", "done");
        el.textContent = "⏳" + el.textContent.slice(1);
      });

      renderResults(data);
    } catch (err) {
      showError(err.message);
    } finally {
      loadingOverlay.classList.remove("active");
      // Reset loading step icons for next run
      const stepEls = ["step-clean", "step-rfm", "step-cluster", "step-profile"];
      const defaultTexts = [
        "⬜ CLEANING DATA…",
        "⬜ COMPUTING RFM SCORES…",
        "⬜ RUNNING K-MEANS CLUSTERING…",
        "⬜ PROFILING SEGMENTS…",
      ];
      stepEls.forEach((id, i) => {
        const el = document.getElementById(id);
        el.classList.remove("active", "done");
        el.textContent = defaultTexts[i];
      });
    }
  });

  // ─── Render Results ───
  function renderResults(data) {
    const { stats, profiles: p, customers, elbow } = data;
    profiles = p;
    allCustomers = customers;

    // Stats
    statRows.textContent = formatNumber(stats.original_rows);
    statCleaned.textContent = formatNumber(stats.removed_rows);
    statCustomers.textContent = formatNumber(stats.total_customers);
    statClusters.textContent = stats.clusters;

    // Profiles
    renderProfiles();

    // Elbow chart
    if (elbow && elbow.length) renderElbowChart(elbow, stats.clusters);

    // 3D scatter
    render3DScatter();

    // 2D PCA chart
    renderChart();

    // Segment filter
    segmentFilter.innerHTML = '<option value="">All Segments</option>';
    profiles.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.name;
      opt.textContent = p.name;
      segmentFilter.appendChild(opt);
    });

    // Table
    filteredCustomers = [...allCustomers];
    sortField = "monetary";
    sortAsc = false;
    currentPage = 1;
    applySort();
    renderTable();

    // Show results
    resultsSection.classList.add("visible");
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // ─── Profile Cards ───
  function renderProfiles() {
    profilesGrid.innerHTML = "";
    profiles.forEach((p) => {
      const card = document.createElement("div");
      card.className = "profile-card";
      card.style.setProperty("--profile-color", p.color);
      card.innerHTML = `
        <div class="profile-header">
          <div class="profile-name">${p.name}</div>
          <div class="profile-count">
            <span class="count-value">${p.count}</span>
            <span class="count-pct">${p.pct}% of total</span>
          </div>
        </div>
        <div class="profile-desc">${p.description}</div>
        <div class="rfm-mini-grid">
          <div class="rfm-item">
            <div class="rfm-label">Recency</div>
            <div class="rfm-value">${p.avg_recency}d</div>
          </div>
          <div class="rfm-item">
            <div class="rfm-label">Frequency</div>
            <div class="rfm-value">${p.avg_frequency}</div>
          </div>
          <div class="rfm-item">
            <div class="rfm-label">Monetary</div>
            <div class="rfm-value">${formatCurrency(p.avg_monetary)}</div>
          </div>
        </div>
        <div class="profile-action"><strong>Action:</strong> ${p.action}</div>
      `;
      profilesGrid.appendChild(card);
    });
  }

  // ─── Elbow Method Chart ───
  function renderElbowChart(elbowData, chosenK) {
    const canvas = document.getElementById("elbowChart");
    if (!canvas) return;
    if (elbowChartInstance) elbowChartInstance.destroy();

    const labels = elbowData.map((d) => "K=" + d.k);
    const values = elbowData.map((d) => d.inertia);
    const pointColors = elbowData.map((d) =>
      d.k === chosenK ? "#ef4444" : "#4f46e5"
    );
    const pointRadii = elbowData.map((d) => (d.k === chosenK ? 10 : 5));

    elbowChartInstance = new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Inertia (Within-Cluster Sum of Squares)",
            data: values,
            borderColor: "#4f46e5",
            backgroundColor: "rgba(79, 70, 229, 0.05)",
            pointBackgroundColor: pointColors,
            pointBorderColor: pointColors,
            pointRadius: pointRadii,
            pointHoverRadius: 10,
            borderWidth: 2,
            fill: true,
            tension: 0.3,
            pointStyle: "circle",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: "#334155",
              font: { family: "'Inter', sans-serif", size: 12, weight: "500" },
            },
          },
          tooltip: {
            backgroundColor: "#0f172a",
            titleColor: "#ffffff",
            bodyColor: "#94a3b8",
            borderColor: "#334155",
            borderWidth: 1,
            cornerRadius: 8,
            padding: 12,
            titleFont: { family: "'Inter', sans-serif", size: 12, weight: "600" },
            bodyFont:  { family: "'Inter', sans-serif", size: 11 },
            callbacks: {
              afterLabel: (ctx) => {
                const k = elbowData[ctx.dataIndex].k;
                return k === chosenK ? " ★ Chosen K" : "";
              },
            },
          },
          annotation: undefined,
        },
        scales: {
          x: {
            ticks: { color: "#64748b", font: { family: "'Inter', sans-serif" } },
            grid: { color: "#f1f5f9" },
            title: { display: true, text: "Number of Clusters (K)", color: "#475569", font: { family: "'Inter', sans-serif", size: 11, weight: "500" } },
          },
          y: {
            ticks: { color: "#64748b", font: { family: "'Inter', sans-serif" } },
            grid: { color: "#f1f5f9" },
            title: { display: true, text: "Inertia", color: "#475569", font: { family: "'Inter', sans-serif", size: 11, weight: "500" } },
          },
        },
        animation: { duration: 600, easing: "easeOutQuart" },
      },
    });
  }

  // ─── 3D RFM Scatter (Plotly) ───
  function render3DScatter() {
    if (!scatter3dEl || typeof Plotly === "undefined") return;

    const traces = profiles.map((prof) => {
      const pts = allCustomers.filter((c) => c.cluster === prof.cluster);
      return {
        type: "scatter3d",
        mode: "markers",
        name: prof.name,
        x: pts.map((c) => c.rfm_x),
        y: pts.map((c) => c.rfm_y),
        z: pts.map((c) => c.rfm_z),
        text: pts.map(
          (c) =>
            `ID: ${c.customerid}<br>Recency: ${c.recency}d<br>Frequency: ${c.frequency}<br>Monetary: $${c.monetary.toFixed(2)}`
        ),
        hovertemplate: "%{text}<extra>" + prof.name + "</extra>",
        marker: {
          size: 5,
          color: prof.color,
          opacity: 0.85,
          line: { width: 0 },
        },
      };
    });

    const layout = {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor:  "rgba(0,0,0,0)",
      scene: {
        bgcolor: "#f8fafc",
        xaxis: {
          title: { text: "RECENCY", font: { color: "#475569", family: "Inter, sans-serif", size: 10, weight: "bold" } },
          tickfont: { color: "#64748b", family: "Inter, sans-serif", size: 9 },
          gridcolor: "#e2e8f0",
          zerolinecolor: "#cbd5e1",
        },
        yaxis: {
          title: { text: "FREQUENCY", font: { color: "#475569", family: "Inter, sans-serif", size: 10, weight: "bold" } },
          tickfont: { color: "#64748b", family: "Inter, sans-serif", size: 9 },
          gridcolor: "#e2e8f0",
          zerolinecolor: "#cbd5e1",
        },
        zaxis: {
          title: { text: "MONETARY", font: { color: "#475569", family: "Inter, sans-serif", size: 10, weight: "bold" } },
          tickfont: { color: "#64748b", family: "Inter, sans-serif", size: 9 },
          gridcolor: "#e2e8f0",
          zerolinecolor: "#cbd5e1",
        },
      },
      legend: {
        orientation: "h",
        yanchor: "bottom",
        y: -0.1,
        xanchor: "center",
        x: 0.5,
        font: { color: "#334155", family: "Inter, sans-serif", size: 11 },
        bgcolor: "rgba(255,255,255,0.9)",
        bordercolor: "#e2e8f0",
        borderwidth: 1,
      },
      margin: { l: 0, r: 0, t: 10, b: 20 },
    };

    Plotly.react(scatter3dEl, traces, layout, {
      displayModeBar: true,
      displaylogo: false,
      modeBarButtonsToRemove: ["toImage"],
      responsive: true,
    });
  }

  function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  // ─── 2D PCA Scatter Chart (Chart.js) ───
  function renderChart() {
    if (chartInstance) chartInstance.destroy();

    const clusterMap = {};
    allCustomers.forEach((c) => {
      if (!clusterMap[c.cluster]) clusterMap[c.cluster] = [];
      clusterMap[c.cluster].push({ x: c.pca_x, y: c.pca_y });
    });

    const datasets = profiles.map((p) => ({
      label: p.name,
      data: (clusterMap[p.cluster] || []),
      backgroundColor: hexToRgba(p.color, 0.6),
      borderColor: p.color,
      borderWidth: 1,
      pointRadius: 4,
      pointHoverRadius: 7,
      pointHoverBackgroundColor: p.color,
    }));

    chartInstance = new Chart(clusterChartCanvas, {
      type: "scatter",
      data: { datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "top",
            labels: {
              color: "#334155",
              font: { family: "'Inter', sans-serif", size: 12, weight: "500" },
              padding: 20,
              usePointStyle: true,
              pointStyle: "circle",
            },
          },
          tooltip: {
            backgroundColor: "#0f172a",
            titleColor: "#ffffff",
            bodyColor: "#94a3b8",
            borderColor: "#334155",
            borderWidth: 1,
            padding: 12,
            cornerRadius: 8,
            titleFont: { family: "'Inter', sans-serif", weight: "600", size: 12 },
            bodyFont:  { family: "'Inter', sans-serif", size: 11 },
          },
        },
        scales: {
          x: {
            title: { display: true, text: "PCA Component 1", color: "#475569", font: { family: "'Inter', sans-serif", size: 11, weight: "500" } },
            grid: { color: "#f1f5f9" },
            ticks: { color: "#64748b", font: { family: "'Inter', sans-serif" } },
          },
          y: {
            title: { display: true, text: "PCA Component 2", color: "#475569", font: { family: "'Inter', sans-serif", size: 11, weight: "500" } },
            grid: { color: "#f1f5f9" },
            ticks: { color: "#64748b", font: { family: "'Inter', sans-serif" } },
          },
        },
        animation: { duration: 800, easing: "easeOutQuart" },
      },
    });
  }

  // ─── Table Rendering ───
  function renderTable() {
    const start = (currentPage - 1) * PAGE_SIZE;
    const pageData = filteredCustomers.slice(start, start + PAGE_SIZE);

    tableBody.innerHTML = pageData
      .map((c) => {
        const prof = profiles.find((p) => p.name === c.segment) || {};
        const color = prof.color || "#9ca3af";
        return `
        <tr>
          <td><strong>${c.customerid}</strong></td>
          <td>${c.recency}</td>
          <td>${c.frequency}</td>
          <td>${formatCurrency(c.monetary)}</td>
          <td>
            <span class="segment-badge"
              style="--badge-bg: ${hexToRgba(color, 0.12)}; --badge-color: ${color}; --badge-border: ${hexToRgba(color, 0.3)};">
              ${c.segment}
            </span>
          </td>
        </tr>`;
      })
      .join("");

    renderPagination();
  }

  // ─── Pagination ───
  function renderPagination() {
    const totalPages = Math.ceil(filteredCustomers.length / PAGE_SIZE);
    if (totalPages <= 1) {
      paginationEl.innerHTML = "";
      return;
    }

    let html = `<button ${currentPage === 1 ? "disabled" : ""} data-page="${currentPage - 1}">‹</button>`;

    // Show max 7 page buttons
    const pages = computeVisiblePages(currentPage, totalPages, 7);
    pages.forEach((p) => {
      if (p === "…") {
        html += `<span class="page-info">…</span>`;
      } else {
        html += `<button class="${p === currentPage ? "active" : ""}" data-page="${p}">${p}</button>`;
      }
    });

    html += `<button ${currentPage === totalPages ? "disabled" : ""} data-page="${currentPage + 1}">›</button>`;
    paginationEl.innerHTML = html;
  }

  function computeVisiblePages(current, total, maxVisible) {
    if (total <= maxVisible) return Array.from({ length: total }, (_, i) => i + 1);
    const pages = [];
    const half = Math.floor(maxVisible / 2);
    let start = Math.max(1, current - half);
    let end = Math.min(total, start + maxVisible - 1);
    if (end - start < maxVisible - 1) start = Math.max(1, end - maxVisible + 1);
    if (start > 1) { pages.push(1); if (start > 2) pages.push("…"); }
    for (let i = start; i <= end; i++) pages.push(i);
    if (end < total) { if (end < total - 1) pages.push("…"); pages.push(total); }
    return pages;
  }

  paginationEl.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-page]");
    if (!btn || btn.disabled) return;
    currentPage = parseInt(btn.dataset.page);
    renderTable();
  });

  // ─── Search & Filter ───
  searchInput.addEventListener("input", applyFilters);
  segmentFilter.addEventListener("change", applyFilters);

  function applyFilters() {
    const query = searchInput.value.trim().toLowerCase();
    const segment = segmentFilter.value;
    filteredCustomers = allCustomers.filter((c) => {
      const matchId = !query || String(c.customerid).toLowerCase().includes(query);
      const matchSeg = !segment || c.segment === segment;
      return matchId && matchSeg;
    });
    currentPage = 1;
    applySort();
    renderTable();
  }

  // ─── Sort ───
  document.querySelectorAll(".data-table th[data-sort]").forEach((th) => {
    th.addEventListener("click", () => {
      const field = th.dataset.sort;
      if (sortField === field) {
        sortAsc = !sortAsc;
      } else {
        sortField = field;
        sortAsc = true;
      }
      // Update sort indicators
      document.querySelectorAll(".data-table th").forEach((t) => t.classList.remove("sorted-asc", "sorted-desc"));
      th.classList.add(sortAsc ? "sorted-asc" : "sorted-desc");
      applySort();
      renderTable();
    });
  });

  function applySort() {
    filteredCustomers.sort((a, b) => {
      let va = a[sortField],
        vb = b[sortField];
      if (typeof va === "string") {
        va = va.toLowerCase();
        vb = vb.toLowerCase();
        return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
      }
      return sortAsc ? va - vb : vb - va;
    });
  }

  // ─── Download CSV ───
  downloadBtn.addEventListener("click", () => {
    if (!allCustomers.length) return;

    const headers = ["CustomerID", "Recency", "Frequency", "Monetary", "Segment", "Cluster"];
    const rows = allCustomers.map((c) => [c.customerid, c.recency, c.frequency, c.monetary, c.segment, c.cluster]);

    let csv = headers.join(",") + "\n";
    rows.forEach((r) => {
      csv += r.map((v) => `"${v}"`).join(",") + "\n";
    });

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "customer_segments.csv";
    a.click();
    URL.revokeObjectURL(url);
  });
})();
