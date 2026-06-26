// dashboard.js - 工数・コスト分析ダッシュボード

const FIXED_HOUR_KEYS = new Set([
  "月", "案件（業務）名", "区分", "内外製区分", "品区コード", "合計時間(h)", "group", "item"
]);

const GROUP_COLORS = {
  "印材":     "#2ecc71",
  "工用":     "#3498db",
  "電気":     "#9b59b6",
  "ロール":   "#e67e22",
  "合樹":     "#1abc9c",
  "新製品PJ": "#e74c3c",
  "MFS":      "#f39c12",
  "精練":     "#16a085",
  "FH":       "#e91e63",
  "(その他)": "#95a5a6",
};

const COLOR_PALETTE = [
  "#3498db","#2ecc71","#e74c3c","#9b59b6","#f39c12","#1abc9c",
  "#e67e22","#34495e","#16a085","#8e44ad","#d35400","#27ae60",
];

// ドーナツ中央テキストプラグイン
const doughnutCenterPlugin = {
  id: 'doughnutCenter',
  afterDraw(chart) {
    if (chart.config.type !== 'doughnut') return;
    const opts = chart.options.plugins?.doughnutCenter;
    if (!opts?.enabled) return;
    const { ctx, chartArea } = chart;
    if (!chartArea) return;
    const cx = (chartArea.left + chartArea.right) / 2;
    const cy = (chartArea.top + chartArea.bottom) / 2;
    ctx.save();
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = `bold ${opts.valueFontSize || 20}px sans-serif`;
    ctx.fillStyle = opts.valueColor || '#212529';
    ctx.fillText(opts.value || '', cx, cy - 14);
    ctx.font = `${opts.labelFontSize || 10}px sans-serif`;
    ctx.fillStyle = '#6c757d';
    ctx.fillText(opts.label || '', cx, cy + 4);
    ctx.font = `bold ${opts.ratioFontSize || 14}px sans-serif`;
    ctx.fillStyle = opts.ratioColor || '#e74c3c';
    ctx.fillText(opts.ratio || '', cx, cy + 22);
    ctx.restore();
  }
};
Chart.register(doughnutCenterPlugin);

// ドーナツスライスラベルプラグイン（グループ名＋%を常時表示）
const doughnutSliceLabels = {
  id: 'doughnutSliceLabels',
  afterDraw(chart) {
    if (chart.config.type !== 'doughnut') return;
    const opts = chart.options.plugins?.doughnutSliceLabels;
    if (!opts?.enabled) return;
    const { ctx } = chart;
    const meta = chart.getDatasetMeta(0);
    if (!meta?.data?.length) return;
    const dataset = chart.data.datasets[0];
    const labels = chart.data.labels || [];
    const total = dataset.data.reduce((a, b) => a + b, 0);
    if (!total) return;
    const fs = opts.fontSize || 11;
    const color = opts.color || '#fff';
    const unit = opts.unit || '';
    const precision = opts.precision ?? 0;
    ctx.save();
    meta.data.forEach((arc, i) => {
      const val = dataset.data[i];
      if (!val || val / total < 0.04) return;
      const midAngle = (arc.startAngle + arc.endAngle) / 2;
      const r = (arc.innerRadius + arc.outerRadius) / 2;
      const x = arc.x + Math.cos(midAngle) * r;
      const y = arc.y + Math.sin(midAngle) * r;
      const numStr = precision > 0
        ? val.toFixed(precision)
        : Math.round(val).toLocaleString('ja-JP');
      const valStr = unit ? numStr + ' ' + unit : numStr;
      const name = (opts.showName !== false) ? (labels[i] || '') : null;
      ctx.textAlign = 'center';
      ctx.fillStyle = color;
      ctx.textBaseline = 'middle';
      if (name) {
        ctx.font = `bold ${fs}px sans-serif`;
        ctx.fillText(name, x, y - (fs * 0.7));
        ctx.font = `${fs}px sans-serif`;
        ctx.fillText(valStr, x, y + (fs * 0.7));
      } else {
        ctx.font = `bold ${fs}px sans-serif`;
        ctx.fillText(valStr, x, y);
      }
    });
    ctx.restore();
  }
};
Chart.register(doughnutSliceLabels);

let charts = {};
let allMonths = [];
let allGroups = [];
let memberCols = [];

// ================================================================
// 初期化
// ================================================================
document.addEventListener('DOMContentLoaded', () => {
  allMonths = extractMonths();
  allGroups = extractGroups();
  memberCols = extractMemberCols();

  buildMonthSelectors();
  buildGroupCheckboxes();
  buildPersonSelector();
  initCharts();
  renderAll();

  document.getElementById('monthFrom').addEventListener('change', renderAll);
  document.getElementById('monthTo').addEventListener('change', renderAll);
  document.getElementById('personSelect').addEventListener('change', () => {
    renderPersonTrend(getMonthRange(), getSelectedGroups());
  });
  document.querySelectorAll('.group-check-input').forEach(cb =>
    cb.addEventListener('change', () => {
      updateGroupCheckStyle(cb);
      renderAll();
    })
  );

  // 個人別タブに切り替えたとき、非表示状態で初期化されたグラフをリサイズして正しく描画する
  document.getElementById('tab-person-btn').addEventListener('shown.bs.tab', () => {
    charts.personHours.resize();
    charts.personProjs.resize();
  });
});

// ================================================================
// データ抽出ヘルパー
// ================================================================
function extractMonths() {
  const s = new Set();
  (typeof allCosts !== 'undefined' ? allCosts : []).forEach(r => r["月"] && s.add(r["月"]));
  (typeof allHours !== 'undefined' ? allHours : []).forEach(r => r["月"] && s.add(r["月"]));
  return Array.from(s).sort();
}

function extractGroups() {
  const s = new Set();
  (typeof allCosts !== 'undefined' ? allCosts : []).forEach(r => r.group && s.add(r.group));
  (typeof allHours !== 'undefined' ? allHours : []).forEach(r => r.group && s.add(r.group));
  const preferred = ["本社","印材","工用","電気","ロール","合樹","新製品PJ","(その他)"];
  const ordered = preferred.filter(g => s.has(g));
  s.forEach(g => { if (!ordered.includes(g)) ordered.push(g); });
  return ordered;
}

function extractMemberCols() {
  if (typeof allHours === 'undefined' || allHours.length === 0) return [];
  return Object.keys(allHours[0]).filter(k => !FIXED_HOUR_KEYS.has(k));
}

function getGroupColor(group, idx) {
  return GROUP_COLORS[group] || COLOR_PALETTE[(idx || 0) % COLOR_PALETTE.length];
}

/** インシデントコードを案件名に解決する（incNameMap があれば使用） */
function resolveProjectName(code) {
  if (typeof incNameMap !== 'undefined' && incNameMap[code]) return incNameMap[code];
  return code;
}

// ================================================================
// フィルター UI の構築
// ================================================================
function buildMonthSelectors() {
  const fromSel = document.getElementById('monthFrom');
  const toSel = document.getElementById('monthTo');
  allMonths.forEach(m => {
    fromSel.append(new Option(m, m));
    toSel.append(new Option(m, m));
  });
  if (allMonths.length > 0) {
    fromSel.value = allMonths[0];
    toSel.value = allMonths[allMonths.length - 1];
  }
}

function buildGroupCheckboxes() {
  const container = document.getElementById('groupCheckboxes');
  allGroups.forEach((g, i) => {
    const color = getGroupColor(g, i);
    const label = document.createElement('label');
    label.className = 'group-check-label';
    label.style.backgroundColor = color + 'aa';
    label.style.borderColor = color;

    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.className = 'group-check-input';
    cb.value = g;
    cb.checked = true;

    label.appendChild(cb);
    label.appendChild(document.createTextNode(' ' + g));
    container.appendChild(label);
  });
}

function buildPersonSelector() {
  const sel = document.getElementById('personSelect');
  if (!sel) return;
  memberCols.forEach(p => sel.append(new Option(p, p)));
  if (memberCols.length > 0) sel.value = memberCols[0];
}

function updateGroupCheckStyle(cb) {
  const label = cb.closest('.group-check-label');
  if (!label) return;
  label.style.opacity = cb.checked ? '1' : '0.4';
}

// ================================================================
// フィルター値の取得
// ================================================================
function getSelectedGroups() {
  return Array.from(document.querySelectorAll('.group-check-input:checked')).map(cb => cb.value);
}

function getMonthRange() {
  const from = document.getElementById('monthFrom').value;
  const to   = document.getElementById('monthTo').value;
  if (from > to) return [];
  return allMonths.filter(m => m >= from && m <= to);
}

function getSelectedPerson() {
  return document.getElementById('personSelect')?.value || '';
}

// ================================================================
// Chart.js インスタンスの初期化（空データ）
// ================================================================
function initCharts() {

  // グラフ① グループ別累計コスト（ドーナツ）
  charts.costTrend = new Chart(
    document.getElementById('chartCostTrend').getContext('2d'), {
    type: 'doughnut',
    data: { labels: [], datasets: [] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'right', labels: { boxWidth: 14, font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: ctx => {
              const val = ctx.parsed;
              const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
              const pct = total > 0 ? (val / total * 100).toFixed(1) : '0.0';
              return ` ${ctx.label}: ${val.toLocaleString()} 千円 (${pct}%)`;
            }
          }
        },
        doughnutCenter: {
          enabled: true,
          value: '',
          label: '千円',
          ratio: '',
          valueColor: '#212529',
          ratioColor: '#6c757d',
          valueFontSize: 20,
          labelFontSize: 12,
          ratioFontSize: 10,
        },
        doughnutSliceLabels: { enabled: false, fontSize: 11, color: '#fff', unit: '千円', precision: 0, showName: false },
      }
    }
  });

  // グラフ② 案件別コスト Top 20（水平棒）
  charts.topProjects = new Chart(
    document.getElementById('chartTopProjects').getContext('2d'), {
    type: 'bar',
    data: { labels: [], datasets: [] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: ctx => {
              const ds = ctx[0].dataset;
              return (ds._fullLabels && ds._fullLabels[ctx[0].dataIndex]) || ctx[0].label;
            },
            label: ctx => {
              const ds = ctx.dataset;
              const lines = [` 部門費: ${Math.round(ctx.parsed.x).toLocaleString('ja-JP')} 千円`];
              if (ds._hours) lines.push(` 工数: ${ds._hours[ctx.dataIndex]} 時間`);
              return lines;
            }
          }
        }
      },
      scales: {
        x: { title: { display: true, text: '部門費（千円）', font: { size: 11 } } },
        y: { ticks: { font: { size: 9 }, autoSkip: false } }
      }
    }
  });

  // グラフ③a 個人別 合計平均工数＋案件数推移（2軸棒＋折れ線）
  charts.personHours = new Chart(
    document.getElementById('chartPersonHours').getContext('2d'), {
    type: 'bar',
    data: { labels: [], datasets: [] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
        tooltip: { mode: 'index' }
      },
      scales: {
        x: { ticks: { font: { size: 10 } } },
        y1: {
          type: 'linear', position: 'left',
          title: { display: true, text: '平均工数（h/件）', font: { size: 10 } },
          min: 0,
        },
        y2: {
          type: 'linear', position: 'right',
          title: { display: true, text: '担当案件数（件）', font: { size: 10 } },
          grid: { drawOnChartArea: false },
          min: 0,
          ticks: { stepSize: 1 },
        }
      }
    }
  });

  // グラフ③b 個人別 担当テーマ工数（横棒）
  charts.personProjs = new Chart(
    document.getElementById('chartPersonProjs').getContext('2d'), {
    type: 'bar',
    data: { labels: [], datasets: [] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: ctx => (ctx[0].dataset._fullLabels || [])[ctx[0].dataIndex] || ctx[0].label,
            label: ctx => {
              const ds = ctx.dataset;
              const i  = ctx.dataIndex;
              const kubun = (ds._kubun || [])[i] || '';
              return ` ${kubun}: ${ctx.parsed.x.toFixed(1)} h`;
            },
          }
        }
      },
      scales: {
        x: { title: { display: true, text: '工数（h）', font: { size: 10 } } },
        y: { ticks: { font: { size: 9 }, autoSkip: false } }
      }
    }
  });

  // エラーバープラグイン（グラフ④用）
  const errorBarPlugin = {
    id: 'errorBar',
    afterDatasetsDraw(chart) {
      const ds = chart.data.datasets.find(d => d._stdDev);
      if (!ds) return;
      const dsIdx = chart.data.datasets.indexOf(ds);
      const meta = chart.getDatasetMeta(dsIdx);
      const ctx = chart.ctx;
      ctx.save();
      ctx.strokeStyle = ds.borderColor || '#3498db';
      ctx.lineWidth = 2;
      meta.data.forEach((pt, i) => {
        const std = ds._stdDev[i] || 0;
        if (std <= 0) return;
        const yScale = chart.scales[ds.yAxisID];
        const yVal = ds.data[i];
        if (yVal == null) return;
        const top = yScale.getPixelForValue(yVal + std);
        const bot = yScale.getPixelForValue(Math.max(0, yVal - std));
        const x = pt.x;
        const hw = 5;
        ctx.beginPath();
        ctx.moveTo(x, top); ctx.lineTo(x, bot);
        ctx.moveTo(x - hw, top); ctx.lineTo(x + hw, top);
        ctx.moveTo(x - hw, bot); ctx.lineTo(x + hw, bot);
        ctx.stroke();
      });
      ctx.restore();
    }
  };

  // グラフ④ 一人当たり案件数推移（折れ線+エラーバー）
  charts.projectTrend = new Chart(
    document.getElementById('chartProjectTrend').getContext('2d'), {
    type: 'bar',
    data: { labels: [], datasets: [] },
    plugins: [errorBarPlugin],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
        tooltip: {
          mode: 'index',
          callbacks: {
            label: ctx => {
              const ds = ctx.dataset;
              if (ds._stdDev) {
                const std = ds._stdDev[ctx.dataIndex] || 0;
                return ` ${ds.label}: ${ctx.parsed.y.toFixed(1)} 件 (±${std.toFixed(1)})`;
              }
              return ` ${ds.label}: ${ctx.parsed.y.toFixed(1)} h/件`;
            }
          }
        }
      },
      scales: {
        x: {},
        y1: {
          type: 'linear', position: 'left',
          title: { display: true, text: '1案件当り平均時間（h）', font: { size: 10 } },
          min: 0,
        },
        y2: {
          type: 'linear', position: 'right',
          title: { display: true, text: '平均担当案件数（件）', font: { size: 10 } },
          grid: { drawOnChartArea: false },
          min: 0,
        }
      }
    }
  });

  // グラフ⑤ 区分別累計工数（ドーナツ）
  charts.kubun = new Chart(
    document.getElementById('chartKubun').getContext('2d'), {
    type: 'doughnut',
    data: { labels: [], datasets: [] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'right', labels: { boxWidth: 14, font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: ctx => {
              const val = ctx.parsed;
              const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
              const pct = total > 0 ? (val / total * 100).toFixed(1) : '0.0';
              return ` ${ctx.label}: ${val.toFixed(1)} 人工/月 (${pct}%)`;
            }
          }
        },
        doughnutCenter: {
          enabled: true,
          value: '',
          label: '人/月',
          ratio: '',
          valueColor: '#212529',
          ratioColor: '#6c757d',
          valueFontSize: 20,
          labelFontSize: 12,
          ratioFontSize: 10,
        },
        doughnutSliceLabels: { enabled: false, fontSize: 11, color: '#fff', unit: '人', precision: 1, showName: false },
      }
    }
  });

  // グラフ⑥ インシデント案件 追加/完了/在庫推移
  charts.incidentTrend = new Chart(
    document.getElementById('chartIncidentTrend').getContext('2d'), {
    type: 'bar',
    data: { labels: [], datasets: [] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
        tooltip: {
          mode: 'index',
          callbacks: {
            label: ctx => {
              const v = ctx.parsed.y;
              if (v === null) return null;
              const sign = v >= 0 ? '+' : '';
              return ` ${ctx.dataset.label}: ${sign}${v} 件`;
            }
          }
        }
      },
      scales: {
        x: { ticks: { font: { size: 10 } } },
        y1: {
          type: 'linear', position: 'left',
          title: { display: true, text: '追加 / 完了（件）', font: { size: 10 } },
          ticks: { stepSize: 1 },
        },
        y2: {
          type: 'linear', position: 'right',
          title: { display: true, text: 'スタック数（件）', font: { size: 10 } },
          grid: { drawOnChartArea: false },
          min: 0,
        }
      }
    }
  });
}

// ================================================================
// 全チャート更新
// ================================================================
function renderAll() {
  const months = getMonthRange();
  const groups = getSelectedGroups();
  updateKpis(months, groups);
  renderCostTrend(months, groups);
  renderTopProjects(months, groups);
  renderProjectTrend(months, groups);
  renderPersonTrend(months, groups);
  renderKubunChart(months);
  renderIncidentTrend(months, groups);
}

// ================================================================
// KPI 更新
// ================================================================
function updateKpis(months, groups) {
  const monthSet = new Set(months);
  const groupSet = new Set(groups);

  // 累計部門費（allCosts ベース）
  const fc = (typeof allCosts !== 'undefined' ? allCosts : [])
    .filter(r => monthSet.has(r["月"]) && groupSet.has(r.group));
  const totalCost = fc.reduce((s, r) => s + (r["労務費(千円)"] || 0) + (r["経費(千円)"] || 0), 0);

  // 価値稼働工数・全工数（kubunHours ベース：全区分含む）
  let valueHours = 0, totalKubunHours = 0;
  (typeof kubunHours !== 'undefined' ? kubunHours : []).forEach(r => {
    if (!monthSet.has(r["月"])) return;
    totalKubunHours += r.hours;
    if (r.kubun === '開発テーマ' || r.kubun === 'インシデント') valueHours += r.hours;
  });
  const ratio = totalKubunHours > 0
    ? (valueHours / totalKubunHours * 100).toFixed(1)
    : '0.0';

  // 月あたり平均担当案件数（開発テーマ＋インシデント合計、グループフィルタ非依存）
  const allH = typeof allHours !== 'undefined' ? allHours : [];
  let monthCountSum = 0, monthCountN = 0;
  months.forEach(m => {
    const rows = allH.filter(r => r["月"] === m);
    const mP = {};
    rows.forEach(r => {
      memberCols.forEach(mc => {
        if ((r[mc] || 0) > 0) mP[mc] = (mP[mc] || 0) + 1;
      });
    });
    const active = Object.values(mP);
    if (active.length > 0) {
      monthCountSum += active.reduce((s, v) => s + v, 0) / active.length;
      monthCountN++;
    }
  });
  const avgProjCount = monthCountN > 0 ? (monthCountSum / monthCountN).toFixed(1) : '—';

  document.getElementById('kpiValueHours').textContent   = Math.round(valueHours).toLocaleString('ja-JP');
  document.getElementById('kpiValueRatio').textContent   = ratio;
  document.getElementById('kpiTotalCost').textContent    = Math.round(totalCost).toLocaleString('ja-JP');
  document.getElementById('kpiProjectCount').textContent = avgProjCount;
}

// ================================================================
// グラフ① グループ別累計コスト（ドーナツ）
// ================================================================
function renderCostTrend(months, groups) {
  const monthSet = new Set(months);
  const costByGroup = {};
  (typeof allCosts !== 'undefined' ? allCosts : []).forEach(r => {
    if (!monthSet.has(r["月"]) || !groups.includes(r.group)) return;
    const c = (r["労務費(千円)"] || 0) + (r["経費(千円)"] || 0);
    costByGroup[r.group] = (costByGroup[r.group] || 0) + c;
  });

  const labels = groups.filter(g => (costByGroup[g] || 0) > 0);
  const data   = labels.map(g => Math.round(costByGroup[g]));
  const colors = labels.map((g, i) => getGroupColor(g, i));

  const totalCost = data.reduce((a, b) => a + b, 0);
  const cp = charts.costTrend.options.plugins.doughnutCenter;
  cp.value = Math.round(totalCost).toLocaleString('ja-JP');
  cp.label = '千円';
  cp.ratio = '累計部門費';

  charts.costTrend.data.labels = labels;
  charts.costTrend.data.datasets = [{
    data,
    backgroundColor: colors,
    borderWidth: 1,
    borderColor: '#fff',
  }];
  charts.costTrend.update();
}

// ================================================================
// グラフ② 案件別コスト Top 20
// ================================================================
function renderTopProjects(months, groups) {
  const monthSet = new Set(months);
  const groupSet = new Set(groups);
  const proj = {};
  (typeof allCosts !== 'undefined' ? allCosts : []).forEach(r => {
    if (!monthSet.has(r["月"]) || !groupSet.has(r.group)) return;
    const name = r["案件（業務）名"];
    if (!proj[name]) proj[name] = { cost: 0, hours: 0, group: r.group };
    proj[name].cost  += (r["労務費(千円)"] || 0) + (r["経費(千円)"] || 0);
    proj[name].hours += r["対象工数(hour)"] || 0;
  });

  const sorted = Object.entries(proj)
    .sort((a, b) => b[1].cost - a[1].cost)
    .slice(0, 20);

  const MAX_LABEL = 14;
  const fullLabels  = sorted.map(([n]) => resolveProjectName(n));
  const shortLabels = fullLabels.map(fn => fn.length > MAX_LABEL ? fn.slice(0, MAX_LABEL - 1) + '…' : fn);
  const costs  = sorted.map(([, v]) => Math.round(v.cost));
  const hours  = sorted.map(([, v]) => v.hours.toFixed(1));
  const colors = sorted.map(([, v]) => getGroupColor(v.group, allGroups.indexOf(v.group)));

  charts.topProjects.data.labels = shortLabels;
  charts.topProjects.data.datasets = [{
    label: '部門費（千円）',
    data: costs,
    backgroundColor: colors,
    borderWidth: 0,
    _fullLabels: fullLabels,
    _hours: hours,
  }];
  charts.topProjects.update();
}

// ================================================================
// グラフ③ 個人別 インシデント/開発テーマ 平均工数・案件数推移
// ================================================================
function renderPersonTrend(months, groups) {
  const person   = getSelectedPerson();
  const groupSet = new Set(groups);
  const allH     = typeof allHours !== 'undefined' ? allHours : [];

  // ---- 左グラフ: 月別 合計平均工数＋合計案件数（開発テーマ＋インシデント合計） ----
  const monthly = { counts: [], totalHours: [] };
  months.forEach(m => {
    const rows = allH.filter(r => r["月"] === m);
    let count = 0, total = 0;
    rows.forEach(r => {
      const h = person ? (r[person] || 0) : 0;
      if (h > 0) { count++; total += h; }
    });
    monthly.counts.push(count);
    monthly.totalHours.push(total);
  });
  const avgHours = monthly.counts.map((c, i) =>
    c > 0 ? parseFloat((monthly.totalHours[i] / c).toFixed(2)) : 0);

  charts.personHours.data.labels = months;
  charts.personHours.data.datasets = [
    {
      label: '平均工数（h/件）',
      data: avgHours,
      backgroundColor: '#3498dbaa',
      borderColor: '#3498db',
      borderWidth: 1,
      type: 'bar',
      yAxisID: 'y1',
      order: 2,
    },
    {
      label: '担当案件数',
      data: monthly.counts,
      borderColor: '#e67e22',
      backgroundColor: '#e67e22',
      type: 'line',
      yAxisID: 'y2',
      tension: 0,
      pointRadius: 4,
      order: 1,
    }
  ];
  charts.personHours.update();

  // ---- 右グラフ: 担当テーマ別工数（横棒、全期間合計） ----
  const projMap = {}; // 案件名 → { hours, kubun }
  allH.forEach(r => {
    if (!months.includes(r["月"])) return;
    if (!groupSet.has(r.group)) return;
    const kubun = getKubunByGroup(r.group);
    if (!kubun) return;
    const h = person ? (r[person] || 0) : 0;
    if (h <= 0) return;
    const name = r["案件（業務）名"];
    if (!projMap[name]) projMap[name] = { hours: 0, kubun, group: r.group };
    projMap[name].hours += h;
  });

  const MAX_PROJ = 20;
  const MAX_LBL  = 14;
  const sorted = Object.entries(projMap)
    .sort((a, b) => b[1].hours - a[1].hours)
    .slice(0, MAX_PROJ);
  const fullLabels  = sorted.map(([n]) => resolveProjectName(n));
  const shortLabels = fullLabels.map(fn => fn.length > MAX_LBL ? fn.slice(0, MAX_LBL - 1) + '…' : fn);
  const hoursData   = sorted.map(([, v]) => parseFloat(v.hours.toFixed(1)));
  const bgColors    = sorted.map(([, v]) => getGroupColor(v.group, allGroups.indexOf(v.group)));
  const kubunLabels = sorted.map(([, v]) => v.kubun);

  charts.personProjs.data.labels = shortLabels;
  charts.personProjs.data.datasets = [{
    data: hoursData,
    backgroundColor: bgColors,
    borderWidth: 0,
    _fullLabels: fullLabels,
    _kubun: kubunLabels,
  }];
  charts.personProjs.update();
}

// ================================================================
// グラフ④ 一人当たり案件数推移
// ================================================================
function renderProjectTrend(months, groups) {
  const meanHPerProj = [];
  const meanCount    = [];
  const stdCount     = [];

  months.forEach(m => {
    // 開発テーマ＋インシデント合計（グループフィルタ非依存）
    const rows = (typeof allHours !== 'undefined' ? allHours : [])
      .filter(r => r["月"] === m);

    const mH = {}, mP = {};
    rows.forEach(r => {
      memberCols.forEach(mc => {
        const h = r[mc] || 0;
        if (h > 0) {
          mH[mc] = (mH[mc] || 0) + h;
          mP[mc] = (mP[mc] || 0) + 1;
        }
      });
    });

    const active = Object.keys(mP);
    if (active.length === 0) {
      meanHPerProj.push(0); meanCount.push(0); stdCount.push(0);
      return;
    }

    const counts    = active.map(mc => mP[mc]);
    const hPerProj  = active.map(mc => mP[mc] > 0 ? mH[mc] / mP[mc] : 0);
    const mc_mean   = counts.reduce((s, v) => s + v, 0) / counts.length;
    const mh_mean   = hPerProj.reduce((s, v) => s + v, 0) / hPerProj.length;
    const variance  = counts.reduce((s, v) => s + (v - mc_mean) ** 2, 0) / counts.length;

    meanHPerProj.push(parseFloat(mh_mean.toFixed(2)));
    meanCount.push(parseFloat(mc_mean.toFixed(2)));
    stdCount.push(parseFloat(Math.sqrt(variance).toFixed(2)));
  });

  // エラーバー上端の最大値に余白を加えてY軸がクリップしないようにする
  const maxY2 = Math.max(...meanCount.map((v, i) => v + (stdCount[i] || 0)));
  charts.projectTrend.options.scales.y2.suggestedMax = maxY2 * 1.15;

  charts.projectTrend.data.labels = months;
  charts.projectTrend.data.datasets = [
    {
      label: '1案件当り平均時間',
      data: meanHPerProj,
      backgroundColor: '#f39c1299',
      borderColor: '#f39c12',
      borderWidth: 1,
      type: 'bar',
      yAxisID: 'y1',
      order: 2,
    },
    {
      label: '平均担当案件数',
      data: meanCount,
      borderColor: '#3498db',
      backgroundColor: '#3498db',
      type: 'line',
      yAxisID: 'y2',
      tension: 0.3,
      pointRadius: 5,
      order: 1,
      _stdDev: stdCount,
    }
  ];
  charts.projectTrend.update();
}

// ================================================================
// グラフ⑤ 区分別累計工数（ドーナツ）
// ================================================================
const KUBUN_COLORS = {
  "開発テーマ": "#e74c3c",
  "インシデント": "#3498db",
  "日常業務":   "#2ecc71",
  "教育":       "#f39c12",
  "不働工数":   "#95a5a6",
};
const KUBUN_ORDER = ["開発テーマ", "インシデント", "日常業務", "教育", "不働工数"];

function renderKubunChart(months) {
  const monthSet = new Set(months);

  // 月別・区分別工数を集計
  const hoursByMonth = {};
  (typeof kubunHours !== 'undefined' ? kubunHours : []).forEach(r => {
    if (!monthSet.has(r["月"])) return;
    if (!hoursByMonth[r["月"]]) hoursByMonth[r["月"]] = {};
    hoursByMonth[r["月"]][r.kubun] = (hoursByMonth[r["月"]][r.kubun] || 0) + r.hours;
  });

  // person_months マップ
  const pmMap = {};
  if (typeof monthlyPersonMonths !== 'undefined') {
    monthlyPersonMonths.forEach(r => { pmMap[r["月"]] = r.pm; });
  }

  // 各月: 総工数を人工数に変換し区分別に按分 → 月平均を算出
  const pmSums = {};
  let pmMonthCount = 0;
  Object.keys(hoursByMonth).forEach(month => {
    const mh = hoursByMonth[month];
    const totalH = Object.values(mh).reduce((a, b) => a + b, 0);
    const pm = pmMap[month];
    if (pm && totalH > 0) {
      KUBUN_ORDER.forEach(k => {
        pmSums[k] = (pmSums[k] || 0) + ((mh[k] || 0) / totalH) * pm;
      });
      pmMonthCount++;
    }
  });

  // 月平均に変換（person_months データがない場合は時間÷標準時間でフォールバック）
  let pmAvg = {};
  if (pmMonthCount > 0) {
    KUBUN_ORDER.forEach(k => { pmAvg[k] = (pmSums[k] || 0) / pmMonthCount; });
  } else {
    const st = typeof standardTime !== 'undefined' ? standardTime : 7.5;
    const totalsH = {};
    Object.values(hoursByMonth).forEach(mh => {
      KUBUN_ORDER.forEach(k => { totalsH[k] = (totalsH[k] || 0) + (mh[k] || 0); });
    });
    const nMonths = Object.keys(hoursByMonth).length || 1;
    KUBUN_ORDER.forEach(k => { pmAvg[k] = (totalsH[k] || 0) / nMonths / st; });
  }

  const labels = KUBUN_ORDER.filter(k => (pmAvg[k] || 0) > 0.001);
  const data   = labels.map(k => parseFloat((pmAvg[k] || 0).toFixed(2)));
  const colors = labels.map(k => KUBUN_COLORS[k] || "#aaa");

  // 合計・価値稼働比率
  const totalPm = data.reduce((a, b) => a + b, 0);
  const valuePm = labels.reduce((s, k, i) =>
    (k === '開発テーマ' || k === 'インシデント') ? s + data[i] : s, 0);
  const pct = totalPm > 0 ? (valuePm / totalPm * 100).toFixed(1) : '0.0';

  // 中央テキスト（monthlyPersonMonths の月平均）
  let avgPm = null;
  if (typeof monthlyPersonMonths !== 'undefined') {
    const pmInRange = monthlyPersonMonths.filter(r => monthSet.has(r["月"]));
    if (pmInRange.length > 0) {
      avgPm = pmInRange.reduce((s, r) => s + r.pm, 0) / pmInRange.length;
    }
  }
  const jinkoNum = avgPm !== null
    ? avgPm.toFixed(1)
    : (totalPm > 0 ? totalPm.toFixed(1) : '—');

  charts.kubun.data.labels = labels;
  charts.kubun.data.datasets = [{
    data,
    backgroundColor: colors,
    borderWidth: 1,
    borderColor: '#fff',
  }];
  const cp = charts.kubun.options.plugins.doughnutCenter;
  cp.value = jinkoNum;
  cp.label = '人/月';
  cp.ratio = pct + '% 価値稼働';
  charts.kubun.update();
}

// ================================================================
// グラフ⑥ インシデント案件数推移
// ================================================================
const INCIDENT_GROUPS = new Set(["工用", "電気", "ロール", "合樹", "印材", "(その他)"]);
const DEV_GROUPS      = new Set(["新製品PJ", "MFS", "精練", "FH"]);
function getKubunByGroup(group) {
  if (INCIDENT_GROUPS.has(group)) return 'インシデント';
  if (DEV_GROUPS.has(group))      return '開発テーマ';
  return null;
}

function renderIncidentTrend(months, groups) {
  const groupSet = new Set(groups);
  const allH = typeof allHours !== 'undefined' ? allHours : [];

  // 全期間のインシデント案件ごとの月別工数マップを構築
  const projMonthHours = {};
  allH.forEach(r => {
    if (!INCIDENT_GROUPS.has(r.group) || !groupSet.has(r.group)) return;
    const name = r["案件（業務）名"];
    const m    = r["月"];
    if (!projMonthHours[name]) projMonthHours[name] = {};
    projMonthHours[name][m] = (projMonthHours[name][m] || 0) + (r["合計時間(h)"] || 0);
  });

  // 全期間の月別アクティブ案件セット（hours > 0）
  const activeByMonth = {};
  allMonths.forEach(m => {
    activeByMonth[m] = new Set(
      Object.entries(projMonthHours)
        .filter(([, mh]) => (mh[m] || 0) > 0)
        .map(([name]) => name)
    );
  });

  const addedData = [], completedData = [], stockData = [];
  months.forEach(m => {
    const idx  = allMonths.indexOf(m);
    const curr = activeByMonth[m] || new Set();
    stockData.push(curr.size);

    if (idx > 0) {
      const prev = activeByMonth[allMonths[idx - 1]] || new Set();
      let addCnt = 0, compCnt = 0;
      curr.forEach(p => { if (!prev.has(p)) addCnt++; });
      prev.forEach(p => { if (!curr.has(p)) compCnt++; });
      addedData.push(addCnt);
      completedData.push(-compCnt);
    } else {
      addedData.push(null);
      completedData.push(null);
    }
  });

  // 純増減 = 追加 − 完了（completedData は負値なので加算）
  const netData = addedData.map((a, i) =>
    a === null ? null : a + completedData[i]
  );
  const netColors = netData.map(v => v === null ? 'transparent' : v >= 0 ? '#2ecc71' : '#e74c3c');

  charts.incidentTrend.data.labels = months;
  charts.incidentTrend.data.datasets = [
    {
      label: '純増減（追加−完了）',
      data: netData,
      backgroundColor: netColors,
      yAxisID: 'y1',
      order: 2,
    },
    {
      label: 'スタック数',
      data: stockData,
      type: 'line',
      borderColor: '#3498db',
      backgroundColor: '#3498db',
      yAxisID: 'y2',
      tension: 0,
      pointRadius: 4,
      fill: false,
      order: 1,
    },
  ];
  charts.incidentTrend.update();
}
