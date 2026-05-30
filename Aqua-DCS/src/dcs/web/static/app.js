// Aqua DCS dashboard frontend

// ── sensor config ─────────────────────────────────────────────────────────────
const SENSORS = [
  { name: "temperature", label: "온도",  unit: "°C",  color: "#f97316", preset: 2.0,   offsetStep: 0.5 },
  { name: "salinity",    label: "염도",  unit: "ppt", color: "#38bdf8", preset: 4.0,   offsetStep: 0.5 },
  { name: "ph",          label: "pH",    unit: "pH",  color: "#a78bfa", preset: 0.6,   offsetStep: 0.05 },
  { name: "light",       label: "조도",  unit: "lux", color: "#facc15", preset: 160.0, offsetStep: 10 },
];

// ── storage keys ──────────────────────────────────────────────────────────────
const LS_KEY = "aqua-dcs:ui:v1";

// ── state ─────────────────────────────────────────────────────────────────────
let activeSensor = SENSORS[0].name;

// time mode
let timeMode = "minutes"; // 'minutes' | 'range'
let currentMinutes = 1440; // default 24h
let rangeFromUtc = null;   // ISO8601Z
let rangeToUtc   = null;   // ISO8601Z

// axes mode
let axesMode = "all"; // 'all' | 'active'

// chart
let chartInst = null;
let lastChartData = null;
let liveTickCount = 0;

// per-sensor scale state
const yScales = {};
const yOffsets = {};

SENSORS.forEach((s, i) => {
  yScales[s.name] = { mode: "auto", min: null, max: null };
  // default lane offsets: spread curves vertically to reduce overlap.
  // This offset is applied in axis-value units for each sensor.
  // You can tune these later if needed.
  const lane = i - (SENSORS.length - 1) / 2;
  yOffsets[s.name] = lane * s.preset * 0.8;
});

// ── DOM helpers ───────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

function safeJsonParse(s) {
  try { return JSON.parse(s); } catch { return null; }
}

function toLocalDatetimeValue(date) {
  // for <input type="datetime-local"> expects "YYYY-MM-DDTHH:mm"
  const pad = (n) => String(n).padStart(2, "0");
  return (
    date.getFullYear() + "-" +
    pad(date.getMonth() + 1) + "-" +
    pad(date.getDate()) + "T" +
    pad(date.getHours()) + ":" +
    pad(date.getMinutes())
  );
}

function localInputToUtcIso(value) {
  // value: "YYYY-MM-DDTHH:mm" (local time)
  // new Date(value) treats it as local time, and toISOString() returns UTC
  const d = new Date(value);
  if (isNaN(d.getTime())) return null;
  return d.toISOString().replace(".000Z", "Z");
}

function setActiveTabUI() {
  const tabsEl = $("sensor-tabs");
  if (!tabsEl) return;
  tabsEl.querySelectorAll(".tab-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.sensor === activeSensor);
  });
}

function setTimeButtonsUI() {
  const tb = $("time-btns");
  if (!tb) return;
  tb.querySelectorAll(".btn").forEach((b) => {
    b.classList.toggle(
      "active",
      timeMode === "minutes" && parseInt(b.dataset.minutes, 10) === currentMinutes
    );
  });
}

function persistUI() {
  const payload = {
    activeSensor,
    timeMode,
    currentMinutes,
    rangeFromUtc,
    rangeToUtc,
    axesMode,
    yScales,
    yOffsets,
  };
  localStorage.setItem(LS_KEY, JSON.stringify(payload));
}

function clampTo24hRange() {
  // for observation mode: default to recent 24h.
  // If a stored custom range exceeds 24h, clamp it.
  if (!rangeFromUtc || !rangeToUtc) return;
  const from = Date.parse(rangeFromUtc);
  const to = Date.parse(rangeToUtc);
  if (isNaN(from) || isNaN(to)) return;
  const maxMs = 24 * 60 * 60 * 1000;
  if (to - from > maxMs) {
    rangeFromUtc = new Date(to - maxMs).toISOString().replace(".000Z", "Z");
  }
}

function restoreUI() {
  const raw = localStorage.getItem(LS_KEY);
  const d = raw ? safeJsonParse(raw) : null;
  if (!d) {
    // initialize datetime inputs to recent 24h
    const now = new Date();
    const from = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    $("from-dt").value = toLocalDatetimeValue(from);
    $("to-dt").value = toLocalDatetimeValue(now);
    return;
  }

  if (d.activeSensor) activeSensor = d.activeSensor;
  if (d.timeMode) timeMode = d.timeMode;
  if (typeof d.currentMinutes === "number") currentMinutes = d.currentMinutes;
  rangeFromUtc = d.rangeFromUtc || null;
  rangeToUtc = d.rangeToUtc || null;
  if (d.axesMode) axesMode = d.axesMode;
  clampTo24hRange();

  if (d.yScales) {
    for (const s of SENSORS) {
      if (d.yScales[s.name]) yScales[s.name] = d.yScales[s.name];
    }
  }

  if (d.yOffsets) {
    for (const s of SENSORS) {
      if (typeof d.yOffsets[s.name] === "number") yOffsets[s.name] = d.yOffsets[s.name];
    }
  }

  // initialize datetime inputs
  const now = new Date();
  const fromDefault = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  $("from-dt").value = toLocalDatetimeValue(fromDefault);
  $("to-dt").value = toLocalDatetimeValue(now);
}

function setAxesButtonsUI() {
  const el = $("axes-btns");
  if (!el) return;
  el.querySelectorAll(".btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.axes === axesMode);
  });
}

// ── build UI ──────────────────────────────────────────────────────────────────
function buildUI() {
  // live cards
  const cardsEl = $("live-cards");
  SENSORS.forEach((s) => {
    const card = document.createElement("div");
    card.className = "live-card";
    card.id = `card-${s.name}`;
    card.innerHTML = `
      <div class="card-top">
        <span class="card-label" style="color:${s.color}">${s.label}</span>
        <span class="source-badge" id="src-${s.name}"></span>
      </div>
      <div class="card-value" id="val-${s.name}">--</div>
      <div class="card-unit">${s.unit}</div>
      <div class="card-ts" id="ts-${s.name}"></div>
    `;
    cardsEl.appendChild(card);
  });

  // sensor tabs
  const tabsEl = $("sensor-tabs");
  SENSORS.forEach((s) => {
    const btn = document.createElement("button");
    btn.className = "tab-btn" + (s.name === activeSensor ? " active" : "");
    btn.dataset.sensor = s.name;
    btn.style.setProperty("--tab-color", s.color);
    btn.textContent = s.label;
    tabsEl.appendChild(btn);
  });

  // events
  tabsEl.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-sensor]");
    if (!btn) return;
    activeSensor = btn.dataset.sensor;
    setActiveTabUI();
    syncYScaleBtns();
    persistUI();
  });

  const timeBtns = $("time-btns");
  if (timeBtns) timeBtns.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-minutes]");
    if (!btn) return;
    timeMode = "minutes";
    currentMinutes = parseInt(btn.dataset.minutes, 10);
    setTimeButtonsUI();
    persistUI();
    refreshTrend();
  });

  const yscaleBtns = $("yscale-btns");
  if (yscaleBtns) yscaleBtns.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-yscale]");
    if (!btn) return;
    handleYScale(activeSensor, btn.dataset.yscale);
    $("yscale-btns").querySelectorAll(".btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    persistUI();
  });

  const offsetBtns = $("offset-btns");
  if (offsetBtns) offsetBtns.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-offset]");
    if (!btn) return;
    handleOffset(activeSensor, btn.dataset.offset);
    persistUI();
  });

  const axesBtns = $("axes-btns");
  if (axesBtns) axesBtns.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-axes]");
    if (!btn) return;
    axesMode = btn.dataset.axes;
    setAxesButtonsUI();
    persistUI();
    // rebuild chart to apply axis visibility changes
    if (lastChartData) buildChart(lastChartData.timestamps, lastChartData.seriesValues);
  });

  const applyRangeBtn = $("apply-range");
  if (applyRangeBtn) applyRangeBtn.addEventListener("click", () => {
    const fv = $("from-dt").value;
    const tv = $("to-dt").value;
    const fUtc = localInputToUtcIso(fv);
    const tUtc = localInputToUtcIso(tv);
    if (!fUtc || !tUtc) {
      $("footer-status").textContent = "구간 선택 오류: from/to 시간을 확인해 주세요";
      return;
    }
    timeMode = "range";
    rangeFromUtc = fUtc;
    rangeToUtc = tUtc;
    setTimeButtonsUI();
    persistUI();
    refreshTrend();
  });

  const clearRangeBtn = $("clear-range");
  if (clearRangeBtn) clearRangeBtn.addEventListener("click", () => {
    timeMode = "minutes";
    rangeFromUtc = null;
    rangeToUtc = null;
    currentMinutes = 1440;
    setTimeButtonsUI();
    persistUI();
    refreshTrend();
  });
}

// ── y-scale/offset logic ─────────────────────────────────────────────────────
function handleYScale(sName, action) {
  const sc = yScales[sName];
  if (action === "auto") {
    sc.mode = "auto";
    sc.min = null;
    sc.max = null;
  } else if (action === "preset") {
    sc.mode = "preset";
    sc.min = null;
    sc.max = null;
  } else if (action === "zoom+" || action === "zoom-") {
    sc.mode = "zoom";
    if (sc.min !== null && sc.max !== null) {
      const mid = (sc.min + sc.max) / 2;
      const half = (sc.max - sc.min) / 2 * (action === "zoom+" ? 0.7 : 1.4);
      sc.min = mid - half;
      sc.max = mid + half;
    }
  }
  if (lastChartData) applyAllYScales(lastChartData.seriesValues);
}

function handleOffset(sName, action) {
  const cfg = SENSORS.find((s) => s.name === sName);
  const step = cfg?.offsetStep ?? 1;
  if (action === "up") yOffsets[sName] += step;
  if (action === "down") yOffsets[sName] -= step;
  if (action === "reset") {
    const i = SENSORS.findIndex((s) => s.name === sName);
    const lane = i - (SENSORS.length - 1) / 2;
    yOffsets[sName] = lane * (cfg?.preset ?? 1) * 0.8;
  }
  if (lastChartData) applyAllYScales(lastChartData.seriesValues);
}

function computeYRange(sName, values) {
  const sc = yScales[sName];
  const cfg = SENSORS.find((s) => s.name === sName);
  const valid = (values || []).filter((v) => v != null);

  // zoom keeps current min/max (then offset will be applied after)
  if (sc.mode === "zoom" && sc.min !== null) return { min: sc.min, max: sc.max };
  if (!valid.length) return { min: 0, max: 1 };

  const dMin = Math.min(...valid);
  const dMax = Math.max(...valid);

  if (sc.mode === "preset") {
    const mid = (dMin + dMax) / 2;
    sc.min = mid - cfg.preset / 2;
    sc.max = mid + cfg.preset / 2;
    return { min: sc.min, max: sc.max };
  }

  const span = dMax - dMin || 1;
  const pad = span * 0.1;
  sc.min = dMin - pad;
  sc.max = dMax + pad;
  return { min: sc.min, max: sc.max };
}

function syncYScaleBtns() {
  const sc = yScales[activeSensor];
  $("yscale-btns").querySelectorAll(".btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.yscale === sc.mode);
  });
}

// ── chart (uPlot) ────────────────────────────────────────────────────────────
const SCALE_KEYS = ["temp", "sal", "ph", "lux"];

function formatYTick(sensorName, v) {
  if (v == null) return "";
  if (sensorName === "temperature") return Number(v).toFixed(1);
  if (sensorName === "salinity") return Number(v).toFixed(1);
  if (sensorName === "ph") return Number(v).toFixed(2);
  if (sensorName === "light") return String(Math.round(Number(v)));
  return String(v);
}

function makeChartOpts(wrap, seriesValues) {
  const width = wrap.clientWidth || 800;
  const height = 320;

  const axes = [
    {
      stroke: "#64748b",
      grid: { stroke: "#1e293b" },
      ticks: { stroke: "#1e293b" },
      values: (u, vals) =>
        vals.map((v) => {
          if (v == null) return "";
          const d = new Date(v * 1000);
          return `${d.getHours().toString().padStart(2, "0")}:${d
            .getMinutes()
            .toString()
            .padStart(2, "0")}`;
        }),
    },
  ];

  // y-axes: keep the axis narrow on mobile.
  // We remove the built-in axis label and instead print the unit above the top tick.
  SENSORS.forEach((s, i) => {
    const showAxis = axesMode === "all" || s.name === activeSensor;
    axes.push({
      scale: SCALE_KEYS[i],
      side: s.name === "temperature" ? 3 : 1,
      size: 42,
      show: showAxis,
      stroke: s.color,
      grid: i === 0 ? { stroke: "#1e293b" } : { show: false },
      ticks: { stroke: "#1e293b" },
      // Put unit above the top-most tick value to save horizontal space.
      values: (u, vals) =>
        vals.map((v, idx) => {
          if (v == null) return "";
          const base = formatYTick(s.name, v);
          if (idx === vals.length - 1) return `${s.unit}\n${base}`;
          return base;
        }),
      // disable axis label area
      label: "",
      labelSize: 0,
    });
  });

  const scales = { x: { time: true } };
  SENSORS.forEach((s, i) => {
    const { min, max } = computeYRange(s.name, seriesValues[i]);
    // apply offset to axis & curve together by shifting the scale range.
    const off = yOffsets[s.name] || 0;
    scales[SCALE_KEYS[i]] = { min: min + off, max: max + off };
  });

  // real sensor = solid, dummy = dashed
  const series = [
    {},
    ...SENSORS.map((s, i) => {
      const isDummy = s.name !== "temperature"; // until real hw exists
      const base = {
        label: s.label,
        scale: SCALE_KEYS[i],
        stroke: s.color,
        width: 2,
        fill: s.color + "18",
        points: { show: false },
      };
      if (isDummy) {
        // uPlot supports line.dash in newer versions; keep fallback safe.
        base.dash = [6, 4];
      }
      return base;
    }),
  ];

  return { width, height, cursor: { show: true }, legend: { show: true }, scales, axes, series };
}

function buildChart(timestamps, seriesValues) {
  const wrap = $("chart-wrap");
  wrap.innerHTML = "";
  chartInst = new uPlot(makeChartOpts(wrap, seriesValues), [timestamps, ...seriesValues], wrap);
  lastChartData = { timestamps, seriesValues };
}

function updateChart(timestamps, seriesValues) {
  if (!chartInst) {
    buildChart(timestamps, seriesValues);
    return;
  }
  const wrap = $("chart-wrap");
  if (wrap.clientWidth && wrap.clientWidth !== chartInst.width) chartInst.setSize({ width: wrap.clientWidth, height: 320 });
  chartInst.setData([timestamps, ...seriesValues]);
  applyAllYScales(seriesValues);
  lastChartData = { timestamps, seriesValues };
}

function applyAllYScales(seriesValues) {
  if (!chartInst) return;
  SENSORS.forEach((s, i) => {
    const { min, max } = computeYRange(s.name, seriesValues[i]);
    const off = yOffsets[s.name] || 0;
    chartInst.setScale(SCALE_KEYS[i], { min: min + off, max: max + off });
  });
}

// ── source badge helper ───────────────────────────────────────────────────────
function sourceBadgeHtml(source) {
  if (source === "sensor") return `<span class="badge badge-sensor">SENSOR</span>`;
  if (source === "dummy") return `<span class="badge badge-dummy">DUMMY</span>`;
  return "";
}

// ── data fetching ─────────────────────────────────────────────────────────────
async function fetchLive() {
  const res = await fetch("/api/v1/live/latest");
  if (!res.ok) return null;
  return res.json();
}

async function fetchRecentAll(minutes) {
  const res = await fetch(`/api/v1/recent/all?minutes=${minutes}&limit=5000`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function fetchHistoryAll(fromUtcIso, toUtcIso) {
  const q = new URLSearchParams({ from: fromUtcIso, to: toUtcIso, limit: "5000" });
  const res = await fetch(`/api/v1/history/all?${q.toString()}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ── live card update (5 s) ────────────────────────────────────────────────────
async function refreshLive() {
  try {
    const data = await fetchLive();
    if (!data || !data.sensors) {
      $("status").textContent = "⚠ live 데이터 없음";
      return;
    }

    liveTickCount++;
    const heartbeat = liveTickCount % 2 === 0 ? "●" : "○";

    SENSORS.forEach((s) => {
      const sv = data.sensors[s.name];
      if (!sv) return;
      const valEl = $(`val-${s.name}`);
      const tsEl = $(`ts-${s.name}`);
      const srcEl = $(`src-${s.name}`);

      if (sv.value != null) {
        valEl.textContent = Number(sv.value).toFixed(3);
        valEl.style.color = s.color;
      } else {
        valEl.textContent = "ERR";
        valEl.style.color = "#ef4444";
      }

      const d = new Date(data.ts_utc);
      tsEl.textContent = d.toLocaleTimeString("ko-KR");

      if (srcEl) srcEl.innerHTML = sourceBadgeHtml(sv.source);
    });

    $("status").innerHTML = `${heartbeat} LIVE`;
    $("status").style.color = "#22c55e";
  } catch (e) {
    $("status").textContent = "⚠ " + e.message;
    $("status").style.color = "#f97316";
  }
}

// ── trend update ─────────────────────────────────────────────────────────────
async function refreshTrend() {
  try {
    let all;
    if (timeMode === "range" && rangeFromUtc && rangeToUtc) {
      all = await fetchHistoryAll(rangeFromUtc, rangeToUtc);
    } else {
      all = await fetchRecentAll(currentMinutes);
    }

    const tsSet = new Set();
    SENSORS.forEach((s) => (all[s.name] || []).forEach((r) => tsSet.add(r.ts_utc)));
    const sortedTs = Array.from(tsSet).sort();
    const timestamps = sortedTs.map((ts) => Date.parse(ts) / 1000);

    const seriesValues = SENSORS.map((s) => {
      const map = new Map((all[s.name] || []).map((r) => [r.ts_utc, r.value]));
      return sortedTs.map((ts) => (map.has(ts) ? map.get(ts) : null));
    });

    updateChart(timestamps, seriesValues);

    const modeText = timeMode === "range" && rangeFromUtc && rangeToUtc
      ? `range ${rangeFromUtc} ~ ${rangeToUtc}`
      : `${currentMinutes}m`;
    $("footer-status").textContent = `트렌드 갱신(${modeText}): ${new Date().toLocaleString("ko-KR")}`;
  } catch (e) {
    $("footer-status").textContent = `트렌드 오류: ${e.message}`;
  }
}

// ── init ──────────────────────────────────────────────────────────────────────
restoreUI();
buildUI();
setActiveTabUI();
setTimeButtonsUI();
syncYScaleBtns();
setAxesButtonsUI();

// If restored state says range mode, keep it; otherwise default to 24h.
if (timeMode !== "range") {
  timeMode = "minutes";
  if (!currentMinutes) currentMinutes = 1440;
}
persistUI();

refreshLive();
refreshTrend();

setInterval(refreshLive, 5000);
setInterval(refreshTrend, 60000);
